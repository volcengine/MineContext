#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Context Collection Node
Intelligently collects and judges context information
"""

from typing import List, Dict, Any, Optional
from .base import BaseNode
from ..core.state import WorkflowState, StreamEvent
from ..models.enums import (
    NodeType, WorkflowStage,
    ContextSufficiency, EventType
)
from ..models.schemas import DocumentInfo
from ..core.llm_context_strategy import LLMContextStrategy




class ContextNode(BaseNode):
    """Context collection node"""
    
    def __init__(self, streaming_manager=None):
        super().__init__(NodeType.CONTEXT, streaming_manager)
        self.strategy = LLMContextStrategy()
        self.max_iterations = 2  # Collect for a maximum of 3 rounds
        
    async def process(self, state: WorkflowState) -> WorkflowState:
        """Process context collection - using an LLM-driven iterative model"""
        state.update_stage(WorkflowStage.CONTEXT_GATHERING)
        await self.streaming_manager.emit(StreamEvent(
            type=EventType.RUNNING,
            content="Starting to intelligently analyze and collect relevant context...",
            stage=WorkflowStage.CONTEXT_GATHERING,
            progress=0.0
        ))
        
        # Update stage
        state.update_stage(WorkflowStage.CONTEXT_GATHERING)
        
        # Process document context
        if state.query.document_id is not None:
            from context_lab.storage.global_storage import get_storage
            doc = get_storage().get_vault(int(state.query.document_id))
            if not doc:
                await self.streaming_manager.emit(StreamEvent(
                    type=EventType.FAIL,
                    content=f"Document {state.query.document_id} not found",
                    stage=WorkflowStage.CONTEXT_GATHERING,
                    progress=1.0
                ))
                state.update_stage(WorkflowStage.FAILED)
                return state
            state.contexts.current_document = DocumentInfo(
                id=state.query.document_id,
                title=doc.get("title", ""),
                content=doc.get("content", ""),
                summary=doc.get("summary", ""),
                tags=doc.get("tags", [])
            )
            await self.streaming_manager.emit(StreamEvent(
                type=EventType.DONE,
                content=f"Added document context: {doc.get('title', '')}",
                stage=WorkflowStage.CONTEXT_GATHERING,
                progress=0.0
            ))

        # LLM-driven iterative collection process
        iteration = 0
        tool_history = []  # Record tool call history
        while iteration < self.max_iterations:
            iteration += 1
            progress = iteration / self.max_iterations
            
            await self.streaming_manager.emit(StreamEvent(
                type=EventType.RUNNING,
                content=f"Round {iteration} of intelligent context collection...",
                stage=WorkflowStage.CONTEXT_GATHERING,
                progress=progress
            ))
            tool_calls = await self.strategy.analyze_and_plan_tools(
                state.intent,
                state.contexts,
                max_tools=5,
                iteration=iteration,
                tool_history=tool_history
            )
            # # Filter duplicate calls
            # if tool_history:
            #     tool_calls = await self.strategy.filter_duplicate_calls(
            #         tool_calls,
            #         tool_history
            #     )
            if tool_calls:
                # 2. Concurrently execute tool calls
                await self.streaming_manager.emit(StreamEvent(
                    type=EventType.RUNNING,
                    content=f"Concurrently calling {len(tool_calls)} tools...",
                    stage=WorkflowStage.CONTEXT_GATHERING))
                new_context_items = await self.strategy.execute_tool_calls_parallel(tool_calls)
                # Record tool call history
                # for call in tool_calls:
                #     func_name = call.get("function", {}).get("name")
                #     func_args = call.get("function", {}).get("arguments", {})
                #     tool_history.append({
                #         "tool_name": func_name,
                #         "query": func_args.get("query", ""),
                #         "iteration": iteration
                #     })
                # 3. Add results to context
                for item in new_context_items:
                    state.contexts.add_item(item)
                await self.streaming_manager.emit(StreamEvent(
                    type=EventType.DONE,
                    content=f"Collected {len(new_context_items)} new context items in this round",
                    stage=WorkflowStage.CONTEXT_GATHERING))
            # 4. LLM evaluates sufficiency
            sufficiency = await self.strategy.evaluate_sufficiency(
                state.contexts,
                state.intent
            )
            state.contexts.sufficiency = sufficiency
            self.logger.info(f"sufficiency {sufficiency}")
            
            # 5. If there are many context items, filter for relevance
            if len(state.contexts.items) > 5:  # Only filter if more than 5 items
                await self.streaming_manager.emit(StreamEvent(
                    type=EventType.RUNNING,
                    content="Filtering irrelevant context...",
                    stage=WorkflowStage.CONTEXT_GATHERING
                ))
                
                # Get relevant context IDs
                relevant_ids = await self.strategy.filter_relevant_contexts(
                    state.contexts.items,
                    state.intent.enhanced_query or state.intent.original_query
                )
                
                # Convert relevant IDs to a set for quick lookup
                relevant_id_set = set(relevant_ids)
                
                # Mark irrelevant context and keep relevant ones
                original_count = len(state.contexts.items)
                filtered_items = []
                
                for item in state.contexts.items:
                    if item.id in relevant_id_set:
                        item.is_relevant = True
                        filtered_items.append(item)
                    else:
                        item.is_relevant = False
                        item.relevance_reason = "Judged irrelevant to the user's question by the LLM"
                
                # Update the context collection
                state.contexts.items = filtered_items
                
                # await self.streaming_manager.emit(StreamEvent(
                #     type=EventType.DONE,
                #     content=f"Retained {len(filtered_items)} relevant context items after filtering (originally {original_count})",
                #     stage=WorkflowStage.CONTEXT_GATHERING
                # ))
            
            if sufficiency == ContextSufficiency.SUFFICIENT:
                await self.streaming_manager.emit(StreamEvent(
                    type=EventType.DONE,
                    content=f"Context collection complete, collected {len(state.contexts.items)} items in total",
                    stage=WorkflowStage.CONTEXT_GATHERING,
                    progress=1.0
                ))
                break
            elif iteration >= self.max_iterations:
                state.contexts.sufficiency = ContextSufficiency.PARTIAL
                await self.streaming_manager.emit(StreamEvent(
                    type=EventType.DONE,
                    content=f"Maximum collection rounds reached, currently have {len(state.contexts.items)} context items",
                    stage=WorkflowStage.CONTEXT_GATHERING,
                    progress=1.0
                ))
                break
        return state
            
    def validate_state(self, state: WorkflowState) -> bool:
        """Validate state"""
        # Requires intent analysis results
        return state.intent is not None