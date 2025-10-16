# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

import asyncio
import json
from typing import Any, Dict, List, Union

from opencontext.config import GlobalConfig
from opencontext.tools.base import BaseTool
from opencontext.tools.operation_tools import *
from opencontext.tools.profile_tools import ProfileEntityTool
from opencontext.tools.retrieval_tools import *


class ToolsExecutor:
    def __init__(self):
        self._tools_map: Dict[str, Union[BaseTool]] = {
            # Context retrieval tools
            ActivityContextTool.get_name(): ActivityContextTool(),
            IntentContextTool.get_name(): IntentContextTool(),
            SemanticContextTool.get_name(): SemanticContextTool(),
            ProceduralContextTool.get_name(): ProceduralContextTool(),
            StateContextTool.get_name(): StateContextTool(),
            # Document retrieval tools
            GetDailyReportsTool.get_name(): GetDailyReportsTool(),
            GetActivitiesTool.get_name(): GetActivitiesTool(),
            GetTipsTool.get_name(): GetTipsTool(),
            GetTodosTool.get_name(): GetTodosTool(),
            # Profile tools
            ProfileEntityTool.get_name(): ProfileEntityTool(),
            # Operation tools
            WebSearchTool.get_name(): WebSearchTool(),
        }

    async def run_async(self, tool_name: str, tool_input: Dict[str, Any]) -> Any:
        if tool_name in self._tools_map:
            tool = self._tools_map[tool_name]

            if (
                isinstance(tool_input, list)
                and len(tool_input) == 1
                and isinstance(tool_input[0], dict)
            ):
                tool_input = tool_input[0]

            # Ensure tool_input is dictionary type
            if not isinstance(tool_input, dict):
                return {
                    "error": f"Tool parameter format error: expected dict, got {type(tool_input).__name__}",
                    "message": "Tool parameters must be in dictionary format",
                    "received_type": type(tool_input).__name__,
                }

            return tool.execute(**tool_input)
        else:
            # Log unknown tool call but don't throw exception, return warning message
            import logging
            from difflib import get_close_matches

            logger = logging.getLogger(__name__)

            # Provide similar tool name suggestions
            available_tools = list(self._tools_map.keys())
            suggestions = get_close_matches(tool_name, available_tools, n=3, cutoff=0.6)
            suggestion_text = f"Suggested tools: {', '.join(suggestions)}" if suggestions else ""

            error_msg = f"Unknown tool: {tool_name}. {suggestion_text}"
            available_tools_text = f"Available tools: {', '.join(available_tools[:10])}" + (
                "..." if len(available_tools) > 10 else ""
            )
            return {
                "error": error_msg,
                "message": "This tool does not exist, please use system-provided tools",
                "available_tools": available_tools_text,
                "suggestions": suggestions,
            }

    def run(self, tool_name: str, tool_input: Dict[str, Any]) -> Any:
        if tool_name in self._tools_map:
            tool = self._tools_map[tool_name]

            # Process input parameters: if tool_input is a list containing a single dictionary, extract the dictionary
            if (
                isinstance(tool_input, list)
                and len(tool_input) == 1
                and isinstance(tool_input[0], dict)
            ):
                tool_input = tool_input[0]

            # Ensure tool_input is dictionary type
            if not isinstance(tool_input, dict):
                return {
                    "error": f"Tool parameter format error: expected dict, got {type(tool_input).__name__}",
                    "message": "Tool parameters must be in dictionary format",
                    "received_type": type(tool_input).__name__,
                }

            return tool.execute(**tool_input)
        else:
            # Log unknown tool call but don't throw exception, return warning message
            import logging
            from difflib import get_close_matches

            logger = logging.getLogger(__name__)

            # Provide similar tool name suggestions
            available_tools = list(self._tools_map.keys())
            suggestions = get_close_matches(tool_name, available_tools, n=3, cutoff=0.6)
            suggestion_text = f"Suggested tools: {', '.join(suggestions)}" if suggestions else ""

            error_msg = f"Unknown tool: {tool_name}. {suggestion_text}"
            available_tools_text = f"Available tools: {', '.join(available_tools[:10])}" + (
                "..." if len(available_tools) > 10 else ""
            )
            return {
                "error": error_msg,
                "message": "This tool does not exist, please use system-provided tools",
                "available_tools": available_tools_text,
                "suggestions": suggestions,
            }

    async def batch_run_tools_async(self, tool_calls: List[Dict[str, Any]]) -> Any:
        results = []
        tool_call_info = []
        tasks = []
        for tc in tool_calls:
            function_name = tc.function.name
            function_args = json.loads(tc.function.arguments)
            tasks.append(self.run_async(function_name, function_args))
            tool_call_info.append((tc.id, function_name))

        res = await asyncio.gather(*tasks)
        for i, r in enumerate(res):
            results.append((tool_call_info[i][0], tool_call_info[i][1], r))
        return results
