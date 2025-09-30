# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
过滤获取上下文工具
支持通过各种过滤条件直接获取处理后的上下文记录，不使用语义搜索
"""

from typing import Any, Dict, List
from context_lab.tools.retrieval_tools.base_retrieval_tool import BaseRetrievalTool, RetrievalToolFilter, TimeRangeFilter
from context_lab.models.enums import ContextType, ContextSimpleDescriptions, get_context_type_options
from context_lab.utils.logging_utils import get_logger

logger = get_logger(__name__)


class FilterContextTool(BaseRetrievalTool):
    """过滤获取上下文工具"""
    
    def __init__(self):
        super().__init__()
    
    @classmethod
    def get_name(cls) -> str:
        return "filter_context"
    
    @classmethod
    def get_description(cls) -> str:
        """动态生成工具描述，包含所有支持的上下文类型"""
        context_descriptions = []
        for context_type in ContextType:
            desc_info = ContextSimpleDescriptions[context_type]
            context_descriptions.append(f"- {context_type.value}: {desc_info['description']}")
        descriptions_text = '\n'.join(context_descriptions)
        return f"""通过精确的过滤条件直接获取指定类型的上下文记录，无需语义匹配。适用于明确知道查询条件的精确检索场景，如按时间范围查找、按实体筛选、按上下文类型获取等结构化查询。支持多维度组合过滤和灵活的排序方式，能够高效地从大量数据中定位目标记录。支持以下上下文类型：\n{descriptions_text}"""
    
    @classmethod
    def get_parameters(cls) -> Dict[str, Any]:
        """获取工具参数定义"""
        context_descriptions = []
        for context_type in ContextType:
            desc_info = ContextSimpleDescriptions[context_type]
            context_descriptions.append(f"- {context_type.value}: {desc_info['description']}. {desc_info['purpose']}")
        context_type_desc = "上下文类型的详细描述：\n" + '\n'.join(context_descriptions)

        return {
            "type": "object",
            "properties": {
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
                        # "timezone": {"type": "string", "default": "local"},
                        "time_type": {
                            "type": "string", 
                            "enum": ["create_time_ts", "update_time_ts", "event_time_ts"], 
                            "default": "event_time_ts",
                            "description": "时间类型：create_time_ts(创建时间)，update_time_ts(更新时间)，event_time_ts(事件时间)"
                        }
                    },
                    "description": "时间范围过滤",
                },
                "sort_by": {
                    "type": "string",
                    "enum": ["time_desc", "time_asc", "update_desc", "update_asc"],
                    "default": "time_desc",
                    "description": "排序方式：time_desc(按事件时间降序)，time_asc(按事件时间升序)，update_desc(按更新时间降序)，update_asc(按更新时间升序)"
                },
                "top_k": {
                    "type": "integer",
                    "default": 20,
                    "minimum": 1,
                    "maximum": 100,
                    "description": "返回结果数量"
                }
            },
            "required": ["context_type"]
        }
    
    def execute(self, **kwargs) -> List[Dict[str, Any]]:
        """执行过滤获取"""
        context_type_str = kwargs.get("context_type")
        entities = kwargs.get("entities", [])
        time_range = kwargs.get("time_range")
        metadata_filters = kwargs.get("metadata_filters", {})
        sort_by = kwargs.get("sort_by", "time_desc")
        top_k = kwargs.get("top_k", 20)
        
        # 验证context_type
        if not context_type_str or context_type_str not in get_context_type_options():
            return [{
                "error": f"Invalid context_type: {context_type_str}. Must be one of: {', '.join(get_context_type_options())}"
            }]
        
        # 构建过滤条件
        filters = RetrievalToolFilter()
        filters.entities = entities
        
        if time_range:
            filters.time_range = TimeRangeFilter(**time_range)
        
        # 合并额外的元数据过滤条件
        build_filters = self._build_filters(filters)
        if metadata_filters:
            build_filters.update(metadata_filters)
        
        try:
            # 直接获取处理后的上下文
            results_dict = self.storage.get_all_processed_contexts(
                context_types=[context_type_str],
                limit=top_k,
                filter=build_filters
            )
            
            # 将结果转换为标准格式
            results = []
            contexts = results_dict.get(context_type_str, [])
            
            # 根据sort_by进行排序
            if sort_by == "time_desc":
                contexts.sort(key=lambda x: getattr(x, 'event_time_ts', 0), reverse=True)
            elif sort_by == "time_asc":
                contexts.sort(key=lambda x: getattr(x, 'event_time_ts', 0))
            elif sort_by == "update_desc":
                contexts.sort(key=lambda x: getattr(x, 'update_time_ts', 0), reverse=True)
            elif sort_by == "update_asc":
                contexts.sort(key=lambda x: getattr(x, 'update_time_ts', 0))
            
            # 格式化结果
            for ctx in contexts[:top_k]:
                result = self._format_context_result(ctx, 1.0)  # 无相似度评分，使用1.0
                result["context_type"] = context_type_str
                context_desc = ContextSimpleDescriptions.get(ContextType(context_type_str), {})
                if context_desc:
                    result["context_description"] = context_desc.get("description", "")
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"FilterContextTool execute exception for {context_type_str}: {str(e)}")
            return [{"error": f"执行过滤获取时发生错误: {str(e)}"}]