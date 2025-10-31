#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Intent Analysis Node
Analyzes user intent and enhances the query
"""

import json
from datetime import datetime
from typing import Any, Dict, List

from opencontext.config.global_config import get_prompt_group
from opencontext.context_consumption.context_agent.models.events import StreamEvent
from opencontext.llm.global_vlm_client import (
    generate_stream_for_agent,
    generate_with_messages_async,
)

from ..core.state import WorkflowState
from ..models.enums import EventType, NodeType, QueryType, WorkflowStage
from ..models.schemas import Intent
from .base import BaseNode


class IntentNode(BaseNode):
    """Intent analysis node"""

    def __init__(self, streaming_manager=None):
        super().__init__(NodeType.INTENT, streaming_manager)

    async def process(self, state: WorkflowState) -> WorkflowState:
        """Process intent analysis"""
        await self.streaming_manager.emit(
            StreamEvent(
                type=EventType.THINKING,
                content="Analyzing your intent...",
                stage=WorkflowStage.INTENT_ANALYSIS,
            )
        )
        # 1. Classify query type
        query_type = await self._classify_query(state.query.text, state.contexts.get_chat_history())
        if not query_type:
            await self.streaming_manager.emit(
                StreamEvent(
                    type=EventType.FAIL,
                    content="Intent analysis failed",
                    stage=WorkflowStage.INTENT_ANALYSIS,
                    metadata={"query": state.query.text},
                )
            )
            state.update_stage(WorkflowStage.FAILED)
            return state

        if query_type == QueryType.SIMPLE_CHAT:
            # For simple chats, directly call the large model for a reply
            return await self._simple_chat(state)
        state.intent = Intent(
            original_query=state.query.text, query_type=query_type, enhanced_query=state.query.text
        )
        # await self._enhance_complex_query(state, query_type)
        # await self.streaming_manager.emit(StreamEvent(
        #     type=EventType.DONE, content=f"Enhanced query: {state.intent.enhanced_query}", stage=WorkflowStage.INTENT_ANALYSIS,
        #     metadata={
        #         "query_type": query_type.value,
        #         "original_query": state.query.text,
        #         "enhanced_query": state.intent.enhanced_query,
        #     })
        # )
        return state

    async def _classify_query(self, query: str, chat_history: List[Dict[str, str]]) -> QueryType:
        """Use LLM to classify query types, including confidence assessment and fallback strategies"""
        prompt_group = get_prompt_group("chat_workflow.query_classification")
        messages = [
            {"role": "system", "content": prompt_group["system"]},
            {
                "role": "user",
                "content": prompt_group["user"].format(
                    query=query, chat_history=json.dumps(chat_history)
                ),
            },
        ]
        response = await generate_with_messages_async(
            messages,
            thinking="disabled",
        )
        response = response.strip().lower()
        if "simple_chat" in response:
            return QueryType.SIMPLE_CHAT
        elif "document_edit" in response:
            return QueryType.DOCUMENT_EDIT
        elif "qa_analysis" in response:
            return QueryType.QA_ANALYSIS
        elif "content_generation" in response:
            return QueryType.CONTENT_GENERATION
        return QueryType.QA_ANALYSIS

    async def _simple_chat(self, state: WorkflowState) -> WorkflowState:
        """Handle simple chats with streaming"""
        from ..models.schemas import ExecutionPlan, ExecutionResult

        await self.streaming_manager.emit(
            StreamEvent(
                type=EventType.THINKING,
                content="Generating reply...",
                stage=WorkflowStage.INTENT_ANALYSIS,
            )
        )
        prompt_template = get_prompt_group("chat_workflow.social_interaction")
        user_prompt = prompt_template["user"].format(query=state.query.text)
        messages = [
            {"role": "system", "content": prompt_template["system"]},
            {"role": "user", "content": user_prompt},
        ]
        if state.contexts.chat_history:
            recent_messages = state.contexts.chat_history[-10:]  # Last 10 messages
            for msg in recent_messages:
                messages.insert(1, {"role": msg.role, "content": msg.content})

        # Use streaming generation
        full_content = ""
        chunk_index = 0
        async for chunk in generate_stream_for_agent(messages):
            if chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if hasattr(delta, "content") and delta.content:
                    full_content += delta.content
                    # Emit streaming chunk event
                    await self.streaming_manager.emit(
                        StreamEvent(
                            type=EventType.STREAM_CHUNK,
                            content=delta.content,
                            stage=WorkflowStage.INTENT_ANALYSIS,
                            progress=0.5,
                            metadata={"index": chunk_index},
                        )
                    )
                    chunk_index += 1

        state.execution_result = ExecutionResult(
            success=True,
            plan=ExecutionPlan(),
            outputs=[full_content],
            metadata={"type": "simple_chat"},
        )
        await self.streaming_manager.emit(
            StreamEvent(
                type=EventType.DONE, content="Reply generated", stage=WorkflowStage.INTENT_ANALYSIS
            )
        )
        state.final_content = full_content
        state.update_stage(WorkflowStage.COMPLETED)
        return state

    async def _enhance_complex_query(
        self, state: WorkflowState, query_type: QueryType
    ) -> WorkflowState:
        """Analyze complex queries"""
        enhancement_results = await self._execute_enhancement_tools(state.query.text)
        prompt_template = get_prompt_group("chat_workflow.intent_analysis")
        chat_history = []
        if state.contexts.chat_history:
            recent_messages = state.contexts.chat_history[-10:]  # Last 10 messages
            for msg in recent_messages:
                chat_history.insert(1, {"role": msg.role, "content": msg.content})

        current_time = datetime.now()
        user_prompt = prompt_template["user"].format(
            query=state.query.text,
            current_time=current_time.strftime("%Y-%m-%d %H:%M:%S"),
            chat_history=json.dumps(chat_history, ensure_ascii=False),
            enhancement_results=(
                json.dumps(enhancement_results, ensure_ascii=False) if enhancement_results else ""
            ),
            selected_content=state.query.selected_content if state.query.selected_content else "",
            document_id=state.query.document_id if state.query.document_id else "",
        )
        messages = [
            {"role": "system", "content": prompt_template["system"]},
            {"role": "user", "content": user_prompt},
        ]
        response = await generate_with_messages_async(
            messages,
            thinking="disabled",
        )
        response = response.strip().lower()
        state.intent = Intent(
            original_query=state.query.text,
            query_type=query_type,
            enhanced_query=response or state.query.text,
        )

    async def _execute_enhancement_tools(self, query: str) -> Dict[str, Any]:
        """Execute entity enhancement tools - use LLM to extract entities and find them via profile_tool"""
        results = {
            "extracted_entities": [],
            "found_entities": [],
        }

        try:
            extracted_entities = await self._extract_entities_from_query(query)
            results["extracted_entities"] = extracted_entities

            if not extracted_entities:
                return results

            from opencontext.tools.profile_tools.profile_entity_tool import ProfileEntityTool

            profile_tool = ProfileEntityTool()

            # Directly call the match_entity function of ProfileEntityTool
            for entity_name in extracted_entities:
                matched_name, context = profile_tool.match_entity(entity_name)
                if context and context.metadata:
                    entity_data = {"entity_name": entity_name}
                    entity_data.update(context.metadata)
                    results["found_entities"].append(entity_data)
            return results

        except Exception as e:
            self.logger.warning(f"Entity enhancement failed: {e}")
            return results

    async def _extract_entities_from_query(self, query: str) -> List[str]:
        """Use LLM to extract entities from the query"""
        try:
            from opencontext.config.global_config import get_prompt_group
            from opencontext.utils.json_parser import parse_json_from_response

            prompt_template = get_prompt_group("entity_processing.entity_extraction")

            messages = [
                {"role": "system", "content": prompt_template["system"]},
                {"role": "user", "content": prompt_template["user"].format(text=query)},
            ]

            response = await generate_with_messages_async(
                messages, thinking="disabled"
            )

            result = parse_json_from_response(response.strip())
            entities = []
            self.logger.info(f"Entity extraction raw result: {result}")
            # Extract entity names from the result
            if isinstance(result, dict) and "entities" in result:
                for entity in result["entities"]:
                    if isinstance(entity, dict) and "name" in entity:
                        entities.append(entity["name"])
                    elif isinstance(entity, str):
                        entities.append(entity)
            elif isinstance(result, list):
                for item in result:
                    if isinstance(item, dict) and "name" in item:
                        entities.append(item["name"])
                    elif isinstance(item, str):
                        entities.append(item)

            return entities

        except Exception as e:
            self.logger.warning(f"Entity extraction failed: {e}")
            return []
