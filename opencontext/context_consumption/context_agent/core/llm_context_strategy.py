#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
LLM-based context collection strategy
Use large language models to intelligently analyze user needs and decide which retrieval tools to call
"""

from typing import List, Dict, Any, Optional, Set
import json
import asyncio
from datetime import datetime

from opencontext.llm.global_vlm_client import generate_with_messages_async, generate_for_agent_async
from opencontext.tools.tools_executor import ToolsExecutor
from opencontext.tools.tool_definitions import ALL_RETRIEVAL_TOOL_DEFINITIONS, ALL_PROFILE_TOOL_DEFINITIONS, WEB_SEARCH_TOOL_DEFINITION
from opencontext.config.global_config import get_prompt_group
from ..models.enums import ContextSufficiency, DataSource
from ..models.schemas import ContextCollection, Intent, ContextItem
from opencontext.utils.logging_utils import get_logger
from opencontext.utils.json_parser import parse_json_from_response


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
        self,
        intent: Intent,
        existing_context: ContextCollection,
        max_tools: int = 5,
        iteration: int = 1,
        tool_history: List[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        Analyze user intent and existing context to decide which tools to call
        
        Returns:
            List of tool calls in OpenAI function calling format
        """
        # Build analysis prompt
        prompts = get_prompt_group("chat_workflow.context_collection.tool_analysis")
        system_prompt = prompts.get("system", "")
        user_template = prompts.get("user", "")
        
        # Format user prompt
        context_summary = self._get_enhanced_context_summary(existing_context, tool_history)
        user_prompt = user_template.format(
            original_query=intent.original_query,
            enhanced_query=intent.enhanced_query or 'None',
            query_type=intent.query_type.value if intent.query_type else 'Unknown',
            context_summary=context_summary,
            max_tools=max_tools,
            current_date=datetime.now().strftime("%Y-%m-%d"),
            current_timestamp=datetime.now().timestamp(),
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        response = await generate_for_agent_async(
            messages=messages,
            tools=self.all_tools,
            thinking="disabled",
        )
        
        # Extract tool calls from the response
        tool_calls = self._extract_tool_calls_from_response(response)
        
        self.logger.info(f"LLM decided to call {len(tool_calls)} tools: {[call.get('function', {}).get('name') for call in tool_calls]}")
        
        return tool_calls
    
    def _get_enhanced_context_summary(self, context: ContextCollection, tool_history: List[Dict] = None) -> str:
        """Get an enhanced context summary, including tool call history"""
        if not context.items and not tool_history:
            return "No existing context"
            
        summary_lines = []
        
        # Existing context statistics
        if context.items:
            sources = {}
            topics = set()
            for item in context.items:
                source = item.source.value
                if source not in sources:
                    sources[source] = 0
                sources[source] += 1
                # Extract topics (from title)
                if item.title:
                    topics.add(item.title[:30])
            
            summary_lines.append(f"Existing {len(context.items)} context items:")
            for source, count in sources.items():
                summary_lines.append(f"- {source}: {count} items")
            
            if topics:
                summary_lines.append(f"\nCovered topics: {', '.join(list(topics)[:5])}")
        
        # Tool call history
        if tool_history:
            summary_lines.append(f"\nExecuted tool calls:")
            for call in tool_history[-5:]:  # Show the last 5 calls
                tool_name = call.get("tool_name", "")
                query = call.get("query", "")
                summary_lines.append(f"- {tool_name}: {query[:50]}...")
        
        return "\n".join(summary_lines)
    
    async def evaluate_sufficiency(
        self,
        contexts: ContextCollection,
        intent: Intent
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
            enhanced_query=intent.enhanced_query or 'None',
            context_count=len(contexts.items),
            context_summary=context_summary
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
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


    def _get_context_summary(self, context: ContextCollection) -> str:
        """Get context summary"""
        if not context.items:
            return "No existing context"
            
        sources = {}
        for item in context.items:
            source = item.source.value
            if source not in sources:
                sources[source] = 0
            sources[source] += 1
            
        summary_lines = []
        for source, count in sources.items():
            summary_lines.append(f"- {source}: {count} items")
            
        return f"Existing {len(context.items)} context items:\n" + "\n".join(summary_lines)

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
            if not hasattr(message, 'tool_calls') or not message.tool_calls:
                return []
            
            tool_calls = []
            for tc in message.tool_calls:
                tool_call = {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": parse_json_from_response(tc.function.arguments)
                    }
                }
                tool_calls.append(tool_call)
                
            return tool_calls
            
        except Exception as e:
            self.logger.exception(f"Failed to extract tool calls: {e}")
            return []

    async def execute_tool_calls_parallel(
        self,
        tool_calls: List[Dict[str, Any]]
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
            
            if function_name:
                task = self.tools_executor.run_async(function_name, function_args)
                tasks.append((function_name, task))
        
        # Execute concurrently
        results = []
        if tasks:
            completed_tasks = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
            
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
        self,
        tool_name: str,
        tool_result: Any
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
            relevance_score = item_dict.get("similarity_score") or item_dict.get("relevance_score", 1.0)
            
            # Infer data source from tool name
            source = self._infer_data_source(tool_name)
            
            return ContextItem(
                source=source,
                content=content,
                title=title,
                relevance_score=relevance_score,
                timestamp=datetime.now(),
                metadata={
                    "tool_name": tool_name,
                    "original_data": item_dict
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to convert dictionary to ContextItem: {e}")
            return None

    async def filter_duplicate_calls(
        self,
        new_calls: List[Dict[str, Any]],
        tool_history: List[Dict] = None
    ) -> List[Dict[str, Any]]:
        """Filter out duplicate tool calls"""
        if not tool_history:
            return new_calls
        
        filtered_calls = []
        for call in new_calls:
            func_name = call.get("function", {}).get("name")
            func_args = call.get("function", {}).get("arguments", {})
            
            # Handle the case where func_args might be a list
            if isinstance(func_args, list):
                # If it's a list, try to get the query from the first element
                query = func_args[0].get("query", "") if func_args else ""
            else:
                # If it's a dictionary, get the query directly
                query = func_args.get("query", "")
            
            # Check for similar queries from the same tool
            is_duplicate = False
            for history in tool_history:
                if history.get("tool_name") == func_name:
                    hist_query = history.get("query", "")
                    # Simple similarity check (can be improved)
                    if query.lower() == hist_query.lower() or (
                        len(query) > 10 and query[:10].lower() == hist_query[:10].lower()
                    ):
                        self.logger.info(f"Filtering duplicate call: {func_name} with query: {query[:50]}")
                        is_duplicate = True
                        break
            
            if not is_duplicate:
                filtered_calls.append(call)
        
        return filtered_calls
    
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

    async def filter_relevant_contexts(
        self, 
        context_items: List,  # List of ContextItem objects
        query: str
    ) -> List[str]:
        """Let LLM determine which contexts are useful for answering the query
        
        Args:
            context_items: List of ContextItem objects
            query: User query
            
        Returns:
            List of relevant ContextItem.id
        """
        if not context_items:
            return []
        
        # Build context summary
        prompts = get_prompt_group("chat_workflow.context_collection.context_filter")
        context_list = []
        for ctx in context_items:
            # Use the real id of the ContextItem
            content = f"title: {ctx.title or 'N/A'}\ncontent: {ctx.content[:400]}"
            
            context_summary = {
                "id": ctx.id,  # Use the real id of the ContextItem
                "content": content
            }
            context_list.append(context_summary)
        
        prompt = prompts.get("user", "").format(
            query=query,
            context_list=json.dumps(context_list, ensure_ascii=False, indent=2)
        )
        
        try:
            response = await generate_with_messages_async(
                messages=[
                    {"role": "system", "content": prompts.get("system", "")},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                thinking="disabled",
            )
            
            # Parse the returned ID list
            response = response.strip()
            if response.startswith('[') and response.endswith(']'):
                try:
                    relevant_ids = parse_json_from_response(response)
                    
                    # Validate that the returned IDs are in the list of valid IDs
                    valid_ids = [ctx.id for ctx in context_items]
                    filtered_ids = [id for id in relevant_ids if id in valid_ids]
                    
                    self.logger.info(f"Context filtering: {len(context_items)} original, {len(filtered_ids)} relevant contexts kept")
                    return filtered_ids
                except json.JSONDecodeError:
                    self.logger.error(f"Failed to parse LLM response, content: {response}")
                    return [ctx.id for ctx in context_items]  # Keep all contexts on failure
            else:
                self.logger.warning(f"LLM returned incorrect format: {response}")
                return [ctx.id for ctx in context_items]  # Keep all contexts on failure
                
        except Exception as e:
            self.logger.error(f"Context filtering failed: {e}")
            return [ctx.id for ctx in context_items]  # Keep all contexts on failure