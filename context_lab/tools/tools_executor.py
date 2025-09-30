# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

from typing import Any, Dict, List, Union
from context_lab.config import GlobalConfig
from context_lab.tools.retrieval_tools import *
from context_lab.tools.profile_tools import ProfileEntityTool
from context_lab.tools.operation_tools import *
from context_lab.tools.base import BaseTool
import asyncio, json

from context_lab.tools.retrieval_tools.document_retrieval_tool import DocumentRetrievalTool


class ToolsExecutor:
    def __init__(self):
        # 为了向后兼容保留storage参数，但不使用它
        
        self._tools_map: Dict[str, Union[BaseTool]] = {
            TextSearchTool.get_name(): TextSearchTool(),
            FilterContextTool.get_name(): FilterContextTool(),
            DocumentRetrievalTool.get_name(): DocumentRetrievalTool(),
            
            # Profile工具 - 统一的实体管理工具
            ProfileEntityTool.get_name(): ProfileEntityTool(),
            
            # 操作工具 - 现在使用无参构造函数
            WebSearchTool.get_name(): WebSearchTool(),
            SQLiteOperationsTool.get_name(): SQLiteOperationsTool(),
        }
    
    async def run_async(self, tool_name: str, tool_input: Dict[str, Any]) -> Any:
        if tool_name in self._tools_map:
            tool = self._tools_map[tool_name]
            
            # 处理输入参数：如果tool_input是一个包含单个字典的列表，则提取字典
            if isinstance(tool_input, list) and len(tool_input) == 1 and isinstance(tool_input[0], dict):
                tool_input = tool_input[0]
            
            # 确保tool_input是字典类型
            if not isinstance(tool_input, dict):
                return {
                    "error": f"工具参数格式错误: 期望dict，得到{type(tool_input).__name__}",
                    "message": "工具参数必须是字典格式",
                    "received_type": type(tool_input).__name__
                }
            
            return tool.execute(**tool_input)
        else:
            # 记录未知工具调用但不抛出异常，返回警告信息
            import logging
            from difflib import get_close_matches
            logger = logging.getLogger(__name__)
            
            # 提供相似的工具名称建议
            available_tools = list(self._tools_map.keys())
            suggestions = get_close_matches(tool_name, available_tools, n=3, cutoff=0.6)
            suggestion_text = f"建议的工具: {', '.join(suggestions)}" if suggestions else ""
            
            error_msg = f"未知工具: {tool_name}。{suggestion_text}"
            available_tools_text = f"可用工具: {', '.join(available_tools[:10])}" + ("..." if len(available_tools) > 10 else "")
            return {
                "error": error_msg,
                "message": "该工具不存在，请使用系统提供的工具",
                "available_tools": available_tools_text,
                "suggestions": suggestions
            }
    
    def run(self, tool_name: str, tool_input: Dict[str, Any]) -> Any:
        if tool_name in self._tools_map:
            tool = self._tools_map[tool_name]
            
            # 处理输入参数：如果tool_input是一个包含单个字典的列表，则提取字典
            if isinstance(tool_input, list) and len(tool_input) == 1 and isinstance(tool_input[0], dict):
                tool_input = tool_input[0]
            
            # 确保tool_input是字典类型
            if not isinstance(tool_input, dict):
                return {
                    "error": f"工具参数格式错误: 期望dict，得到{type(tool_input).__name__}",
                    "message": "工具参数必须是字典格式",
                    "received_type": type(tool_input).__name__
                }
            
            return tool.execute(**tool_input)
        else:
            # 记录未知工具调用但不抛出异常，返回警告信息
            import logging
            from difflib import get_close_matches
            logger = logging.getLogger(__name__)
            
            # 提供相似的工具名称建议
            available_tools = list(self._tools_map.keys())
            suggestions = get_close_matches(tool_name, available_tools, n=3, cutoff=0.6)
            suggestion_text = f"建议的工具: {', '.join(suggestions)}" if suggestions else ""
            
            error_msg = f"未知工具: {tool_name}。{suggestion_text}"
            available_tools_text = f"可用工具: {', '.join(available_tools[:10])}" + ("..." if len(available_tools) > 10 else "")
            return {
                "error": error_msg,
                "message": "该工具不存在，请使用系统提供的工具",
                "available_tools": available_tools_text,
                "suggestions": suggestions
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
