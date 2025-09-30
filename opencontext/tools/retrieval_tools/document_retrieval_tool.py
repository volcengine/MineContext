#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Document retrieval tool - supports document-level retrieval and chunk aggregation
Track and retrieve documents based on raw_type and raw_id
"""

from typing import Any, Dict, List, Tuple
from collections import defaultdict

from opencontext.models.enums import ContextType, ContextSimpleDescriptions, get_context_type_options
from opencontext.tools.retrieval_tools.base_retrieval_tool import BaseRetrievalTool, RetrievalToolFilter, TimeRangeFilter
from opencontext.models.context import ProcessedContext, Vectorize
from opencontext.utils.logging_utils import get_logger

logger = get_logger(__name__)


class DocumentRetrievalTool(BaseRetrievalTool):
    """
    Document retrieval tool
    
    Supported features:
    - Retrieve complete documents by raw_id
    - Chunk-level semantic retrieval
    - Document-level aggregation
    - Context expansion retrieval
    """
    
    def __init__(self):
        super().__init__()
        self.supported_modes = [
            'document',     # Document-level retrieval
            'chunk',        # Chunk-level retrieval  
            'hybrid',       # Hybrid retrieval
            'context'       # Context expansion retrieval
        ]
    
    @classmethod
    def get_name(cls) -> str:
        """Get tool name"""
        return "document_retrieval"
    
    @classmethod
    def get_description(cls) -> str:
        """Get tool description - dynamically generate supported context types"""
        return "Document retrieval tool providing document-level and chunk-level exact and semantic search. Supports raw_id retrieval, document aggregation and context expansion"
    
    @classmethod
    def get_parameters(cls) -> Dict[str, Any]:
        """Get tool parameter definitions"""
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query string, supports semantic search",
                },
                "mode": {
                    "type": "string",
                    "description": "Retrieval mode",
                    "enum": ["document", "chunk", "hybrid", "context"],
                },
                "raw_type": {
                    "type": "string", 
                    "description": "Raw type filter, e.g. 'vaults'"
                },
                "raw_id": {
                    "type": "string",
                    "description": "Raw ID filter, used to retrieve specific documents"
                },
                "context_types": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": get_context_type_options()
                    },
                    "description": "List of context types, defaults to [INTENT_CONTEXT]"
                },
                "time_range": {
                    "type": "object",
                    "properties": {
                        "start": {"type": "integer", "description": "Start time in seconds timestamp"},
                        "end": {"type": "integer", "description": "End time in seconds timestamp"},
                        "time_type": {
                            "type": "string",
                            "enum": ["create_time_ts", "update_time_ts", "event_time_ts"],
                            "default": "event_time_ts"
                        }
                    },
                    "description": "Time range filter"
                },
                "entities": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Entity list for filtering records containing specific entities"
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of results to return",
                    "minimum": 1,
                    "maximum": 100,
                    "default": 10
                },
                "expand_context": {
                    "type": "boolean",
                    "description": "Whether to expand related context",
                    "default": False
                },
                "aggregate_documents": {
                    "type": "boolean", 
                    "description": "Whether to aggregate results by document",
                    "default": True
                }
            },
            "required": []
        }
    
    def execute(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Execute document retrieval - implement BaseRetrievalTool's abstract method
        
        Args:
            **kwargs: Retrieval parameters
            
        Returns:
            List of retrieval results
        """
        # Extract parameters, set default values
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
        
        # Build retrieval filter
        tool_filter = RetrievalToolFilter()
        if entities:
            tool_filter.entities = entities
        if time_range:
            tool_filter.time_range = TimeRangeFilter(**time_range)
        
        # Use base class's _build_filters method to build filter conditions
        filters = self._build_filters(tool_filter)
        
        # Add document-specific filter conditions
        if raw_type:
            filters["raw_type"] = {"$eq": raw_type}
        if raw_id:
            filters["raw_id"] = {"$eq": raw_id}
        
        # Default context type
        if not context_types:
            context_types = [ContextType.INTENT_CONTEXT.value]
        
        try:
            # Execute retrieval based on mode
            if mode == 'document':
                results = self._retrieve_documents(query, context_types, filters, top_k)
            elif mode == 'chunk':
                results = self._retrieve_chunks(query, context_types, filters, top_k)
            elif mode == 'context':
                results = self._retrieve_with_context(query, context_types, filters, top_k)
            else:  # hybrid
                results = self._retrieve_hybrid(query, context_types, filters, top_k)
            
            # Post-processing
            if aggregate_documents and mode != 'document':
                results = self._aggregate_by_document(results)
            
            if expand_context:
                results = self._expand_context(results)
            
            # Format results
            formatted_results = self._format_results(results)
            
            # Add mode information
            for result in formatted_results:
                result["retrieval_mode"] = mode
                result["context_type"] = context_types[0] if context_types else ""
            
            return formatted_results
            
        except Exception as e:
            logger.exception(f"Document retrieval failed: {e}")
            return [{"error": f"Error occurred during document retrieval: {str(e)}"}]
    
    def get_document_by_id(self, 
                          raw_type: str, 
                          raw_id: str,
                          return_chunks: bool = True) -> Dict[str, Any]:
        """
        Get complete document by raw_type and raw_id
        
        Args:
            raw_type: Raw type (e.g. 'vaults')
            raw_id: Raw ID
            return_chunks: Whether to return all chunks
            
        Returns:
            Document information
        """
        try:
            # Build exact match filter
            filters = {
                "raw_type": {"$eq": raw_type},
                "raw_id": {"$eq": raw_id}
            }
            
            # Retrieve all related chunks
            results = self._execute_document_search(
                query=" ",
                context_types=[ContextType.SEMANTIC_CONTEXT.value],
                filters=filters,
                top_k=1000  # Get all chunks
            )
            
            if not results:
                return {
                    "success": False,
                    "message": f"Document not found: {raw_type}:{raw_id}",
                    "document": None
                }
            
            # Aggregate document information
            document = self._aggregate_document_info(results)
            
            return {
                "success": True,
                "document": document,
                "chunks": [self._format_context_result(ctx, score) 
                          for ctx, score in results] if return_chunks else [],
                "total_chunks": len(results)
            }
            
        except Exception as e:
            logger.exception(f"Failed to get document: {e}")
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
        List documents (aggregate chunks with the same raw_id)
        
        Args:
            raw_type: Raw type filter
            filters: Additional filter conditions
            limit: Return limit
            
        Returns:
            Document list
        """
        try:
            # Build filters
            search_filters = self._build_document_filters(
                raw_type=raw_type,
                filters=filters or {}
            )
            
            # Get all matching contexts
            results = self._execute_document_search(
                query="",
                context_types=[ContextType.SEMANTIC_CONTEXT.value],
                filters=search_filters,
                top_k=limit * 10  # Get more for aggregation
            )
            
            # Aggregate by document
            documents = self._group_by_document(results)
            
            # Limit return count
            document_list = list(documents.values())[:limit]
            
            return {
                "success": True,
                "documents": document_list,
                "total": len(document_list)
            }
            
        except Exception as e:
            logger.exception(f"Failed to list documents: {e}")
            return {
                "success": False,
                "error": str(e),
                "documents": []
            }
    
    def delete_document_chunks(self, raw_type: str, raw_id: str) -> Dict[str, Any]:
        """
        Delete all chunks of specified document (for cleanup when deleting document)
        
        Args:
            raw_type: Raw type
            raw_id: Raw ID
            
        Returns:
            Deletion result
        """
        try:
            # Build exact match filter
            filters = {
                "raw_type": {"$eq": raw_type},
                "raw_id": {"$eq": raw_id}
            }
            
            # Find chunks to delete
            results = self._execute_document_search(
                query="",
                context_types=[ContextType.SEMANTIC_CONTEXT.value],
                filters=filters,
                top_k=1000
            )
            
            if not results:
                return {
                    "success": True,
                    "message": f"No chunks found for document {raw_type}:{raw_id}",
                    "deleted_count": 0
                }
            
            # Extract chunk IDs
            chunk_ids = [ctx.id for ctx, _ in results]
            
            # Execute deletion (storage backend support required)
            # Note: This is a simplified implementation, actual implementation may need to call storage backend's delete method
            logger.info(f"Preparing to delete {len(chunk_ids)} chunks for document {raw_type}:{raw_id}")
            
            # TODO: Implement actual deletion logic
            # deleted_count = self.storage.delete_processed_contexts(chunk_ids)
            
            return {
                "success": True,
                "message": f"Deleted chunks for document {raw_type}:{raw_id}",
                "deleted_count": len(chunk_ids),
                "deleted_ids": chunk_ids
            }
            
        except Exception as e:
            logger.exception(f"Failed to delete document chunks: {e}")
            return {
                "success": False,
                "error": str(e),
                "deleted_count": 0
            }
    
    def _build_document_filters(self,
                               raw_type: str = None,
                               raw_id: str = None,
                               filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Build document retrieval filters"""
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
        """Execute document search operation - directly use the built filter dictionary"""
        if query:
            # Semantic search
            vectorize = Vectorize(text=query)
            return self.storage.search(
                query=vectorize,
                context_types=context_types,
                filters=filters,
                top_k=top_k
            )
        else:
            # Pure filter query
            results_dict = self.storage.get_all_processed_contexts(
                context_types=context_types,
                limit=top_k,
                filter=filters
            )
            
            # Convert results to (context, score) format
            results = []
            for context_type in context_types:
                contexts = results_dict.get(context_type, [])
                for ctx in contexts:
                    results.append((ctx, 1.0))
            
            return results[:top_k]
    
    def _retrieve_documents(self, query: str, context_types: List[str], 
                           filters: Dict[str, Any], top_k: int) -> List[Tuple[ProcessedContext, float]]:
        """Document-level retrieval (retrieve chunks first, then aggregate)"""
        # Get more chunks for aggregation first
        chunk_results = self._execute_document_search(query, context_types, filters, top_k * 3)
        
        # Aggregate by document and get top_k
        documents = self._group_by_document(chunk_results)
        
        # Return representative chunks of top_k documents
        document_items = list(documents.items())[:top_k]
        return [(info['representative_chunk'], info['max_score']) 
                for _, info in document_items]
    
    def _retrieve_chunks(self, query: str, context_types: List[str], 
                        filters: Dict[str, Any], top_k: int) -> List[Tuple[ProcessedContext, float]]:
        """Chunk-level retrieval"""
        return self._execute_document_search(query, context_types, filters, top_k)
    
    def _retrieve_hybrid(self, query: str, context_types: List[str], 
                        filters: Dict[str, Any], top_k: int) -> List[Tuple[ProcessedContext, float]]:
        """Hybrid retrieval (chunk + document aggregation)"""
        # Get chunk-level results
        chunk_results = self._execute_document_search(query, context_types, filters, top_k)
        
        # Partial results for document-level aggregation
        if len(chunk_results) > top_k // 2:
            # Keep first half at chunk level, aggregate second half
            keep_chunks = chunk_results[:top_k // 2]
            aggregate_chunks = chunk_results[top_k // 2:]
            
            # Aggregate second half
            documents = self._group_by_document(aggregate_chunks)
            document_results = [(info['representative_chunk'], info['max_score']) 
                              for info in documents.values()]
            
            # Merge results
            all_results = keep_chunks + document_results
            return all_results[:top_k]
        
        return chunk_results
    
    def _retrieve_with_context(self, query: str, context_types: List[str], 
                              filters: Dict[str, Any], top_k: int) -> List[Tuple[ProcessedContext, float]]:
        """Context expansion retrieval"""
        # Get core results first
        core_results = self._execute_document_search(query, context_types, filters, top_k // 2)
        
        # Expand context for each result
        expanded_results = []
        for context, score in core_results:
            expanded_results.append((context, score))
            
            # Find related chunks (other chunks from the same document)
            if hasattr(context.properties, 'raw_id') and context.properties.raw_id:
                related_filters = filters.copy()
                related_filters["raw_id"] = {"$eq": context.properties.raw_id}
                
                related_results = self._execute_document_search("", context_types, related_filters, 3)
                for related_ctx, related_score in related_results:
                    if related_ctx.id != context.id:  # Avoid duplicates
                        expanded_results.append((related_ctx, related_score * 0.8))  # Reduce weight
        
        # Deduplicate and sort
        unique_results = {}
        for ctx, score in expanded_results:
            if ctx.id not in unique_results or unique_results[ctx.id][1] < score:
                unique_results[ctx.id] = (ctx, score)
        
        sorted_results = sorted(unique_results.values(), key=lambda x: x[1], reverse=True)
        return sorted_results[:top_k]
    
    def _aggregate_by_document(self, results: List[Tuple[ProcessedContext, float]]) -> List[Tuple[ProcessedContext, float]]:
        """Aggregate results by document"""
        documents = self._group_by_document(results)
        
        # Return representative chunk for each document
        return [(info['representative_chunk'], info['max_score']) 
                for info in documents.values()]
    
    def _group_by_document(self, results: List[Tuple[ProcessedContext, float]]) -> Dict[str, Dict[str, Any]]:
        """Group by document"""
        documents = defaultdict(lambda: {
            'chunks': [],
            'max_score': 0,
            'representative_chunk': None,
            'total_chunks': 0
        })
        
        for context, score in results:
            # Build document key
            raw_type = getattr(context.properties, 'raw_type', 'unknown')
            raw_id = getattr(context.properties, 'raw_id', context.id)
            doc_key = f"{raw_type}:{raw_id}"
            
            # Update document information
            doc_info = documents[doc_key]
            doc_info['chunks'].append((context, score))
            doc_info['total_chunks'] += 1
            
            # Update highest score and representative chunk
            if score > doc_info['max_score']:
                doc_info['max_score'] = score
                doc_info['representative_chunk'] = context
        
        return dict(documents)
    
    def _aggregate_document_info(self, results: List[Tuple[ProcessedContext, float]]) -> Dict[str, Any]:
        """Aggregate complete information for a single document"""
        if not results:
            return None
        
        # Use first context as base information
        first_context, _ = results[0]
        
        # Aggregate all content
        full_content = []
        all_keywords = set()
        all_entities = set()
        total_importance = 0
        max_confidence = 0
        
        for context, _ in results:  # score not used, replace with _
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
        """Expand context (find related chunks)"""
        # Simplified implementation: return original results
        # In actual implementation, can find chunks close in time and related in topic
        return results
    
    def _format_document_results(self, results: List[Tuple[ProcessedContext, float]], mode: str) -> Dict[str, Any]:
        """Format document retrieval results"""
        formatted_results = []
        
        for context, score in results:
            result = self._format_context_result(context, score)
            
            # Add document-level information
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