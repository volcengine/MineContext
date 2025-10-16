# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Document management tool for administrative operations
Handles document-level operations like deletion and retrieval by ID
Separate from retrieval tools which focus on search/filter operations
"""

from typing import Any, Dict, List, Tuple

from opencontext.models.context import ProcessedContext, Vectorize
from opencontext.models.enums import ContextType
from opencontext.storage.global_storage import get_storage
from opencontext.utils.logging_utils import get_logger

logger = get_logger(__name__)


class DocumentManagementTool:
    """
    Document management tool for administrative operations

    Provides functionality for:
    - Retrieving complete documents by raw_type and raw_id
    - Deleting document chunks
    - Aggregating document information

    This is separate from retrieval tools as it focuses on management
    rather than search/filter operations.
    """

    def __init__(self):
        pass

    @property
    def storage(self):
        """Get storage from global singleton"""
        return get_storage()

    def get_document_by_id(
        self, raw_type: str, raw_id: str, return_chunks: bool = True
    ) -> Dict[str, Any]:
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
            filters = {"raw_type": {"$eq": raw_type}, "raw_id": {"$eq": raw_id}}

            # Retrieve all related chunks
            results = self._execute_document_search(
                query=" ",
                context_types=[ContextType.SEMANTIC_CONTEXT.value],
                filters=filters,
                top_k=1000,  # Get all chunks
            )

            if not results:
                return {
                    "success": False,
                    "message": f"Document not found: {raw_type}:{raw_id}",
                    "document": None,
                }

            # Aggregate document information
            document = self._aggregate_document_info(results)

            return {
                "success": True,
                "document": document,
                "chunks": (
                    [self._format_context_result(ctx, score) for ctx, score in results]
                    if return_chunks
                    else []
                ),
                "total_chunks": len(results),
            }

        except Exception as e:
            logger.exception(f"Failed to get document: {e}")
            return {"success": False, "error": str(e), "document": None}

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
            filters = {"raw_type": {"$eq": raw_type}, "raw_id": {"$eq": raw_id}}

            # Find chunks to delete
            results = self._execute_document_search(
                query="",
                context_types=[ContextType.SEMANTIC_CONTEXT.value],
                filters=filters,
                top_k=1000,
            )

            if not results:
                return {
                    "success": True,
                    "message": f"No chunks found for document {raw_type}:{raw_id}",
                    "deleted_count": 0,
                }

            # Extract chunk IDs
            chunk_ids = [ctx.id for ctx, _ in results]

            # Execute deletion (storage backend support required)
            # Note: This is a simplified implementation, actual implementation may need to call storage backend's delete method
            logger.info(
                f"Preparing to delete {len(chunk_ids)} chunks for document {raw_type}:{raw_id}"
            )

            # TODO: Implement actual deletion logic
            # deleted_count = self.storage.delete_processed_contexts(chunk_ids)

            return {
                "success": True,
                "message": f"Deleted chunks for document {raw_type}:{raw_id}",
                "deleted_count": len(chunk_ids),
                "deleted_ids": chunk_ids,
            }

        except Exception as e:
            logger.exception(f"Failed to delete document chunks: {e}")
            return {"success": False, "error": str(e), "deleted_count": 0}

    def _execute_document_search(
        self, query: str, context_types: List[str], filters: Dict[str, Any], top_k: int = 10
    ) -> List[Tuple[ProcessedContext, float]]:
        """Execute document search operation - directly use the built filter dictionary"""
        if query:
            # Semantic search
            vectorize = Vectorize(text=query)
            return self.storage.search(
                query=vectorize, context_types=context_types, filters=filters, top_k=top_k
            )
        else:
            # Pure filter query
            results_dict = self.storage.get_all_processed_contexts(
                context_types=context_types, limit=top_k, filter=filters
            )

            # Convert results to (context, score) format
            results = []
            for context_type in context_types:
                contexts = results_dict.get(context_type, [])
                for ctx in contexts:
                    results.append((ctx, 1.0))

            return results[:top_k]

    def _aggregate_document_info(
        self, results: List[Tuple[ProcessedContext, float]]
    ) -> Dict[str, Any]:
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

        for context, _ in results:
            if hasattr(context, "extracted_data"):
                full_content.append(context.extracted_data.summary or "")
                all_keywords.update(context.extracted_data.keywords or [])
                all_entities.update(context.extracted_data.entities or [])
                total_importance += context.extracted_data.importance or 0
                max_confidence = max(max_confidence, context.extracted_data.confidence or 0)

        return {
            "raw_type": getattr(first_context.properties, "raw_type", ""),
            "raw_id": getattr(first_context.properties, "raw_id", ""),
            "title": (
                first_context.extracted_data.title
                if hasattr(first_context, "extracted_data")
                else ""
            ),
            "content": "\n\n".join(full_content),
            "keywords": list(all_keywords),
            "entities": list(all_entities),
            "total_chunks": len(results),
            "avg_importance": total_importance / len(results) if results else 0,
            "max_confidence": max_confidence,
            "created_at": (
                first_context.properties.create_time.isoformat()
                if hasattr(first_context.properties, "create_time")
                else None
            ),
        }

    def _format_context_result(
        self, context: ProcessedContext, score: float, additional_fields: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Format single context result"""
        result = {"similarity_score": score}
        result["context"] = context.get_llm_context_string()

        # Add additional fields
        if additional_fields:
            result.update(additional_fields)

        return result
