#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Unified storage base interfaces and abstract classes.
Defines contracts for different storage backend types.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Tuple
from dataclasses import dataclass
from datetime import datetime

from opencontext.models.context import ProcessedContext, Vectorize


class StorageType(Enum):
    """Enumeration of supported storage types."""
    VECTOR_DB = "vector_db"      # Vector databases: ChromaDB
    DOCUMENT_DB = "document_db"  # Document databases: SQLite, MongoDB


class DataType(Enum):
    """Enumeration of supported data types."""
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    MARKDOWN = "markdown"


@dataclass
class StorageConfig:
    """Base storage configuration class"""
    storage_type: StorageType
    name: str
    config: Dict[str, Any]


@dataclass
class DocumentData:
    """Document data structure"""
    id: str
    content: str
    metadata: Dict[str, Any]
    data_type: DataType = DataType.TEXT
    images: Optional[List[str]] = None  # Image paths or base64 data
    files: Optional[List[str]] = None   # Attachment file paths


@dataclass
class QueryResult:
    """Query result"""
    documents: List[DocumentData]
    total_count: int
    scores: Optional[List[float]] = None


class IStorageBackend(ABC):
    """Storage backend interface"""
    
    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize storage backend"""
    
    @abstractmethod
    def get_name(self) -> str:
        """Get storage backend name"""
    
    @abstractmethod
    def get_storage_type(self) -> StorageType:
        """Get storage type"""



class IVectorStorageBackend(IStorageBackend):
    """Vector storage backend interface"""
    @abstractmethod
    def get_collection_names(self) -> Optional[List[str]]:
        """Get all collection names in vector database"""
    
    @abstractmethod
    def delete_contexts(self, ids: List[str], context_type: str) -> bool:
        """Delete contexts of specified type"""

    @abstractmethod
    def upsert_processed_context(self, context: ProcessedContext) -> str:
        """Store processed context"""
      
    @abstractmethod
    def batch_upsert_processed_context(self, contexts: List[ProcessedContext]) -> List[str]:
        """Batch store processed contexts"""
    
    @abstractmethod
    def get_all_processed_contexts(self,
                                  context_types: Optional[List[str]] = None,
                                  limit: int = 100,
                                  offset: int = 0,
                                  filter: Optional[Dict[str, Any]] = None,
                                  need_vector: bool = False) -> Dict[str, List[ProcessedContext]]:
        """Get processed contexts"""

    @abstractmethod
    def get_processed_context(self, id : str, context_type : str) -> ProcessedContext:
        """Get specified context"""
        
    @abstractmethod
    def delete_processed_context(self, id : str, context_type : str) -> bool:
        """Delete specified context"""
    
    @abstractmethod
    def search(self, 
              query: Vectorize, 
              top_k: int = 10, 
              context_types: Optional[List[str]] = None, 
              filters: Optional[Dict[str, Any]] = None) -> List[Tuple[ProcessedContext, float]]:
        """Vector similarity search"""

    @abstractmethod 
    def get_processed_context_count(self, context_type: str) -> int:
        """Get record count for specified context_type"""
    
    @abstractmethod
    def get_all_processed_context_counts(self) -> Dict[str, int]:
        """Get record counts for all context_types"""


class IDocumentStorageBackend(IStorageBackend):
    """Document storage backend interface"""

    @abstractmethod
    def insert_vaults(self, title: str, summary: str, content: str, document_type: str, tags: str = None, 
                     parent_id: int = None, is_folder: bool = False) -> int:
        """Insert vault"""

    @abstractmethod
    def get_reports(self, limit: int = 100, offset: int = 0, is_deleted: bool = False) -> List[Dict]:
        """Get reports"""
    
    @abstractmethod
    def get_vaults(self, 
                   limit: int = 100, 
                   offset: int = 0, 
                   is_deleted: bool = False,
                   document_type: str = None,
                   created_after: datetime = None,
                   created_before: datetime = None,
                   updated_after: datetime = None,
                   updated_before: datetime = None) -> List[Dict]:
        """Get vaults"""
        
    @abstractmethod
    def get_vault(self, vault_id: int) -> Optional[Dict]:
        """Get vault by ID"""
        pass
    
    @abstractmethod
    def update_vault(self, vault_id: int, **kwargs) -> bool:
        """Update vault"""
        pass
    
    @abstractmethod
    def insert_todo(self, content: str, start_time: datetime = None, end_time: datetime = None,
                   status: int = 0, urgency: int = 0, assignee: str = None, reason: str = None) -> int:
        """Insert todo item"""

    @abstractmethod
    def get_todos(self, status: int = None, limit: int = 100, offset: int = 0, start_time: datetime = None, end_time: datetime = None) -> List[Dict]:
        """Get todo items"""


    @abstractmethod
    def insert_activity(self, title: str, content: str, resources: str = None,
                       metadata: str = None, start_time: datetime = None, end_time: datetime = None) -> int:
        """Insert activity
        
        Args:
            title: Activity title
            content: Activity content
            resources: Resource information (JSON string)
            metadata: Metadata information (JSON string), including categories, insights, etc.
            start_time: Start time
            end_time: End time
            
        Returns:
            int: Activity record ID
        """
    
    @abstractmethod
    def get_activities(self, start_time: datetime = None, end_time: datetime = None, 
                      limit: int = 100, offset: int = 0) -> List[Dict]:
        """Get activities"""
    
    @abstractmethod
    def insert_tip(self, content: str) -> int:
        """Insert tip"""

    @abstractmethod
    def get_tips(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """Get tips"""
      
    
    @abstractmethod
    def update_todo_status(self, todo_id: int, status: int, end_time: datetime = None) -> bool:
        """Update todo item status"""
