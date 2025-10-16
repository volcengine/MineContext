#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Context Agent Main Entry Point
Provides a simple API interface
"""

import asyncio
from typing import Any, AsyncIterator, Dict, Optional

from opencontext.context_consumption.context_agent.core.state import StateManager, WorkflowState
from opencontext.context_consumption.context_agent.core.streaming import StreamingManager
from opencontext.context_consumption.context_agent.core.workflow import WorkflowEngine
from opencontext.context_consumption.context_agent.models.events import EventType, StreamEvent
from opencontext.utils.logging_utils import get_logger

logger = get_logger("ContextAgent")


class ContextAgent:
    """Context Agent main class"""

    def __init__(self, enable_streaming: bool = True):
        """
        Initialize the Context Agent

        Args:
            enable_streaming: Whether to enable streaming output
        """
        self.streaming_manager = StreamingManager() if enable_streaming else None
        self.state_manager = StateManager()
        self.workflow_engine = WorkflowEngine(
            streaming_manager=self.streaming_manager, state_manager=self.state_manager
        )
        self.enable_streaming = enable_streaming

    async def process(self, **kwargs) -> Dict[str, Any]:
        """
        Process user queries
        """
        # Execute the workflow
        state = await self.workflow_engine.execute(streaming=self.enable_streaming, **kwargs)
        return self._format_result(state)

    async def process_stream(self, **kwargs) -> AsyncIterator[StreamEvent]:
        async for event in self.workflow_engine.execute_stream(**kwargs):
            yield event

    def _format_result(self, state: WorkflowState) -> Dict[str, Any]:
        """Format the result"""
        result = {
            "success": state.stage.value == "completed",
            "workflow_id": state.metadata.workflow_id,
            "stage": state.stage.value,
            "query": state.query.text,
        }

        # Add intent analysis results
        if state.intent:
            result["intent"] = {
                "type": state.intent.query_type.value,
                "enhanced_query": state.intent.enhanced_query,
                "original_query": state.intent.original_query,
            }
        # Add context information
        if state.contexts:
            result["context"] = {
                "count": len(state.contexts.items),
                "sufficiency": state.contexts.sufficiency.value,
                "summary": state.contexts.get_summary(),
            }
        # Add execution results
        if state.execution_result:
            result["execution"] = {
                "success": state.execution_result.success,
                "outputs": state.execution_result.outputs,
                "errors": state.execution_result.errors,
            }
        # Add reflection results
        if state.reflection:
            result["reflection"] = {
                "type": state.reflection.reflection_type.value,
                "success_rate": state.reflection.success_rate,
                "summary": state.reflection.summary,
                "improvements": state.reflection.improvements,
            }
        # Add error information
        if state.errors:
            result["errors"] = state.errors

        return result

    async def get_state(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        Get workflow state
        """
        state = self.workflow_engine.get_state(workflow_id)
        if state:
            return self._format_result(state)
        return None

    async def resume(self, workflow_id: str, user_input: Optional[str] = None) -> Dict[str, Any]:
        """
        Resume a workflow

        Args:
            workflow_id: Workflow ID
            user_input: User input

        Returns:
            Processing result
        """
        state = await self.workflow_engine.resume(workflow_id, user_input)
        return self._format_result(state)

    def cancel(self, workflow_id: str):
        """
        Cancel a workflow

        Args:
            workflow_id: Workflow ID
        """
        self.workflow_engine.cancel(workflow_id)


# Convenience functions


async def process_query(
    query: str, session_id: Optional[str] = None, context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Convenience function to process a query

    Args:
        query: User query
        session_id: Session ID
        context: Additional context

    Returns:
        Processing result
    """
    agent = ContextAgent()
    return await agent.process(query, session_id=session_id, context=context)


async def process_query_stream(
    query: str, session_id: Optional[str] = None, context: Optional[Dict[str, Any]] = None
) -> AsyncIterator[Dict[str, Any]]:
    """
    Convenience function to process a query with streaming

    Args:
        query: User query
        session_id: Session ID
        context: Additional context

    Yields:
        Stream events
    """
    agent = ContextAgent(enable_streaming=True)
    async for event in agent.process_stream(query, session_id=session_id, context=context):
        yield event
