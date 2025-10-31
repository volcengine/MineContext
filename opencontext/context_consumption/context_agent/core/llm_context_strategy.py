#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
LLM-based context collection strategy
Use large language models to intelligently analyze user needs and decide which retrieval tools to call
"""

import asyncio
import json
from datetime import datetime
from math import log
from typing import Any, Dict, List, Optional, Set

from opencontext.config.global_config import get_prompt_group
from opencontext.llm.global_vlm_client import generate_for_agent_async, generate_with_messages_async
from opencontext.tools.tool_definitions import (
    ALL_PROFILE_TOOL_DEFINITIONS,
    ALL_RETRIEVAL_TOOL_DEFINITIONS,
    WEB_SEARCH_TOOL_DEFINITION,
)
from opencontext.tools.tools_executor import ToolsExecutor
from opencontext.utils.json_parser import parse_json_from_response
from opencontext.utils.logging_utils import get_logger

from ..models.enums import ContextSufficiency, DataSource
from ..models.schemas import ContextCollection, ContextItem, Intent


class LLMContextStrategy:
    """LLM-based context collection strategy"""

    def __init__(self):
        self.tools_executor = ToolsExecutor()
        self.logger = get_logger(self.__class__.__name__)

        # Toolset configuration
        self.retrieval_tools = ALL_RETRIEVAL_TOOL_DEFINITIONS
        self.entity_tools = ALL_PROFILE_TOOL_DEFINITIONS
        self.web_search_tool = WEB_SEARCH_TOOL_DEFINITION
        self.all_tools = self.retrieval_tools + self.entity_tools + self.web_search_tool

    async def analyze_and_plan_tools(
        self, intent: Intent, existing_context: ContextCollection, iteration: int = 1
    ) -> tuple[List[Dict[str, Any]], Dict[str, str]]:
        """
        Analyze user intent and existing context to decide which tools to call
        Returns:
            Tuple of (tool_calls, analysis_message_dict)
        """
        # Build analysis prompt
        prompts = get_prompt_group("chat_workflow.context_collection.tool_analysis")
        system_prompt = prompts.get("system", "")
        user_template = prompts.get("user", "")

        # Format user prompt
        context_summary = self._get_context_summary(existing_context)
        user_prompt = user_template.format(
            original_query=intent.original_query,
            enhanced_query=intent.enhanced_query or "None",
            query_type=intent.query_type.value if intent.query_type else "Unknown",
            context_summary=context_summary,
            current_date=datetime.now().strftime("%Y-%m-%d"),
            current_timestamp=int(datetime.now().timestamp()),
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        response = await generate_for_agent_async(
            messages=messages,
            tools=self.all_tools,
            # thinking="disabled",
        )

        # Extract tool calls from the response
        tool_calls = self._extract_tool_calls_from_response(response)

        self.logger.info(
            f"LLM decided to call {len(tool_calls)} tools: {[call.get('function', {}).get('name') for call in tool_calls]}"
        )

        # Build analysis message for conversation history
        tool_call_summary = [
            {
                "tool": call.get("function", {}).get("name"),
                "params": call.get("function", {}).get("arguments", {}),
            }
            for call in tool_calls
        ]
        analysis_message = {
            "role": "assistant",
            "content": f"Iteration {iteration} analysis: Planning to call {len(tool_calls)} tools:\n{json.dumps(tool_call_summary, ensure_ascii=False, indent=2)}",
        }

        return tool_calls, analysis_message

    def _get_context_summary(self, context: ContextCollection) -> str:
        """Get context summary"""
        summary_lines = []

        # Add current document information
        # if context.current_document:
        #     doc = context.current_document
        #     doc_info = f"Current Document: {doc.title or 'Untitled'}"
        #     if doc.id:
        #         doc_info += f" (ID: {doc.id})"
        #     summary_lines.append(doc_info)

        # Add selected content information
        if context.selected_content:
            summary_lines.append(f"Selected Content: {context.selected_content}")

        # Add chat history information
        if context.chat_history:
            chat_history = []
            for message in context.chat_history:
                chat_history.append(f"{message.role}: {message.content}")
            summary_lines.append(f"Chat History: \n" + "\n".join(chat_history))

        if context.items:
            sources = {}
            for item in context.items:
                source = item.source.value
                if source not in sources:
                    sources[source] = 0
                sources[source] += 1

            summary_lines.append("Collected Context Items:")
            for source, count in sources.items():
                summary_lines.append(f"  - {source}: {count} items")

        return "\n".join(summary_lines) if summary_lines else "No existing context"

    async def evaluate_sufficiency(
        self, contexts: ContextCollection, intent: Intent
    ) -> ContextSufficiency:
        """
        Evaluate whether the context is sufficient to meet user needs
        """
        prompts = get_prompt_group("chat_workflow.context_collection.sufficiency_evaluation")
        system_prompt = prompts.get("system", "")
        user_template = prompts.get("user", "")

        # Format user prompt
        context_summary = self._get_detailed_context_summary(contexts)
        user_prompt = user_template.format(
            original_query=intent.original_query,
            enhanced_query=intent.enhanced_query or "None",
            context_count=len(contexts.items),
            context_summary=context_summary,
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        # Use normal text generation, no tool calls needed
        response = await generate_with_messages_async(
            messages=messages,
            enable_executor=False,
            thinking="disabled",
        )
        # Parse sufficiency evaluation
        response_upper = response.upper()
        self.logger.info(f"evaluate_sufficiency {response_upper}")
        if "SUFFICIENT" == response_upper:
            return ContextSufficiency.SUFFICIENT
        elif "PARTIAL" == response_upper:
            return ContextSufficiency.PARTIAL
        else:
            return ContextSufficiency.INSUFFICIENT

    def _get_detailed_context_summary(self, context: ContextCollection) -> str:
        """Get a detailed context summary"""
        if not context.items:
            return "No context information"

        summary_lines = []
        for i, item in enumerate(context.items):  # Show only the first 10 items
            title = item.title or ""
            content_preview = item.content
            summary_lines.append(f"{i+1}. [{item.source.value}] {title}: {content_preview}")

        if len(context.items) > 10:
            summary_lines.append(f"... and {len(context.items) - 10} more items")

        return "\n".join(summary_lines)

    def _extract_tool_calls_from_response(self, response) -> List[Dict[str, Any]]:
        """
        Extract tool calls from the LLM response object

        Args:
            response: LLM response object, containing choices[0].message.tool_calls

        Returns:
            List of tool call dictionaries
        """
        try:
            message = response.choices[0].message
            if not hasattr(message, "tool_calls") or not message.tool_calls:
                return []

            tool_calls = []
            for tc in message.tool_calls:
                tool_call = {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": parse_json_from_response(tc.function.arguments),
                    },
                }
                tool_calls.append(tool_call)

            return tool_calls

        except Exception as e:
            self.logger.exception(f"Failed to extract tool calls: {e}")
            return []

    async def execute_tool_calls_parallel(
        self, tool_calls: List[Dict[str, Any]]
    ) -> List[ContextItem]:
        """
        Execute tool calls concurrently and convert the results to ContextItem
        """
        if not tool_calls:
            return []

        tasks = []
        for call in tool_calls:
            function_name = call.get("function", {}).get("name")
            function_args = call.get("function", {}).get("arguments", {})
            # self.logger.info(f"Tool call {function_name} args {function_args}")
            if function_name:
                task = self.tools_executor.run_async(function_name, function_args)
                tasks.append((function_name, task))

        # Execute concurrently
        results = []
        if tasks:
            completed_tasks = await asyncio.gather(
                *[task for _, task in tasks], return_exceptions=True
            )

            for i, result in enumerate(completed_tasks):
                function_name = tasks[i][0]

                if isinstance(result, Exception):
                    self.logger.error(f"Tool call failed {function_name}: {result}")
                    continue

                # Convert tool execution result to ContextItem
                context_items = self._convert_tool_result_to_context_items(function_name, result)
                results.extend(context_items)
        return results

    def _convert_tool_result_to_context_items(
        self, tool_name: str, tool_result: Any
    ) -> List[ContextItem]:
        """
        Convert tool execution result to a list of ContextItems
        """
        context_items = []

        try:
            # Convert based on tool type and result format
            if isinstance(tool_result, list):
                # If the result is a list, process each item
                for item in tool_result:
                    if isinstance(item, dict):
                        context_item = self._dict_to_context_item(tool_name, item)
                        if context_item:
                            context_items.append(context_item)

            elif isinstance(tool_result, dict):
                # If the result is a dictionary
                if "results" in tool_result:
                    # If there is a results field, process the results
                    for item in tool_result.get("results", []):
                        context_item = self._dict_to_context_item(tool_name, item)
                        if context_item:
                            context_items.append(context_item)
                else:
                    # Convert the dictionary directly
                    context_item = self._dict_to_context_item(tool_name, tool_result)
                    if context_item:
                        context_items.append(context_item)

        except Exception as e:
            self.logger.error(f"Failed to convert tool result {tool_name}: {e}")

        return context_items

    def _dict_to_context_item(self, tool_name: str, item_dict: dict) -> Optional[ContextItem]:
        """Convert a dictionary to a ContextItem"""
        try:
            # Try to extract information from the dictionary
            content = item_dict.get("context") or item_dict.get("content") or str(item_dict)
            title = item_dict.get("title") or f"{tool_name} result"
            relevance_score = item_dict.get("similarity_score") or item_dict.get(
                "relevance_score", 1.0
            )

            # Infer data source from tool name
            source = self._infer_data_source(tool_name)

            return ContextItem(
                source=source,
                content=content,
                title=title,
                relevance_score=relevance_score,
                timestamp=datetime.now(),
                metadata={"tool_name": tool_name, "original_data": item_dict},
            )

        except Exception as e:
            self.logger.error(f"Failed to convert dictionary to ContextItem: {e}")
            return None

    def _infer_data_source(self, tool_name: str) -> DataSource:
        """Infer data source from tool name"""
        tool_name_lower = tool_name.lower()

        if "document" in tool_name_lower:
            return DataSource.DOCUMENT
        elif "web" in tool_name_lower or "search" in tool_name_lower:
            return DataSource.WEB_SEARCH
        elif "entity" in tool_name_lower:
            return DataSource.ENTITY
        elif "processed" in tool_name_lower or "context" in tool_name_lower:
            return DataSource.PROCESSED
        else:
            return DataSource.UNKNOWN

    async def validate_and_filter_tool_results(
        self,
        tool_calls: List[Dict[str, Any]],
        tool_results: List[ContextItem],
        intent: Intent,
        existing_context: ContextCollection,
    ) -> tuple[List[ContextItem], Dict[str, str]]:
        """
        Validate tool results and filter relevant context items
        Returns:
            Tuple of (relevant_context_items, validation_message_dict)
        """
        if not tool_results:
            message = {"role": "assistant", "content": "No tool results to validate."}
            return [], message

        # Build validation prompt
        prompts = get_prompt_group("chat_workflow.context_collection.tool_result_validation")
        system_prompt = prompts.get("system", "")
        user_template = prompts.get("user", "")

        # Format tool calls summary
        # tool_calls_summary = []
        # for call in tool_calls:
        #     tool_calls_summary.append({
        #         "tool_name": call.get("function", {}).get("name"),
        #         "parameters": call.get("function", {}).get("arguments", {})
        #     })

        # Format tool results summary
        results_summary = []
        for idx, item in enumerate(tool_results):
            results_summary.append(
                {
                    "result_id": item.id,
                    "index": idx,
                    "source": item.source.value,
                    "content": item.content,
                }
            )

        user_prompt = user_template.format(
            original_query=intent.original_query,
            enhanced_query=intent.enhanced_query,
            # tool_calls=json.dumps(tool_calls_summary, ensure_ascii=False, indent=2),
            tool_results=json.dumps(results_summary, ensure_ascii=False, indent=2),
        )

        # Build messages with conversation history from existing context
        # System message must be first, then conversation history, then current request
        messages = [{"role": "system", "content": system_prompt}]

        # Add user's chat history to give LLM context awareness
        # if existing_context.chat_history:
        #     recent_messages = existing_context.chat_history[-10:]  # Last 10 messages
        #     for msg in recent_messages:
        #         messages.append({"role": msg.role, "content": msg.content})

        messages.append({"role": "user", "content": user_prompt})

        try:
            response = await generate_with_messages_async(
                messages=messages,
                thinking="disabled",
            )

            # Parse validation result
            validation_result = parse_json_from_response(response)

            # Extract relevant result IDs

            # Fallback: if no valid IDs found, return all results to avoid data loss
            if "relevant_result_ids" not in validation_result:
                self.logger.warning(
                    "No relevant_result_ids found in validation response. "
                    "Returning all results as fallback."
                )
                relevant_items = tool_results
            else:
                relevant_ids = set(validation_result.get("relevant_result_ids", []))
                # Filter relevant context items
                relevant_items = [item for item in tool_results if item.id in relevant_ids]
                # self.logger.info(f"Filtered to {len(relevant_items)}/{len(tool_results)} relevant items")

            # Build validation message for conversation history
            validation_message = {
                "role": "assistant",
                "content": f"Filtered {len(relevant_items)}/{len(tool_results)} relevant results",
            }

            return relevant_items, validation_message

        except Exception as e:
            self.logger.error(f"Tool result validation failed: {e}")
            # On failure, return all results and error message
            error_message = {
                "role": "assistant",
                "content": f"Validation failed: {str(e)}. Keeping all results.",
            }
            return tool_results, error_message
