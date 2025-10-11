#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Unified storage system - unified management supporting multiple storage backends
"""

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from opencontext.storage.base_storage import (
    IStorageBackend, IVectorStorageBackend, IDocumentStorageBackend, StorageType,
    DataType, DocumentData, QueryResult
)
from opencontext.models.enums import ContextType
from opencontext.models.context import ProcessedContext
from opencontext.utils.logging_utils import get_logger
from opencontext.models.context import Vectorize

logger = get_logger(__name__)


class StorageBackendFactory:
    """Storage backend factory class"""
    
    def __init__(self):
        self._backends = {
            StorageType.VECTOR_DB: {
                'chromadb': self._create_chromadb_backend,
            },
            StorageType.DOCUMENT_DB: {
                'sqlite': self._create_sqlite_backend,
            }
        }
    
    def create_backend(self, storage_type: StorageType, config: Dict[str, Any]) -> Optional[IStorageBackend]:
        """Create storage backend"""
        backend_name = config.get('backend', 'default')
        
        if storage_type not in self._backends:
            logger.error(f"Unsupported storage type: {storage_type}")
            return None
        
        # Get default backend
        type_backends = self._backends[storage_type]
        if backend_name == 'default':
            backend_name = list(type_backends.keys())[0]
        
        if backend_name not in type_backends:
            logger.error(f"Unsupported {storage_type.value} backend: {backend_name}")
            return None
        
        try:
            backend = type_backends[backend_name](config)
            if backend.initialize(config):
                return backend
            else:
                logger.error(f"Backend {backend_name} initialization failed")
                return None
        except Exception as e:
            logger.exception(f"Creating {backend_name} backend failed: {e}")
            return None
    
    def _create_chromadb_backend(self, config: Dict[str, Any]):
        from opencontext.storage.backends.chromadb_backend import ChromaDBBackend
        return ChromaDBBackend()
    
    def _create_sqlite_backend(self, config: Dict[str, Any]):
        from opencontext.storage.backends.sqlite_backend import SQLiteBackend
        return SQLiteBackend()


class UnifiedStorage:
    """
    Unified storage system - manages multiple storage backends, supports automatic routing based on data type and storage requirements
    """
    
    def __init__(self):
        self._factory = StorageBackendFactory()
        self._initialized = False
        self._vector_backend: IVectorStorageBackend = None
        self._document_backend: IDocumentStorageBackend = None

    def get_vector_collection_names(self) -> Optional[List[str]]:
        """Get all collection names in vector database"""
        if not self._vector_backend:
            return None
        return self._vector_backend.get_collection_names()

    def initialize(self) -> bool:
        """
        Initialize unified storage system
        
        Args:
            storage_configs: Storage configuration list, each configuration contains:
                - name: Backend name
                - storage_type: Storage type (vector_db/document_db)
                - backend: Specific backend (chromadb/sqlite etc.)
                - config: Backend specific configuration
                - default: Whether it's the default backend for this type
                - data_types: List of supported data types
        """
        try:
            from opencontext.config.global_config import get_config
            
            storage_config = get_config('storage')
            backend_configs = storage_config.get("backends", [])
            if not backend_configs:
                logger.error("No storage backends configured")
                return False

            for config in backend_configs:
                storage_type = StorageType(config['storage_type'])
                backend = self._factory.create_backend(storage_type, config)
                if backend:
                    # Set dedicated backend reference
                    if storage_type == StorageType.VECTOR_DB and isinstance(backend, IVectorStorageBackend):
                        if self._vector_backend is None or config.get('default', False):
                            self._vector_backend = backend
                    elif storage_type == StorageType.DOCUMENT_DB and isinstance(backend, IDocumentStorageBackend):
                        if self._document_backend is None or config.get('default', False):
                            self._document_backend = backend

                    logger.info(f"Storage backend {config['name']} ({storage_type.value}) initialized successfully")
                else:
                    logger.error(f"Storage backend {config['name']} initialization failed")
                    return False
            
            self._initialized = True
            return True
            
        except Exception as e:
            logger.exception(f"Unified storage system initialization failed: {e}")
            return False

    def get_default_backend(self, storage_type: StorageType) -> Optional[IStorageBackend]:
        """Get default storage backend for specified type"""
        if storage_type == StorageType.VECTOR_DB:
            return self._vector_backend
        elif storage_type == StorageType.DOCUMENT_DB:
            return self._document_backend
        return None
    
    def batch_upsert_processed_context(self, contexts: List[ProcessedContext]) -> Optional[List[str]]:
        """Batch store processed contexts to vector database"""
        if not self._initialized:
            logger.error("Unified storage system not initialized")
            return None
        
        if not self._vector_backend:
            logger.error("Vector database backend not initialized")
            return None
        
        try:
            # Directly pass ProcessedContext to vector database
            doc_ids = self._vector_backend.batch_upsert_processed_context(contexts)
            return doc_ids
            
        except Exception as e:
            logger.exception(f"Failed to store context: {e}")
            return None
    
    def upsert_processed_context(self, context: ProcessedContext) -> Optional[str]:
        """Store processed context to vector database"""
        if not self._initialized:
            logger.error("Unified storage system not initialized")
            return None
        
        if not self._vector_backend:
            logger.error("Vector database backend not initialized")
            return None
        
        try:
            # Directly pass ProcessedContext to vector database
            doc_id = self._vector_backend.upsert_processed_context(context)
            return doc_id
            
        except Exception as e:
            logger.exception(f"Failed to store context: {e}")
            return None
    
    def get_processed_context(self, id : str, context_type : str):
        return self._vector_backend.get_processed_context(id, context_type)
    
    def delete_processed_context(self, id : str, context_type : str):
        return self._vector_backend.delete_processed_context(id, context_type)
    
    def get_all_processed_contexts(self,
                                  context_types: Optional[List[str]] = None,
                                  limit: int = 100,
                                  offset: int = 0,
                                  filter: Optional[Dict[str, Any]] = None,
                                  need_vector: bool = False) -> Dict[str, List[ProcessedContext]]:
        """Get processed contexts, query only from vector database"""
        if not self._initialized:
            logger.error("Unified storage system not initialized")
            return {}
        
        if not self._vector_backend:
            logger.error("Vector database backend not initialized")
            return {}
        
        if not context_types:
            context_types = [ct.value for ct in ContextType]
        try:
            return self._vector_backend.get_all_processed_contexts(
                context_types=context_types,
                limit=limit,
                offset=offset,
                filter=filter,
                need_vector=need_vector
            )
        except Exception as e:
            logger.exception(f"Failed to query ProcessedContext: {e}")
            return {}

    def get_processed_context_count(self, context_type: str) -> int:
        """Get record count for specified context_type"""
        if not self._initialized:
            logger.error("Unified storage system not initialized")
            return 0
        
        if not self._vector_backend:
            logger.error("Vector database backend not initialized")
            return 0
        
        try:
            return self._vector_backend.get_processed_context_count(context_type)
        except Exception as e:
            logger.exception(f"Failed to get {context_type} record count: {e}")
            return 0
    
    def get_all_processed_context_counts(self) -> Dict[str, int]:
        """Get record count for all context_type"""
        if not self._initialized:
            logger.error("Unified storage system not initialized")
            return {}
        
        if not self._vector_backend:
            logger.error("Vector database backend not initialized")
            return {}
        
        try:
            return self._vector_backend.get_all_processed_context_counts()
        except Exception as e:
            logger.exception(f"Failed to get all context_type record counts: {e}")
            return {}
    
    def get_available_context_types(self) -> List[str]:
        """Get all available context_type - all ProcessedContext use vector database"""
        # Return all ContextType enum values, as all ProcessedContext are stored in vector database
        from opencontext.models.enums import ContextType
        return [ct.value for ct in ContextType]
    
    def search(self, 
              query: Vectorize,
              top_k: int = 10,
              context_types: Optional[List[str]] = None,
              filters: Optional[Dict[str, Any]] = None) -> List[Tuple[ProcessedContext, float]]:
        """Vector search, supports context_type filtering"""
        if not self._initialized:
            logger.error("Unified storage system not initialized")
            return []
        
        if not self._vector_backend:
            logger.error("Vector database backend not initialized")
            return []
        
        try:
            # Execute vector search
            search_results = self._vector_backend.search(
                query=query,
                top_k=top_k,
                context_types=context_types,
                filters=filters
            )
            
            return search_results
            
        except Exception as e:
            logger.exception(f"Vector search failed: {e}")
            return []
    
    def get_document(self, doc_id: str) -> Optional[DocumentData]:
        """Get document"""
        if not self._initialized:
            logger.error("Unified storage system not initialized")
            return None
        
        if not self._document_backend:
            return None
        return self._document_backend.get(doc_id)
    
    def query_documents(self,
                       query: str,
                       limit: int = 10,
                       filters: Optional[Dict[str, Any]] = None) -> Optional[QueryResult]:
        """Query documents"""
        if not self._initialized:
            logger.error("Unified storage system not initialized")
            return None
        
        if not self._document_backend:
            return None
        return self._document_backend.query(query, limit, filters)

    def delete_document(self, doc_id: str) -> bool:
        """Delete document"""
        if not self._initialized:
            logger.error("Unified storage system not initialized")
            return False
        
        # Try to delete from all backends
        if self._document_backend:
            self._document_backend.delete(doc_id)
            return True
        return False
  
    def insert_vaults(self, title: str, summary: str, content: str, document_type: str, tags: str = None, 
                     parent_id: int = None, is_folder: bool = False) -> int:
        """Insert report"""
        if not self._initialized:
            logger.error("Unified storage system not initialized")
            return None

        if not self._document_backend:
            return None
        return self._document_backend.insert_vaults(title, summary, content, document_type, tags, parent_id, is_folder)

    def update_vault(self, vault_id: int, title: str = None, content: str = None, 
                     summary: str = None, tags: str = None, is_deleted: bool = None) -> bool:
        """Update report"""
        if not self._initialized:
            logger.error("Unified storage system not initialized")
            return False
        if not self._document_backend:
            return False
        
        # Build kwargs, only include non-None values
        kwargs = {}
        if title is not None:
            kwargs['title'] = title
        if content is not None:
            kwargs['content'] = content
        if summary is not None:
            kwargs['summary'] = summary
        if tags is not None:
            kwargs['tags'] = tags
        if is_deleted is not None:
            kwargs['is_deleted'] = is_deleted

        return self._document_backend.update_vault(vault_id, **kwargs)

    def get_reports(self, limit: int = 100, offset: int = 0, is_deleted: bool = False) -> List[Dict]:
        """Get report"""
        if not self._initialized:
            logger.error("Unified storage system not initialized")
            return []
        
        if not self._document_backend:
            return []
        return self._document_backend.get_reports(limit, offset, is_deleted)

    def get_vaults(self, 
                   limit: int = 100, 
                   offset: int = 0, 
                   is_deleted: bool = False,
                   document_type: str = None,
                   created_after: datetime = None,
                   created_before: datetime = None,
                   updated_after: datetime = None,
                   updated_before: datetime = None) -> List[Dict]:
        """Get vaults list, supports more filtering conditions"""
        if not self._initialized:
            logger.error("Unified storage system not initialized")
            return []
        
        if not self._document_backend:
            return []
        
        return self._document_backend.get_vaults(
            limit=limit, 
            offset=offset, 
            is_deleted=is_deleted,
            document_type=document_type,
            created_after=created_after,
            created_before=created_before,
            updated_after=updated_after,
            updated_before=updated_before
        )
    
    def get_vault(self, vault_id: int) -> Optional[Dict]:
        """Get vaults by ID"""
        if not self._initialized:
            return None
        
        if not self._document_backend:
            return None
        return self._document_backend.get_vault(vault_id)

    def insert_todo(self, content: str, start_time: datetime = None, end_time: datetime = None,
                   status: int = 0, urgency: int = 0, assignee: str = None, reason: str = None) -> int:
        """Insert todo item"""
        if not self._initialized:
            logger.error("Unified storage system not initialized")
            return None

        if not self._document_backend:
            return None
        return self._document_backend.insert_todo(content, start_time, end_time, status, urgency, assignee, reason)
    
    def get_todos(self, status: int = None, limit: int = 100, offset: int = 0, start_time: datetime = None, end_time: datetime = None) -> List[Dict]:
        """Get todo items"""
        if not self._initialized:
            logger.error("Unified storage system not initialized")
            return []
        
        if not self._document_backend:
            return []
        return self._document_backend.get_todos(status, limit, offset, start_time, end_time)
    
    def insert_activity(self, title: str, content: str, resources: str = None,
                       metadata: str = None, start_time: datetime = None, end_time: datetime = None) -> int:
        """Insert activity
        
        Args:
            title: Activity title
            content: Activity content
            resources: Resource information (JSON string)
            metadata: Metadata information (JSON string), including categories, insights etc.
            start_time: Start time
            end_time: End time
            
        Returns:
            int: Activity record ID
        """
        if not self._initialized:
            logger.error("Unified storage system not initialized")
            return None

        if not self._document_backend:
            return None
        return self._document_backend.insert_activity(title, content, resources, metadata, start_time, end_time)
    
    def get_activities(self, start_time: datetime = None, end_time: datetime = None, 
                      limit: int = 100, offset: int = 0) -> List[Dict]:
        """Get activities"""
        if not self._initialized:
            logger.error("Unified storage system not initialized")
            return []
        
        if not self._document_backend:
            return []
        return self._document_backend.get_activities(start_time, end_time, limit, offset)
      
    def insert_tip(self, content: str) -> int:
        """Insert tip"""
        if not self._initialized:
            logger.error("Unified storage system not initialized")
            return None

        if not self._document_backend:
            return None
        return self._document_backend.insert_tip(content)
    
    def get_tips(self, start_time: datetime = None, end_time: datetime = None,
                 limit: int = 100, offset: int = 0) -> List[Dict]:
        """Get tips"""
        if not self._initialized:
            logger.error("Unified storage system not initialized")
            return []
        
        if not self._document_backend:
            return []
        return self._document_backend.get_tips(start_time, end_time, limit, offset)

    def update_todo_status(self, todo_id: int, status: int, end_time: datetime = None) -> bool:
        """Update todo item status"""
        if not self._initialized:
            logger.error("Unified storage system not initialized")
            return False
        
        if not self._document_backend:
            return False
        return self._document_backend.update_todo_status(todo_id=todo_id, status=status, end_time=end_time)

class ActivityStorageManager:
    """
    Activity generated document storage manager
    Specialized for handling activity generated markdown content and image storage
    """
    
    def __init__(self, unified_storage: UnifiedStorage):
        self.unified_storage = unified_storage
        self.logger = get_logger(__name__)
    

    def search_activities(self, 
                         query: str,
                         limit: int = 10,
                         filters: Optional[Dict[str, Any]] = None) -> Optional[QueryResult]:
        """Search activity documents"""
        # Add activity specific filter
        activity_filters = {"content_type": "activity_markdown"}
        if filters:
            activity_filters.update(filters)
        
        return self.unified_storage.query_documents(
            query=query,
            limit=limit,
            filters=activity_filters,
            storage_type=StorageType.DOCUMENT_DB
        )
    
    def _generate_id(self) -> str:
        """Generate unique ID"""
        import uuid
        import time
        return f"{int(time.time())}_{str(uuid.uuid4())[:8]}"

    def _get_current_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()