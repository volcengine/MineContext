#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Context search operations for OpenContext.
Separated from main OpenContext class for better maintainability.
"""

import datetime
import os
from typing import Dict, Any, Optional, List

from opencontext.models.context import ProcessedContext, RawContextProperties
from opencontext.models.enums import ContextSource, ContentFormat
from opencontext.models.context import Vectorize
from opencontext.storage.global_storage import get_storage
from opencontext.utils.logging_utils import get_logger

logger = get_logger(__name__)


class ContextOperations:
    """Handles context CRUD and search operations."""
    
    def __init__(self):
        self.storage = get_storage()
    
    def get_all_contexts(
        self, 
        limit: int = 10, 
        offset: int = 0, 
        filter_criteria: Optional[Dict[str, Any]] = None,
        need_vector: bool = False
    ) -> Dict[str, List[ProcessedContext]]:
        """Get all processed contexts with pagination and filtering."""
        limit = min(limit, 1000)  # Prevent excessive memory usage
        if self.storage:
            return self.storage.get_all_processed_contexts(
                limit=limit, 
                offset=offset, 
                filter=filter_criteria or {},
                need_vector=need_vector
            )
        logger.warning("Storage is not initialized.")
        return {}

    def get_context(self, doc_id: str, context_type: str) -> Optional[ProcessedContext]:
        """Get a single processed context by ID and type."""
        if self.storage:
            return self.storage.get_processed_context(doc_id, context_type)
        logger.warning("Storage is not initialized.")
        return None

    def update_context(self, doc_id: str, context: ProcessedContext) -> bool:
        """Update a processed context."""
        if self.storage:
            return self.storage.upsert_processed_context(context)
        logger.warning("Storage is not initialized.")
        return False

    def delete_context(self, doc_id: str, context_type: str) -> bool:
        """Delete a processed context."""
        if self.storage:
            return self.storage.delete_processed_context(doc_id, context_type)
        logger.warning("Storage is not initialized.")
        return False

    def add_screenshot(
        self, 
        path: str, 
        window: str, 
        create_time: str, 
        app: str,
        context_processor_callback
    ) -> Optional[str]:
        """Add a screenshot to the system."""
        logger.info(f"Adding screenshot: path={path}, window={window}, create_time={create_time}, app={app}")
        
        # Validate inputs
        if not path:
            error_msg = "Screenshot path cannot be empty"
            logger.error(error_msg)
            return error_msg
            
        if not os.path.exists(path):
            error_msg = f"Screenshot path {path} does not exist"
            logger.error(error_msg)
            return error_msg
        
        try:
            screenshot_format = os.path.splitext(path)[1][1:]
            # Handle ISO format time string, supports Z suffix
            if create_time.endswith('Z'):
                create_time = create_time[:-1] + '+00:00'
            
            raw_context = RawContextProperties(
                source=ContextSource.SCREENSHOT,
                content_format=ContentFormat.IMAGE,
                create_time=datetime.datetime.fromisoformat(create_time),
                content_path=path,
                additional_info={
                    "window": window,
                    "app": app,
                    "duration_count": 1, 
                    "screenshot_format": screenshot_format,
                }
            )
            
            if not context_processor_callback(raw_context):
                return "Failed to add screenshot"
            return None
        except Exception as e:
            error_msg = f"Failed to process screenshot: {e}"
            logger.error(error_msg)
            return error_msg

    def search(
        self, 
        query: str, 
        top_k: int = 10, 
        context_types: Optional[List[str]] = None, 
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform vector search without LLM processing.
        
        Args:
            query: Search query text
            top_k: Number of results to return
            context_types: Context type filter list
            filters: Additional filter conditions
            
        Returns:
            List of search results with context and scores
        """
        if not self.storage:
            raise RuntimeError("Storage not initialized")
        
        try:
            # Create query vector
            query_vectorize = Vectorize(text=query)
            
            # Execute vector search
            search_results = self.storage.search(
                query=query_vectorize,
                top_k=top_k,
                context_types=context_types,
                filters=filters
            )
            
            # Format results
            results = []
            for context, score in search_results:
                results.append({
                    "context": {
                        "id": context.id,
                        "extracted_data": {
                            "title": context.extracted_data.title,
                            "summary": context.extracted_data.summary,
                            "context_type": context.extracted_data.context_type.value,
                            "tags": context.extracted_data.tags,
                            "keywords": context.extracted_data.keywords
                        },
                        "properties": {
                            "create_time": context.properties.create_time
                        }
                    },
                    "score": score
                })
            
            return results
            
        except Exception as e:
            logger.exception(f"Vector search failed: {e}")
            raise RuntimeError(f"Vector search failed: {str(e)}") from e

    def get_context_types(self) -> List[str]:
        """
        Get all available context types.
        
        Returns:
            List of context types
        """
        if not self.storage:
            raise RuntimeError("Storage not initialized")
        
        try:
            return self.storage.get_vector_collection_names()
        except Exception as e:
            logger.exception(f"Failed to get context types: {e}")
            raise RuntimeError(f"Failed to get context types: {str(e)}") from e