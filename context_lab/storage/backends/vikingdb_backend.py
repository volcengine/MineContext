#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
VikingDB vector storage backend adapter
Refactor existing VikingDB backend to adapt to new UnifiedStorage architecture
"""

from typing import Any, Dict, List, Optional, Tuple
import json
from datetime import datetime
from enum import Enum

from volcengine.viking_db.VikingDBService import VikingDBService
from volcengine.viking_db.common import Data, VectorOrder

from context_lab.storage.base_storage import (
    IVectorStorageBackend, StorageType, DataType, DocumentData, QueryResult
)
from context_lab.utils.logging_utils import get_logger

logger = get_logger(__name__)


class VikingDBBackend(IVectorStorageBackend):
    """
    VikingDB vector storage backend adapter
    Adapts to new UnifiedStorage architecture, supports DocumentData format
    """
    
    def __init__(self):
        self.vikingdb_service: Optional[VikingDBService] = None
        self.collection_client = None
        self.index_client = None
        self.collection_name: Optional[str] = None
        self.index_name: Optional[str] = None
        self._initialized = False
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize VikingDB backend"""
        try:
            endpoint = config['endpoint']
            ak = config['ak']
            sk = config['sk']
            region = config['region']
            self.collection_name = config['collection_name']
            self.index_name = config['index_name']
            
            # Initialize VikingDB service
            self.vikingdb_service = VikingDBService(
                host=endpoint, 
                region=region, 
                ak=ak, 
                sk=sk
            )
            
            # Get Collection and Index client instances
            self.collection_client = self.vikingdb_service.get_collection(self.collection_name)
            self.index_client = self.vikingdb_service.get_index(self.collection_name, self.index_name)
            
            self._initialized = True
            logger.info(f"VikingDB vector backend initialized successfully, collection: {self.collection_name}, index: {self.index_name}")
            return True
            
        except Exception as e:
            logger.exception(f"VikingDB vector backend initialization failed: {e}")
            return False
    
    def get_name(self) -> str:
        return "vikingdb"
    
    def get_storage_type(self) -> StorageType:
        return StorageType.VECTOR_DB
    
    def _document_to_viking_format(self, document: DocumentData) -> Dict[str, Any]:
        """Convert DocumentData to VikingDB format"""
        doc = {
            'id': document.id,
            'content': document.content,
            'data_type': document.data_type.value
        }
        
        # Handle metadata
        for key, value in document.metadata.items():
            if isinstance(value, datetime):
                doc[f"{key}_ts"] = int(value.timestamp())
                doc[key] = value.isoformat()
            elif isinstance(value, Enum):
                doc[key] = value.value
            elif isinstance(value, (dict, list)):
                try:
                    doc[key] = json.dumps(value, ensure_ascii=False, default=str)
                except (TypeError, ValueError):
                    doc[key] = str(value)
            elif value is not None:
                doc[key] = value
        
        # Handle image paths
        if document.images:
            processed_images = [
                img if img.startswith('MineContext://') else f'MineContext://{img}'
                for img in document.images
            ]
            doc['images'] = json.dumps(processed_images, ensure_ascii=False)
        
        return doc
    
    def _viking_format_to_document(self, viking_data: Dict[str, Any]) -> DocumentData:
        """Convert VikingDB format to DocumentData"""
        doc_id = viking_data['id']
        content = viking_data.get('content', '')
        data_type = DataType(viking_data.get('data_type', 'text'))
        
        # Restore metadata
        metadata = {}
        images = None
        
        for key, value in viking_data.items():
            if key in ['id', 'content', 'data_type']:
                continue
            elif key == 'images':
                try:
                    images = json.loads(value) if isinstance(value, str) else value
                except (json.JSONDecodeError, TypeError):
                    pass
            elif key.endswith('_ts'):
                continue  # Skip timestamp fields
            else:
                # Try to deserialize JSON strings
                if isinstance(value, str) and value.startswith(('{', '[')):
                    try:
                        metadata[key] = json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        metadata[key] = value
                else:
                    metadata[key] = value
        
        return DocumentData(
            id=doc_id,
            content=content,
            metadata=metadata,
            data_type=data_type,
            images=images
        )
    
    def store(self, document: DocumentData) -> str:
        """Store single document"""
        return self.batch_store([document])[0]
    
    def batch_store(self, documents: List[DocumentData]) -> List[str]:
        """Batch store documents"""
        if not self._initialized:
            raise RuntimeError("VikingDB backend not initialized")
        
        if not documents:
            return []
        
        # Convert to VikingDB format
        datas_to_upsert = []
        ids = []
        
        for document in documents:
            viking_doc = self._document_to_viking_format(document)
            datas_to_upsert.append(Data(fields=viking_doc))
            ids.append(document.id)
        
        try:
            # Use upsert_data interface to write data
            self.collection_client.upsert_data(datas_to_upsert)
            logger.info(f"Successfully batch wrote {len(ids)} documents to VikingDB")
            return ids
            
        except Exception as e:
            logger.exception(f"Failed to batch store documents to VikingDB: {e}")
            raise
    
    def get(self, doc_id: str) -> Optional[DocumentData]:
        """Get document by ID"""
        if not self._initialized:
            return None
        
        try:
            # Use fetch_data interface to get data by primary key
            results = self.collection_client.fetch_data([doc_id])
            
            if not results:
                return None
            
            # results is a list of Data instances
            doc_data = results[0].fields
            if not doc_data:
                return None
            
            return self._viking_format_to_document(doc_data)
            
        except Exception as e:
            logger.exception(f"Failed to get document from VikingDB (ID: {doc_id}): {e}")
            return None
    
    def query(self, query: str, limit: int = 10, filters: Optional[Dict[str, Any]] = None) -> QueryResult:
        """Query documents (requires external vector provision)"""
        # VikingDB is mainly used for vector search, text query needs to be converted to vector first
        # Return empty result here, recommend using vector_search method
        logger.warning("VikingDB backend does not support direct text query, please use vector_search method")
        return QueryResult(documents=[], total_count=0)
    
    def search(self, vector: List[float], top_k: int = 10, filters: Optional[Dict[str, Any]] = None) -> List[Tuple[DocumentData, float]]:
        """Vector similarity search"""
        if not self._initialized:
            return []
        
        try:
            # Build VikingDB filter
            viking_filter = self._build_viking_filter(filters)
            
            # Execute vector search
            results = self.index_client.search(
                order=VectorOrder(vector=vector),
                limit=top_k,
                filter=viking_filter,
                output_fields=['*']  # Return all fields
            )
            
            search_results = []
            
            if results and results.data:
                for item in results.data:
                    doc_data = item.fields
                    if doc_data:
                        document = self._viking_format_to_document(doc_data)
                        # VikingDB returns distance, need to convert to similarity score
                        score = item.score if hasattr(item, 'score') else 1.0
                        search_results.append((document, score))
            
            return search_results
            
        except Exception as e:
            logger.exception(f"VikingDB vector search failed: {e}")
            return []
    
    def _build_viking_filter(self, filters: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Build VikingDB filter format"""
        if not filters:
            return None
        
        conds = []
        
        # Exact match fields
        for field in ["entities", "file_path", "content_type", "data_type"]:
            if field in filters and filters[field]:
                conds.append({
                    "op": "must",
                    "field": field,
                    "conds": [filters[field]]
                })
        
        # Time range query
        range_filter = {}
        for time_field in ["created_at_ts", "updated_at_ts"]:
            if f"{time_field}_range" in filters:
                time_range = filters[f"{time_field}_range"]
                if isinstance(time_range, dict):
                    if "gte" in time_range:
                        range_filter["gte"] = time_range["gte"]
                    if "lte" in time_range:
                        range_filter["lte"] = time_range["lte"]
                    
                    if range_filter:
                        range_filter["op"] = "range" 
                        range_filter["field"] = time_field
                        conds.append(range_filter)
                        break
        
        if not conds:
            return None
        elif len(conds) == 1:
            return conds[0]
        else:
            return {
                "op": "and",
                "conds": conds
            }
    
    def update(self, doc_id: str, document: DocumentData) -> bool:
        """Update document"""
        try:
            # VikingDB uses upsert semantics, direct storage can update
            self.store(document)
            return True
        except Exception as e:
            logger.exception(f"Failed to update VikingDB document: {e}")
            return False
    
    def delete(self, doc_id: str) -> bool:
        """Delete document"""
        if not self._initialized:
            return False
        
        try:
            self.collection_client.delete_data([doc_id])
            logger.info(f"Deleted document from VikingDB: {doc_id}")
            return True
        except Exception as e:
            logger.exception(f"Failed to delete document from VikingDB: {e}")
            return False
