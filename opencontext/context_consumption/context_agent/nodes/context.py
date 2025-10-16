#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Context Collection Node
Intelligently collects and judges context information
"""

import json
from typing import Any, Dict, List, Optional

from ..core.llm_context_strategy import LLMContextStrategy
from ..core.state import StreamEvent, WorkflowState
from ..models.enums import ContextSufficiency, EventType, NodeType, WorkflowStage
from ..models.schemas import DocumentInfo
from .base import BaseNode


class ContextNode(BaseNode):
    """Context collection node"""

    def __init__(self, streaming_manager=None):
        super().__init__(NodeType.CONTEXT, streaming_manager)
        self.strategy = LLMContextStrategy()
        self.max_iterations = 2  # Collect for a maximum of 3 rounds

    async def process(self, state: WorkflowState) -> WorkflowState:
        """Process context collection - using an LLM-driven iterative model"""
        state.update_stage(WorkflowStage.CONTEXT_GATHERING)
        await self.streaming_manager.emit(
            StreamEvent(
                type=EventType.RUNNING,
                content="Starting to intelligently analyze and collect relevant context...",
                stage=WorkflowStage.CONTEXT_GATHERING,
                progress=0.0,
            )
        )

        # Update stage
        state.update_stage(WorkflowStage.CONTEXT_GATHERING)

        # Process document context
        if state.query.document_id is not None:
            from opencontext.storage.global_storage import get_storage

            doc = get_storage().get_vault(int(state.query.document_id))
            if not doc:
                await self.streaming_manager.emit(
                    StreamEvent(
                        type=EventType.FAIL,
                        content=f"Document {state.query.document_id} not found",
                        stage=WorkflowStage.CONTEXT_GATHERING,
                        progress=1.0,
                    )
                )
                state.update_stage(WorkflowStage.FAILED)
                return state
            state.contexts.current_document = DocumentInfo(
                id=state.query.document_id,
                title=doc.get("title", ""),
                content=doc.get("content", ""),
                summary=doc.get("summary", ""),
                tags=doc.get("tags", []),
            )
            await self.streaming_manager.emit(
                StreamEvent(
                    type=EventType.DONE,
                    content=f"Added document context: {doc.get('title', '')}",
                    stage=WorkflowStage.CONTEXT_GATHERING,
                    progress=0.0,
                )
            )

        # LLM-driven iterative collection process
        iteration = 0
        while iteration < self.max_iterations:
            iteration += 1
            progress = iteration / self.max_iterations
            await self.streaming_manager.emit(
                StreamEvent(
                    type=EventType.RUNNING,
                    content=f"Round {iteration} of intelligent context collection...",
                    stage=WorkflowStage.CONTEXT_GATHERING,
                    progress=progress,
                )
            )

            # 1. Evaluate sufficiency first (including first iteration)
            sufficiency = await self.strategy.evaluate_sufficiency(state.contexts, state.intent)
            state.contexts.sufficiency = sufficiency

            if sufficiency == ContextSufficiency.SUFFICIENT:
                await self.streaming_manager.emit(
                    StreamEvent(
                        type=EventType.DONE,
                        content=f"Context is sufficient, collected {len(state.contexts.items)} items in total",
                        stage=WorkflowStage.CONTEXT_GATHERING,
                        progress=1.0,
                    )
                )
                break

            # 2. Analyze information gap and plan tool calls
            tool_calls, _ = await self.strategy.analyze_and_plan_tools(
                state.intent, state.contexts, iteration=iteration
            )

            if not tool_calls:
                await self.streaming_manager.emit(
                    StreamEvent(
                        type=EventType.DONE,
                        content=f"No more tools to call, ending collection with {len(state.contexts.items)} items",
                        stage=WorkflowStage.CONTEXT_GATHERING,
                        progress=1.0,
                    )
                )
                break

            # 3. Execute tool calls concurrently
            await self.streaming_manager.emit(
                StreamEvent(
                    type=EventType.RUNNING,
                    content=f"Concurrently calling {len(tool_calls)} tools...",
                    stage=WorkflowStage.CONTEXT_GATHERING,
                )
            )
            new_context_items = await self.strategy.execute_tool_calls_parallel(tool_calls)

            # 4. Validate and filter tool results
            await self.streaming_manager.emit(
                StreamEvent(
                    type=EventType.RUNNING,
                    content="Validating tool results and filtering relevant contexts...",
                    stage=WorkflowStage.CONTEXT_GATHERING,
                )
            )
            validated_items, _ = await self.strategy.validate_and_filter_tool_results(
                tool_calls, new_context_items, state.intent, state.contexts
            )

            # 5. Add validated results to context collection
            for item in validated_items:
                state.contexts.add_item(item)

            await self.streaming_manager.emit(
                StreamEvent(
                    type=EventType.DONE,
                    content=f"Round {iteration}: Added {len(validated_items)} relevant context items (filtered from {len(new_context_items)} total)",
                    stage=WorkflowStage.CONTEXT_GATHERING,
                )
            )

            # Check if reached max iterations
            if iteration >= self.max_iterations:
                state.contexts.sufficiency = ContextSufficiency.PARTIAL
                await self.streaming_manager.emit(
                    StreamEvent(
                        type=EventType.DONE,
                        content=f"Maximum collection rounds reached, currently have {len(state.contexts.items)} context items",
                        stage=WorkflowStage.CONTEXT_GATHERING,
                        progress=1.0,
                    )
                )
                break
        return state

    def validate_state(self, state: WorkflowState) -> bool:
        """Validate state"""
        # Requires intent analysis results
        return state.intent is not None
