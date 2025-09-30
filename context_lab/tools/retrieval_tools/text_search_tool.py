# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
文本语义搜索工具
支持使用自然语言查询进行语义搜索，返回相关的上下文记录
"""

from typing import Any, Dict, List
from context_lab.tools.retrieval_tools.base_retrieval_tool import BaseRetrievalTool, RetrievalToolFilter, TimeRangeFilter
from context_lab.models.enums import ContextType, ContextSimpleDescriptions, get_context_type_options
from context_lab.models.context import Vectorize
from context_lab.utils.logging_utils import get_logger

logger = get_logger(__name__)


class TextSearchTool(BaseRetrievalTool):
    """文本语义搜索工具"""
    
    def __init__(self):
        super().__init__()
    
    @classmethod
    def get_name(cls) -> str:
        return "text_search"
    
    @classmethod
    def get_description(cls) -> str:
        """动态生成工具描述，包含所有支持的上下文类型"""
        context_descriptions = []
        for context_type in ContextType:
            desc_info = ContextSimpleDescriptions[context_type]
            context_descriptions.append(f"- {context_type.value}: {desc_info['description']}")
        descriptions_text = '\n'.join(context_descriptions)
        return f"""使用自然语言查询进行智能语义搜索，基于向量相似度匹配从指定类型的上下文记录中找到最相关的内容。适用于模糊查询、概念搜索、内容理解等场景，能够理解查询意图并返回语义相关的结果。支持时间范围过滤、实体筛选等高级功能。支持以下上下文类型：\n{descriptions_text}"""
    
    @classmethod
    def get_parameters(cls) -> Dict[str, Any]:
        """获取工具参数定义"""
        # 动态生成context_type的描述
        context_descriptions = []
        for context_type in ContextType:
            desc_info = ContextSimpleDescriptions[context_type]
            context_descriptions.append(f"- {context_type.value}: {desc_info['description']}. {desc_info['purpose']}")
        context_type_desc = "上下文类型的详细描述：\n" + '\n'.join(context_descriptions)

        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "用于语义搜索的自然语言查询文本"
                },
                "context_type": {
                    "type": "string",
                    "enum": get_context_type_options(),
                    "description": context_type_desc
                },
                "entities": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "实体列表，用于过滤包含特定实体的记录（如人名、项目名、概念名等）"
                },
                "time_range": {
                    "type": "object",
                    "properties": {
                        "start": {"type": "integer", "description": "开始时间的秒级时间戳，若无限制则不填"},
                        "end": {"type": "integer", "description": "结束时间的秒级时间戳，若无限制则不填"},
                        "timezone": {"type": "string", "default": "local"},
                        "time_type": {
                            "type": "string", 
                            "enum": ["create_time_ts", "update_time_ts", "event_time_ts"], 
                            "default": "event_time_ts",
                            "description": "根据query选择合适的时间类型"
                        }
                    },
                    "description": "时间范围过滤"
                },
                "top_k": {
                    "type": "integer",
                    "default": 20,
                    "minimum": 1,
                    "maximum": 100,
                    "description": "返回结果数量"
                }
            },
            "required": ["query", "context_type"]
        }
    
    def execute(self, **kwargs) -> List[Dict[str, Any]]:
        """执行语义搜索"""
        query = kwargs.get("query")
        context_type_str = kwargs.get("context_type")
        entities = kwargs.get("entities", [])
        time_range = kwargs.get("time_range")
        top_k = kwargs.get("top_k", 20)
        
        # 验证必需参数
        if not query:
            return [{"error": "query参数是必需的"}]
        
        if not context_type_str or context_type_str not in get_context_type_options():
            return [{
                "error": f"Invalid context_type: {context_type_str}. Must be one of: {', '.join(get_context_type_options())}"
            }]
        filters = RetrievalToolFilter()
        filters.entities = entities
        
        if time_range:
            filters.time_range = TimeRangeFilter(**time_range)
        
        try:
            vectorize = Vectorize(text=query)
            search_results = self.storage.search(
                query=vectorize,
                context_types=[context_type_str],
                filters=self._build_filters(filters),
                top_k=top_k
            )
            formatted_results = self._format_results(search_results)
            for result in formatted_results:
                result["context_type"] = context_type_str
                context_desc = ContextSimpleDescriptions.get(ContextType(context_type_str), {})
                if context_desc:
                    result["context_description"] = context_desc.get("description", "")
            return formatted_results
        except Exception as e:
            logger.error(f"TextSearchTool execute exception for {context_type_str}: {str(e)}")
            return [{"error": f"执行语义搜索时发生错误: {str(e)}"}]