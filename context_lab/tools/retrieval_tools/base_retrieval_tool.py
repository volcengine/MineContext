# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
基础检索工具类，提供通用的检索功能和格式化方法
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple, Optional
from context_lab.tools.base import BaseTool
from context_lab.models.context import Vectorize, ProcessedContext
from context_lab.storage.global_storage import get_storage
from context_lab.tools.profile_tools.profile_entity_tool import ProfileEntityTool


@dataclass
class TimeRangeFilter:
    """时间范围过滤条件"""
    start: Optional[int] = None
    end: Optional[int] = None
    timezone: Optional[str] = None
    time_type: Optional[str] = "event_time_ts"

@dataclass
class RetrievalToolFilter:
    """检索工具过滤条件"""
    time_range: Optional[TimeRangeFilter] = None
    entities: List[str] = field(default_factory=list)

class BaseRetrievalTool(BaseTool):
    """检索工具基类，提供通用的检索功能"""
    
    def __init__(self):
        super().__init__()
        # 初始化用户实体统一工具
        self.profile_entity_tool = ProfileEntityTool()
    
    @property
    def storage(self):
        """从全局单例获取 storage"""
        return get_storage()

    def _build_filters(self, filters: RetrievalToolFilter) -> Dict[str, Any]:
        """构建过滤条件"""
        build_filter = {}
        if filters.time_range is not None and filters.time_range.time_type:
            time_type = filters.time_range.time_type
            build_filter[time_type] = {}
            if filters.time_range.start:
                build_filter[time_type]["$gte"] = filters.time_range.start
            if filters.time_range.end:
                build_filter[time_type]["$lte"] = filters.time_range.end
        if filters.entities is not None and filters.entities:
            # 使用Profile实体工具处理实体统一
            unify_result = self.profile_entity_tool.execute(
                entities=filters.entities,
                operation="match_entities",
                context_info=""
            )
            if unify_result.get("success"):
                # 提取匹配的标准化实体名称
                matches = unify_result.get("matches", [])
                unified_entities = [match.get("entity_canonical_name", match["input_entity"]) for match in matches]
                if not unified_entities:
                    unified_entities = filters.entities
                build_filter["entity"] = unified_entities
            else:
                build_filter["entity"] = filters.entities
        return build_filter
    
    def _execute_search(self, 
                       query: str,
                       context_types: List[str],
                       filters: RetrievalToolFilter,
                       top_k: int = 10) -> List[Tuple[ProcessedContext, float]]:
        """执行搜索操作"""
        
        filters = self._build_filters(filters)
        
        if query:
            # 语义搜索
            vectorize = Vectorize(text=query)
            return self.storage.search(
                query=vectorize,
                context_types=context_types,
                filters=filters,
                top_k=top_k
            )
        else:
            # 纯过滤查询
            results_dict = self.storage.get_all_processed_contexts(
                context_types=context_types,
                limit=top_k,
                filter=filters
            )
            
            # 将结果转换为 (context, score) 格式
            results = []
            for context_type in context_types:
                contexts = results_dict.get(context_type, [])
                for ctx in contexts:
                    results.append((ctx, 1.0))
            
            return results[:top_k]
    
    def _format_context_result(self, 
                              context: ProcessedContext, 
                              score: float,
                              additional_fields: Dict[str, Any] = None) -> Dict[str, Any]:
        """格式化单个上下文结果"""
        result = {
            "similarity_score": score
        }
        result["context"] = context.get_llm_context_string()
        # 添加额外字段
        if additional_fields:
            result.update(additional_fields)

        return result
    
    def _format_results(self, 
                       search_results: List[Tuple[ProcessedContext, float]],
                       additional_processing: callable = None) -> List[Dict[str, Any]]:
        """格式化搜索结果"""
        formatted_results = []
        
        for context, score in search_results:
            result = self._format_context_result(context, score)
            
            # 执行额外的处理逻辑
            if additional_processing:
                result = additional_processing(result, context, score)
            
            formatted_results.append(result)
        
        return formatted_results
    
    def execute_with_error_handling(self, **kwargs) -> List[Dict[str, Any]]:
        """带错误处理的执行方法"""
        try:
            return self.execute(**kwargs)
        except Exception as e:
            error_message = f"执行{self.get_name()}时发生错误: {str(e)}"
            return [{"error": error_message}]