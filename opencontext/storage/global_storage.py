#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Global storage manager singleton wrapper
Provides global access to UnifiedStorage instance
"""

import threading
from typing import Optional, Dict, Any, List

from opencontext.storage.unified_storage import UnifiedStorage
from opencontext.models.context import ProcessedContext, Vectorize
from opencontext.models.enums import ContextType
from opencontext.utils.logging_utils import get_logger

logger = get_logger(__name__)


class GlobalStorage:
    """
    Global storage manager (singleton pattern)
    
    Provides global access to UnifiedStorage instance, avoiding passing Storage objects between components.
    All components can access UnifiedStorage through GlobalStorage.get_instance().
    """
    
    _instance = None
    _lock = threading.Lock()
    _initialized = False
    
    def __new__(cls):
        """Ensure singleton pattern"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize global storage manager"""
        if not self._initialized:
            with self._lock:
                if not self._initialized:
                    self._storage: Optional[UnifiedStorage] = None
                    self._auto_initialized = False
                    GlobalStorage._initialized = True
    
    @classmethod
    def get_instance(cls) -> 'GlobalStorage':
        """
        Get global storage manager instance
        
        Returns:
            GlobalStorage: Global storage manager singleton instance
        """
        instance = cls()
        # If not initialized yet, try auto-initialization
        if not instance._auto_initialized and instance._storage is None:
            instance._auto_initialize()
        return instance
    
    @classmethod
    def reset(cls):
        """Reset singleton instance (mainly for testing)"""
        with cls._lock:
            cls._instance = None
            cls._initialized = False
    
    def _auto_initialize(self):
        """Auto-initialize storage manager"""
        if self._auto_initialized:
            return
            
        try:
            # Try to auto-initialize storage
            from opencontext.config.global_config import get_config
            
            storage_config = get_config('storage')
            
            if storage_config and storage_config.get('enabled', False):
                backend_configs = storage_config.get("backends", [])
                if backend_configs:
                    storage = UnifiedStorage()
                    if storage.initialize():
                        self._storage = storage
                        logger.info("GlobalStorage auto-initialized successfully")
                    else:
                        logger.warning("GlobalStorage auto-initialization: storage initialization failed")
                else:
                    logger.warning("GlobalStorage auto-initialization: no backend configs found")
            else:
                logger.warning("GlobalStorage auto-initialization: storage not enabled in config")
            self._auto_initialized = True
        except Exception as e:
            logger.error(f"GlobalStorage auto-initialization failed: {e}")
            self._auto_initialized = True  # Prevent repeated attempts
    
    def get_storage(self) -> Optional[UnifiedStorage]:
        """
        Get storage instance
        
        Returns:
            UnifiedStorage: Storage instance, returns None if not initialized
        """
        return self._storage
    
    def is_initialized(self) -> bool:
        """
        Check if initialized
        
        Returns:
            bool: Whether initialized
        """
        return self._storage is not None
    
    # Convenience methods - directly call common UnifiedStorage methods
    
    def upsert_processed_context(self, context: ProcessedContext) -> bool:
        """Store processed context"""
        if not self._storage:
            raise RuntimeError("Storage not initialized")
        return self._storage.upsert_processed_context(context)
    
    def batch_upsert_processed_context(self, contexts: List[ProcessedContext]) -> bool:
        """Batch store processed contexts"""
        if not self._storage:
            raise RuntimeError("Storage not initialized")
        return self._storage.batch_upsert_processed_context(contexts)
    
    def get_processed_context(self, doc_id: str, context_type: ContextType) -> Optional[ProcessedContext]:
        """Get processed context"""
        if not self._storage:
            raise RuntimeError("Storage not initialized")
        return self._storage.get_processed_context(doc_id, context_type)
    
    def delete_processed_context(self, doc_id: str, context_type: ContextType) -> bool:
        """Delete processed context"""
        if not self._storage:
            raise RuntimeError("Storage not initialized")
        return self._storage.delete_processed_context(doc_id, context_type)
    
    def list_processed_contexts(
        self, 
        context_types: Optional[List[ContextType]] = None,
        limit: int = 100, 
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ProcessedContext]:
        """List processed contexts"""
        if not self._storage:
            raise RuntimeError("Storage not initialized")
        return self._storage.list_processed_contexts(context_types, limit, offset, filters)
    
    def search_contexts(
        self, 
        query: str, 
        context_types: Optional[List[ContextType]] = None,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search contexts"""
        if not self._storage:
            raise RuntimeError("Storage not initialized")
        return self._storage.search_contexts(query, context_types, top_k, filters)
    
    def get_context_types(self) -> List[str]:
        """Get all context types"""
        if not self._storage:
            raise RuntimeError("Storage not initialized")
        return self._storage.get_context_types()
    
    def vectorize(self, vectorize: Vectorize, **kwargs):
        """Vectorize"""
        if not self._storage:
            raise RuntimeError("Storage not initialized")
        return self._storage.vectorize(vectorize, **kwargs)


# Convenience functions
def get_global_storage() -> GlobalStorage:
    """Convenience function to get global storage manager instance"""
    return GlobalStorage.get_instance()


def get_storage() -> Optional[UnifiedStorage]:
    """Convenience function to get storage instance"""
    return GlobalStorage.get_instance().get_storage()