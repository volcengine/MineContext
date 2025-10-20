#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Workflow Engine
Core workflow control logic.
"""

import asyncio
from datetime import datetime
from typing import Any, AsyncIterator, Dict, Optional

from opencontext.utils.logging_utils import get_logger

from ..models.enums import ContextSufficiency, EventType, ReflectionType, WorkflowStage
from ..models.events import StreamEvent
from ..models.schemas import Query
from .state import StateManager, WorkflowState
from .streaming import StreamingManager


class WorkflowEngine:
    """Workflow engine."""

    def __init__(
        self,
        streaming_manager: Optional[StreamingManager] = None,
        state_manager: Optional[StateManager] = None,
    ):
        self.streaming_manager = streaming_manager or StreamingManager()
        self.state_manager = state_manager or StateManager()
        self.logger = get_logger(self.__class__.__name__)

        # Node instances (lazy initialization)
        self._nodes = {}

    def _init_nodes(self):
        """Initialize nodes."""
        if not self._nodes:
            # Import node classes (to avoid circular imports)
            from ..nodes.context import ContextNode
            from ..nodes.executor import ExecutorNode
            from ..nodes.intent import IntentNode
            from ..nodes.reflection import ReflectionNode

            # Create node instances
            self._nodes = {
                WorkflowStage.INTENT_ANALYSIS: IntentNode(streaming_manager=self.streaming_manager),
                WorkflowStage.CONTEXT_GATHERING: ContextNode(
                    streaming_manager=self.streaming_manager
                ),
                WorkflowStage.EXECUTION: ExecutorNode(
                    streaming_manager=self.streaming_manager,
                ),
                WorkflowStage.REFLECTION: ReflectionNode(streaming_manager=self.streaming_manager),
            }

    async def execute(self, streaming, **kwargs) -> WorkflowState:
        """
        Execute the workflow.
        """
        # Initialize nodes
        self._init_nodes()
        query_obj = Query(
            text=kwargs.get("query", ""),
            user_id=kwargs.get("user_id", None),
            session_id=kwargs.get("session_id", None),
            selected_content=kwargs.get("selected_content", None),
            document_id=kwargs.get("document_id", None),
        )
        state = self.state_manager.create_state(query_obj=query_obj, **kwargs)
        try:
            await self.streaming_manager.emit(
                StreamEvent(
                    type=EventType.RUNNING,
                    stage=state.stage,
                    content=f"Starting to process query: {state.query.text}...",
                )
            )
            state = await self._execute_workflow(state)
            self.logger.info(f"Workflow execution completed, current stage: {state.stage.value}")
            if streaming:
                await self.streaming_manager.emit(
                    StreamEvent(
                        type=EventType.STREAM_COMPLETE,
                        stage=state.stage,
                        content="",
                        progress=1.0,
                    )
                )
            else:
                await self.streaming_manager.emit(
                    StreamEvent(
                        type=EventType.COMPLETED,
                        stage=state.stage,
                        content=state.final_content,
                        progress=1.0,
                    )
                )
        except Exception as e:
            self.logger.exception(f"Workflow execution failed: {e}")
            state.update_stage(WorkflowStage.FAILED)
            state.add_error(str(e))
            await self.streaming_manager.emit(
                StreamEvent(
                    type=EventType.FAIL,
                    stage=state.stage,
                    content=f"Workflow execution failed: {str(e)}",
                )
            )
        return state

    async def execute_stream(self, **kwargs) -> AsyncIterator[StreamEvent]:
        """
        Execute the workflow in streaming mode.
        """
        # Start the workflow execution task
        task = asyncio.create_task(self.execute(streaming=True, **kwargs))
        try:
            async for event in self.streaming_manager.stream():
                yield event
        finally:
            await task

    async def _execute_workflow(self, state: WorkflowState) -> WorkflowState:
        """Execute the main workflow logic."""
        # 1. Intent analysis
        state.update_stage(WorkflowStage.INTENT_ANALYSIS)
        intent_node = self._nodes[WorkflowStage.INTENT_ANALYSIS]
        state = await intent_node.execute(state)

        # Check if we need to continue
        if state.stage == WorkflowStage.FAILED or state.stage == WorkflowStage.COMPLETED:
            return state
        # 2. Context gathering
        state.update_stage(WorkflowStage.CONTEXT_GATHERING)
        context_node = self._nodes[WorkflowStage.CONTEXT_GATHERING]
        state = await context_node.execute(state)
        # Check if the context is sufficient
        if state.contexts.sufficiency == ContextSufficiency.INSUFFICIENT:
            return state
        if state.stage == WorkflowStage.FAILED or state.stage == WorkflowStage.COMPLETED:
            return state
        # 3. Execution
        state.update_stage(WorkflowStage.EXECUTION)
        executor_node = self._nodes[WorkflowStage.EXECUTION]
        state = await executor_node.execute(state)
        if state.stage == WorkflowStage.FAILED:
            return state
        # # 4. Reflection
        # state.update_stage(WorkflowStage.REFLECTION)
        # reflection_node = self._nodes[WorkflowStage.REFLECTION]
        # state = await reflection_node.execute(state)
        # # Check if a retry is needed
        # if state.reflection and state.reflection.should_retry and state.should_retry():
        #     state.increment_retry()
        #     # Recursive execution
        #     return await self._execute_workflow(state)
        # Done

        state.update_stage(WorkflowStage.COMPLETED)
        return state

    async def _emit_workflow_event(self, event_type: EventType, state: WorkflowState, message: str):
        """Emit a workflow event."""
        if self.streaming_manager:
            event = StreamEvent.create_workflow_event(
                event_type=event_type,
                stage=state.stage,
                message=message,
                workflow_id=state.metadata.workflow_id,
            )
            await self.streaming_manager.emit(event)

    async def resume(self, workflow_id: str, user_input: Optional[str] = None) -> WorkflowState:
        """
        Resume workflow execution.

        Args:
            workflow_id: The workflow ID.
            user_input: User input (for scenarios requiring user confirmation).

        Returns:
            The updated workflow state.
        """
        state = self.state_manager.get_state(workflow_id)
        if not state:
            raise ValueError(f"Workflow {workflow_id} not found")

        if state.is_complete():
            return state

        if state.stage == WorkflowStage.INSUFFICIENT_INFO and user_input:
            state.query.text += f" {user_input}"
            return await self._execute_workflow(state)
        return await self._execute_workflow(state)

    def get_state(self, workflow_id: str) -> Optional[WorkflowState]:
        """Get the workflow state."""
        return self.state_manager.get_state(workflow_id)

    def cancel(self, workflow_id: str):
        """Cancel the workflow."""
        state = self.state_manager.get_state(workflow_id)
        if state:
            state.is_cancelled = True
            state.update_stage(WorkflowStage.FAILED)
