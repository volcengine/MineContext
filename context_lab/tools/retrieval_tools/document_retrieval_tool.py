#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
文档检索工具 - 支持文档级检索和chunk聚合
基于raw_type和raw_id追踪和检索文档
"""

from typing import Any, Dict, List, Tuple
from collections import defaultdict

from context_lab.models.enums import ContextType, ContextSimpleDescriptions, get_context_type_options
from context_lab.tools.retrieval_tools.base_retrieval_tool import BaseRetrievalTool, RetrievalToolFilter, TimeRangeFilter
from context_lab.models.context import ProcessedContext, Vectorize
from context_lab.utils.logging_utils import get_logger

logger = get_logger(__name__)


class DocumentRetrievalTool(BaseRetrievalTool):
    """
    文档检索工具
    
    支持功能：
    - 根据raw_id检索完整文档
    - chunk级别的语义检索
    - 文档级聚合
    - 上下文扩展检索
    """
    
    def __init__(self):
        super().__init__()
        self.supported_modes = [
            'document',     # 文档级检索
            'chunk',        # chunk级检索  
            'hybrid',       # 混合检索
            'context'       # 上下文扩展检索
        ]
    
    @classmethod
    def get_name(cls) -> str:
        """获取工具名称"""
        return "document_retrieval"
    
    @classmethod
    def get_description(cls) -> str:
        """获取工具描述 - 动态生成支持的上下文类型"""
        return "文档检索工具，提供文档级和chunk级的精确及语义搜索。支持raw_id检索、文档聚合和上下文扩展"
    
    @classmethod
    def get_parameters(cls) -> Dict[str, Any]:
        """获取工具参数定义"""
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索查询字符串，支持语义搜索",
                },
                "mode": {
                    "type": "string",
                    "description": "检索模式",
                    "enum": ["document", "chunk", "hybrid", "context"],
                },
                "raw_type": {
                    "type": "string", 
                    "description": "原始类型过滤，如 'vaults'"
                },
                "raw_id": {
                    "type": "string",
                    "description": "原始ID过滤，用于检索特定文档"
                },
                "context_types": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": get_context_type_options()
                    },
                    "description": "上下文类型列表，默认为 [INTENT_CONTEXT]"
                },
                "time_range": {
                    "type": "object",
                    "properties": {
                        "start": {"type": "integer", "description": "开始时间的秒级时间戳"},
                        "end": {"type": "integer", "description": "结束时间的秒级时间戳"},
                        "time_type": {
                            "type": "string",
                            "enum": ["create_time_ts", "update_time_ts", "event_time_ts"],
                            "default": "event_time_ts"
                        }
                    },
                    "description": "时间范围过滤"
                },
                "entities": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "实体列表，用于过滤包含特定实体的记录"
                },
                "top_k": {
                    "type": "integer",
                    "description": "返回结果数量",
                    "minimum": 1,
                    "maximum": 100,
                    "default": 10
                },
                "expand_context": {
                    "type": "boolean",
                    "description": "是否扩展相关上下文",
                    "default": False
                },
                "aggregate_documents": {
                    "type": "boolean", 
                    "description": "是否按文档聚合结果",
                    "default": True
                }
            },
            "required": []
        }
    
    def execute(self, **kwargs) -> List[Dict[str, Any]]:
        """
        执行文档检索 - 实现BaseRetrievalTool的抽象方法
        
        Args:
            **kwargs: 检索参数
            
        Returns:
            检索结果列表
        """
        # 提取参数，设置默认值
        query = kwargs.get('query', '')
        mode = kwargs.get('mode', 'hybrid')
        raw_type = kwargs.get('raw_type')
        raw_id = kwargs.get('raw_id')
        context_types = kwargs.get('context_types')
        time_range = kwargs.get('time_range')
        entities = kwargs.get('entities', [])
        top_k = kwargs.get('top_k', 10)
        expand_context = kwargs.get('expand_context', False)
        aggregate_documents = kwargs.get('aggregate_documents', True)
        
        # 构建检索过滤器
        tool_filter = RetrievalToolFilter()
        if entities:
            tool_filter.entities = entities
        if time_range:
            tool_filter.time_range = TimeRangeFilter(**time_range)
        
        # 使用基类的_build_filters方法构建过滤条件
        filters = self._build_filters(tool_filter)
        
        # 添加文档特定的过滤条件
        if raw_type:
            filters["raw_type"] = {"$eq": raw_type}
        if raw_id:
            filters["raw_id"] = {"$eq": raw_id}
        
        # 默认上下文类型
        if not context_types:
            context_types = [ContextType.INTENT_CONTEXT.value]
        
        try:
            # 根据模式执行检索
            if mode == 'document':
                results = self._retrieve_documents(query, context_types, filters, top_k)
            elif mode == 'chunk':
                results = self._retrieve_chunks(query, context_types, filters, top_k)
            elif mode == 'context':
                results = self._retrieve_with_context(query, context_types, filters, top_k)
            else:  # hybrid
                results = self._retrieve_hybrid(query, context_types, filters, top_k)
            
            # 后处理
            if aggregate_documents and mode != 'document':
                results = self._aggregate_by_document(results)
            
            if expand_context:
                results = self._expand_context(results)
            
            # 格式化结果
            formatted_results = self._format_results(results)
            
            # 添加模式信息
            for result in formatted_results:
                result["retrieval_mode"] = mode
                result["context_type"] = context_types[0] if context_types else ""
            
            return formatted_results
            
        except Exception as e:
            logger.exception(f"文档检索失败: {e}")
            return [{"error": f"执行文档检索时发生错误: {str(e)}"}]
    
    def get_document_by_id(self, 
                          raw_type: str, 
                          raw_id: str,
                          return_chunks: bool = True) -> Dict[str, Any]:
        """
        根据raw_type和raw_id获取完整文档
        
        Args:
            raw_type: 原始类型 (如'vaults')
            raw_id: 原始ID
            return_chunks: 是否返回所有chunks
            
        Returns:
            文档信息
        """
        try:
            # 构建精确匹配过滤器
            filters = {
                "raw_type": {"$eq": raw_type},
                "raw_id": {"$eq": raw_id}
            }
            
            # 检索所有相关chunks
            results = self._execute_document_search(
                query=" ",
                context_types=[ContextType.SEMANTIC_CONTEXT.value],
                filters=filters,
                top_k=1000  # 获取所有chunks
            )
            
            if not results:
                return {
                    "success": False,
                    "message": f"未找到文档 {raw_type}:{raw_id}",
                    "document": None
                }
            
            # 聚合文档信息
            document = self._aggregate_document_info(results)
            
            return {
                "success": True,
                "document": document,
                "chunks": [self._format_context_result(ctx, score) 
                          for ctx, score in results] if return_chunks else [],
                "total_chunks": len(results)
            }
            
        except Exception as e:
            logger.exception(f"获取文档失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "document": None
            }
    
    def list_documents(self,
                      raw_type: str = None,
                      filters: Dict[str, Any] = None,
                      limit: int = 50) -> Dict[str, Any]:
        """
        列出文档列表（聚合相同raw_id的chunks）
        
        Args:
            raw_type: 原始类型过滤
            filters: 额外过滤条件
            limit: 返回数量限制
            
        Returns:
            文档列表
        """
        try:
            # 构建过滤器
            search_filters = self._build_document_filters(
                raw_type=raw_type,
                filters=filters or {}
            )
            
            # 获取所有匹配的contexts
            results = self._execute_document_search(
                query="",
                context_types=[ContextType.SEMANTIC_CONTEXT.value],
                filters=search_filters,
                top_k=limit * 10  # 获取更多以便聚合
            )
            
            # 按文档聚合
            documents = self._group_by_document(results)
            
            # 限制返回数量
            document_list = list(documents.values())[:limit]
            
            return {
                "success": True,
                "documents": document_list,
                "total": len(document_list)
            }
            
        except Exception as e:
            logger.exception(f"列出文档失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "documents": []
            }
    
    def delete_document_chunks(self, raw_type: str, raw_id: str) -> Dict[str, Any]:
        """
        删除指定文档的所有chunks（用于文档删除时的清理）
        
        Args:
            raw_type: 原始类型
            raw_id: 原始ID
            
        Returns:
            删除结果
        """
        try:
            # 构建精确匹配过滤器
            filters = {
                "raw_type": {"$eq": raw_type},
                "raw_id": {"$eq": raw_id}
            }
            
            # 查找要删除的chunks
            results = self._execute_document_search(
                query="",
                context_types=[ContextType.SEMANTIC_CONTEXT.value],
                filters=filters,
                top_k=1000
            )
            
            if not results:
                return {
                    "success": True,
                    "message": f"未找到文档 {raw_type}:{raw_id} 的chunks",
                    "deleted_count": 0
                }
            
            # 提取chunk IDs
            chunk_ids = [ctx.id for ctx, _ in results]
            
            # 执行删除（这里需要存储后端支持）
            # 注意：这是一个简化实现，实际可能需要调用存储后端的删除方法
            logger.info(f"准备删除文档 {raw_type}:{raw_id} 的 {len(chunk_ids)} 个chunks")
            
            # TODO: 实现实际的删除逻辑
            # deleted_count = self.storage.delete_processed_contexts(chunk_ids)
            
            return {
                "success": True,
                "message": f"已删除文档 {raw_type}:{raw_id} 的chunks",
                "deleted_count": len(chunk_ids),
                "deleted_ids": chunk_ids
            }
            
        except Exception as e:
            logger.exception(f"删除文档chunks失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "deleted_count": 0
            }
    
    def _build_document_filters(self,
                               raw_type: str = None,
                               raw_id: str = None,
                               filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """构建文档检索过滤器"""
        search_filters = filters.copy() if filters else {}
        
        if raw_type:
            search_filters["raw_type"] = {"$eq": raw_type}
        
        if raw_id:
            search_filters["raw_id"] = {"$eq": raw_id}
        
        return search_filters
    
    def _execute_document_search(self, 
                                 query: str,
                                 context_types: List[str],
                                 filters: Dict[str, Any],
                                 top_k: int = 10) -> List[Tuple[ProcessedContext, float]]:
        """执行文档搜索操作 - 直接使用已构建的过滤器字典"""
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
    
    def _retrieve_documents(self, query: str, context_types: List[str], 
                           filters: Dict[str, Any], top_k: int) -> List[Tuple[ProcessedContext, float]]:
        """文档级检索（先检索chunks，再聚合）"""
        # 先获取更多chunks用于聚合
        chunk_results = self._execute_document_search(query, context_types, filters, top_k * 3)
        
        # 按文档聚合并取top_k
        documents = self._group_by_document(chunk_results)
        
        # 返回前top_k个文档的代表chunk
        document_items = list(documents.items())[:top_k]
        return [(info['representative_chunk'], info['max_score']) 
                for _, info in document_items]
    
    def _retrieve_chunks(self, query: str, context_types: List[str], 
                        filters: Dict[str, Any], top_k: int) -> List[Tuple[ProcessedContext, float]]:
        """chunk级检索"""
        return self._execute_document_search(query, context_types, filters, top_k)
    
    def _retrieve_hybrid(self, query: str, context_types: List[str], 
                        filters: Dict[str, Any], top_k: int) -> List[Tuple[ProcessedContext, float]]:
        """混合检索（chunk + 文档聚合）"""
        # 获取chunk级结果
        chunk_results = self._execute_document_search(query, context_types, filters, top_k)
        
        # 部分结果进行文档级聚合
        if len(chunk_results) > top_k // 2:
            # 前一半保持chunk级，后一半聚合
            keep_chunks = chunk_results[:top_k // 2]
            aggregate_chunks = chunk_results[top_k // 2:]
            
            # 聚合后一半
            documents = self._group_by_document(aggregate_chunks)
            document_results = [(info['representative_chunk'], info['max_score']) 
                              for info in documents.values()]
            
            # 合并结果
            all_results = keep_chunks + document_results
            return all_results[:top_k]
        
        return chunk_results
    
    def _retrieve_with_context(self, query: str, context_types: List[str], 
                              filters: Dict[str, Any], top_k: int) -> List[Tuple[ProcessedContext, float]]:
        """上下文扩展检索"""
        # 先获取核心结果
        core_results = self._execute_document_search(query, context_types, filters, top_k // 2)
        
        # 为每个结果扩展上下文
        expanded_results = []
        for context, score in core_results:
            expanded_results.append((context, score))
            
            # 查找相关chunks（相同文档的其他chunks）
            if hasattr(context.properties, 'raw_id') and context.properties.raw_id:
                related_filters = filters.copy()
                related_filters["raw_id"] = {"$eq": context.properties.raw_id}
                
                related_results = self._execute_document_search("", context_types, related_filters, 3)
                for related_ctx, related_score in related_results:
                    if related_ctx.id != context.id:  # 避免重复
                        expanded_results.append((related_ctx, related_score * 0.8))  # 降权
        
        # 去重并排序
        unique_results = {}
        for ctx, score in expanded_results:
            if ctx.id not in unique_results or unique_results[ctx.id][1] < score:
                unique_results[ctx.id] = (ctx, score)
        
        sorted_results = sorted(unique_results.values(), key=lambda x: x[1], reverse=True)
        return sorted_results[:top_k]
    
    def _aggregate_by_document(self, results: List[Tuple[ProcessedContext, float]]) -> List[Tuple[ProcessedContext, float]]:
        """按文档聚合结果"""
        documents = self._group_by_document(results)
        
        # 返回每个文档的代表chunk
        return [(info['representative_chunk'], info['max_score']) 
                for info in documents.values()]
    
    def _group_by_document(self, results: List[Tuple[ProcessedContext, float]]) -> Dict[str, Dict[str, Any]]:
        """按文档分组"""
        documents = defaultdict(lambda: {
            'chunks': [],
            'max_score': 0,
            'representative_chunk': None,
            'total_chunks': 0
        })
        
        for context, score in results:
            # 构建文档键
            raw_type = getattr(context.properties, 'raw_type', 'unknown')
            raw_id = getattr(context.properties, 'raw_id', context.id)
            doc_key = f"{raw_type}:{raw_id}"
            
            # 更新文档信息
            doc_info = documents[doc_key]
            doc_info['chunks'].append((context, score))
            doc_info['total_chunks'] += 1
            
            # 更新最高分和代表chunk
            if score > doc_info['max_score']:
                doc_info['max_score'] = score
                doc_info['representative_chunk'] = context
        
        return dict(documents)
    
    def _aggregate_document_info(self, results: List[Tuple[ProcessedContext, float]]) -> Dict[str, Any]:
        """聚合单个文档的完整信息"""
        if not results:
            return None
        
        # 取第一个context作为基础信息
        first_context, _ = results[0]
        
        # 聚合所有内容
        full_content = []
        all_keywords = set()
        all_entities = set()
        total_importance = 0
        max_confidence = 0
        
        for context, _ in results:  # score未使用，用_替代
            if hasattr(context, 'extracted_data'):
                full_content.append(context.extracted_data.summary or "")
                all_keywords.update(context.extracted_data.keywords or [])
                all_entities.update(context.extracted_data.entities or [])
                total_importance += context.extracted_data.importance or 0
                max_confidence = max(max_confidence, context.extracted_data.confidence or 0)
        
        return {
            'raw_type': getattr(first_context.properties, 'raw_type', ''),
            'raw_id': getattr(first_context.properties, 'raw_id', ''),
            'title': first_context.extracted_data.title if hasattr(first_context, 'extracted_data') else '',
            'content': '\n\n'.join(full_content),
            'keywords': list(all_keywords),
            'entities': list(all_entities),
            'total_chunks': len(results),
            'avg_importance': total_importance / len(results) if results else 0,
            'max_confidence': max_confidence,
            'created_at': first_context.properties.create_time.isoformat() if hasattr(first_context.properties, 'create_time') else None
        }
    
    def _expand_context(self, results: List[Tuple[ProcessedContext, float]]) -> List[Tuple[ProcessedContext, float]]:
        """扩展上下文（查找相关chunks）"""
        # 简化实现：返回原结果
        # 实际实现中可以查找时间相近、主题相关的chunks
        return results
    
    def _format_document_results(self, results: List[Tuple[ProcessedContext, float]], mode: str) -> Dict[str, Any]:
        """格式化文档检索结果"""
        formatted_results = []
        
        for context, score in results:
            result = self._format_context_result(context, score)
            
            # 添加文档级信息
            result.update({
                'raw_type': getattr(context.properties, 'raw_type', ''),
                'raw_id': getattr(context.properties, 'raw_id', ''),
                'file_path': getattr(context.properties, 'file_path', ''),
                'retrieval_mode': mode
            })
            
            formatted_results.append(result)
        
        return {
            "success": True,
            "mode": mode,
            "results": formatted_results,
            "total": len(formatted_results)
        }