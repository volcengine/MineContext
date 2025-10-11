#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
ChromaDB vector storage backend
Specifically handles ProcessedContext, supports vectorized storage and retrieval
Creates independent collections for each context_type
"""

from typing import Any, Dict, List, Optional, Tuple
import json
import datetime
import time
from enum import Enum

import chromadb
import signal
import atexit
import threading

from opencontext.storage.base_storage import IVectorStorageBackend, StorageType
from opencontext.models.context import ProcessedContext, Vectorize, ExtractedData, ContextProperties
from opencontext.models.enums import ContextType, ContentFormat
from opencontext.utils.logging_utils import get_logger
from opencontext.llm.global_embedding_client import do_vectorize

logger = get_logger(__name__)


class ChromaDBBackend(IVectorStorageBackend):
    """
    ChromaDB vector storage backend.
    Specializes in handling ProcessedContext, supporting vectorized storage and retrieval.
    Creates a separate collection for each context_type.
    """
    
    def __init__(self):
        self._client: Optional[chromadb.Client] = None
        self._collections: Dict[str, chromadb.Collection] = {}  # context_type -> collection
        self._initialized = False
        self._config = None
        self._is_server_mode = False
        self._connection_retry_count = 0
        self._max_retry_count = 3
        self._retry_delay = 1.0  # seconds
        self._pending_writes = []  # Pending writes
        self._write_lock = threading.Lock()  # Write lock
        self._cleanup_registered = False
        
        # Register graceful shutdown handler
        self._register_cleanup_handlers()
    
    def _register_cleanup_handlers(self) -> None:
        """Register graceful shutdown handlers"""
        if not self._cleanup_registered:
            # Register exit handler
            atexit.register(self._cleanup)
            
            # Register signal handlers
            signal.signal(signal.SIGTERM, self._signal_handler)
            signal.signal(signal.SIGINT, self._signal_handler)
            
            self._cleanup_registered = True
            logger.debug("ChromaDB graceful shutdown handlers registered")
    
    def _signal_handler(self, signum, frame):
        """Handle system signals"""
        logger.info(f"Received signal {signum}, safely shutting down ChromaDB...")
        self._cleanup()
        
    def _cleanup(self) -> None:
        """Clean up resources and persist data"""
        try:
            with self._write_lock:
                # Complete all pending writes
                if self._pending_writes:
                    logger.info(f"Completing {len(self._pending_writes)} pending write operations...")
                    self._flush_pending_writes()
                

                logger.info("Persisting ChromaDB index...")
                # self._client.persist()
                logger.info("ChromaDB safely shut down")
                
        except Exception as e:
            logger.error(f"Error during ChromaDB cleanup: {e}")
    
    def _flush_pending_writes(self) -> None:
        """Flush pending write operations"""
        try:
            # Process pending writes
            for write_op in self._pending_writes:
                try:
                    # Execute write operation
                    collection = write_op['collection']
                    collection.upsert(
                        ids=write_op['ids'],
                        documents=write_op['documents'],
                        metadatas=write_op['metadatas'],
                        embeddings=write_op['embeddings']
                    )
                    logger.debug(f"Completed pending write: {len(write_op['ids'])} documents")
                except Exception as e:
                    logger.error(f"Failed to flush write operation: {e}")
            
            # Clear pending writes
            self._pending_writes.clear()
            
        except Exception as e:
            logger.error(f"Failed to flush pending writes: {e}")
        
    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize the ChromaDB backend, supporting local persistence and server mode"""
        try:
            self._config = config
            chroma_config = config.get('config', {})
            
            # Check mode configuration
            mode = chroma_config.get('mode', 'local')
            
            if mode == 'server':
                # Server mode
                self._is_server_mode = True
                host = chroma_config.get('host', 'localhost')
                port = chroma_config.get('port', 8000)
                ssl = chroma_config.get('ssl', False)
                headers = chroma_config.get('headers', {})
                settings = chroma_config.get('settings', {})
                
                # Build server URL
                protocol = "https" if ssl else "http"
                server_url = f"{protocol}://{host}:{port}"
                
                logger.info(f"Initializing ChromaDB in server mode: {server_url}")
                
                # Create HTTP client and test connection
                self._client = self._create_server_client(host, port, ssl, headers, settings)
                
            else:
                # Local persistence mode
                self._is_server_mode = False
                path = chroma_config.get("path", "./persist/chromadb")
                logger.info(f"Initializing ChromaDB in local persistence mode: {path}")
                
                if path:
                    self._client = chromadb.PersistentClient(path=path)
                else:
                    self._client = chromadb.Client()
            
            # Get all available context_types
            context_types = [ct.value for ct in ContextType]
            config.get("collection_prefix", "opencontext")
            
            # Create a separate collection for each context_type
            for context_type in context_types:
                collection_name = f"{context_type}"
                collection = self._client.get_or_create_collection(
                    name=collection_name,
                    metadata={"hnsw:space": "cosine", "context_type": context_type}
                )
                self._collections[context_type] = collection
            
            self._initialized = True
            logger.info(f"ChromaDB vector backend initialized successfully, created {len(self._collections)} collections")
            return True
            
        except Exception as e:
            logger.exception(f"ChromaDB vector backend initialization failed: {e}")
            return False
    
    def _create_server_client(self, host: str, port: int, ssl: bool, headers: Dict, settings: Dict) -> chromadb.HttpClient:
        """Create a server client and test the connection"""
        for attempt in range(self._max_retry_count):
            try:
                client = chromadb.HttpClient(
                    host=host,
                    port=port,
                    ssl=ssl,
                    headers=headers,
                    settings=chromadb.Settings(**settings) if settings else None
                )
                
                # Test connection
                client.heartbeat()
                logger.info("ChromaDB server connection successful")
                self._connection_retry_count = 0
                return client
                
            except Exception as e:
                self._connection_retry_count += 1
                protocol = "https" if ssl else "http"
                server_url = f"{protocol}://{host}:{port}"
                
                if attempt < self._max_retry_count - 1:
                    logger.warning(f"ChromaDB server connection failed (attempt {attempt + 1}/{self._max_retry_count}): {e}, retrying in {self._retry_delay} seconds")
                    time.sleep(self._retry_delay)
                    self._retry_delay *= 2  # Exponential backoff
                else:
                    logger.error(f"Could not connect to ChromaDB server {server_url} (all retries failed): {e}")
                    raise RuntimeError(f"ChromaDB server connection failed: {e}")
    
    def _check_connection(self) -> bool:
        """Check connection health"""
        if not self._client:
            return False
            
        if self._is_server_mode:
            try:
                self._client.heartbeat()
                return True
            except Exception as e:
                logger.warning(f"ChromaDB server health check failed: {e}")
                return False
        else:
            # Local mode, assume connection is always available
            return True
    
    def _ensure_connection(self) -> bool:
        """Ensure connection is available, reconnect if necessary"""
        if self._check_connection():
            return True
            
        if self._is_server_mode and self._config:
            logger.info("Attempting to reconnect to ChromaDB server...")
            try:
                chroma_config = self._config.get('config', {})
                host = chroma_config.get('host', 'localhost')
                port = chroma_config.get('port', 8000)
                ssl = chroma_config.get('ssl', False)
                headers = chroma_config.get('headers', {})
                settings = chroma_config.get('settings', {})
                
                self._client = self._create_server_client(host, port, ssl, headers, settings)
                
                # Re-initialize collections
                self._collections.clear()
                context_types = [ct.value for ct in ContextType]
                for context_type in context_types:
                    collection_name = f"{context_type}"
                    collection = self._client.get_or_create_collection(
                        name=collection_name,
                        metadata={"hnsw:space": "cosine", "context_type": context_type}
                    )
                    self._collections[context_type] = collection
                    
                logger.info("ChromaDB server reconnected successfully")
                return True
                
            except Exception as e:
                logger.error(f"ChromaDB server reconnection failed: {e}")
                return False
        
        return False
    
    def get_name(self) -> str:
        return "chromadb"
    
    def get_collection_names(self) -> Optional[List[str]]:
        return list(self._collections.keys())
    
    def get_storage_type(self) -> StorageType:
        return StorageType.VECTOR_DB
    
    def _ensure_vectorized(self, context: ProcessedContext) -> List[float]:
        """Ensure the context is vectorized, and vectorize it if not"""
        # Check if vector already exists
        
        if not context.vectorize:
            raise ValueError("Not set")
        if context.vectorize.vector:
            return context.vectorize.vector
        
        try:
            do_vectorize(context.vectorize)
            return context.vectorize.vector
        except Exception as e:
            logger.exception(f"Vectorization failed: {e}")
            raise RuntimeError(f"Vectorization failed: {str(e)}")
    
    def _context_to_chroma_format(self, context: ProcessedContext) -> Dict[str, Any]:
        """
        Convert the context object to a document format for storage
        """
        doc = context.model_dump(exclude_none=True, exclude={'properties', 'extracted_data', 'vectorize', 'metadata'})

        if context.extracted_data:
            extracted_data_dict = context.extracted_data.model_dump(exclude_none=True)
            doc.update(extracted_data_dict)

        if context.metadata:
            doc.update(context.metadata)
        
        if context.vectorize:
            if context.vectorize.content_format == ContentFormat.TEXT:
                doc["document"] = context.vectorize.text
            doc["embedding"] = context.vectorize.vector

        if context.properties:
            properties_dict = context.properties.model_dump(exclude_none=True)
            doc.update(properties_dict)

        def default_json_serializer(obj):
            if isinstance(obj, datetime.datetime):
                return obj.isoformat()
            if isinstance(obj, Enum):
                return obj.value

        for key, value in list(doc.items()):
            if key in ["id", "embedding", "document"]:  # These are not metadata
                continue
            if value is None:
                del doc[key]
                continue
            if isinstance(value, datetime.datetime):
                doc[f"{key}_ts"] = int(value.timestamp())
                doc[key] = value.isoformat()
            elif isinstance(value, Enum):
                doc[key] = value.value
            elif isinstance(value, (dict, list)):
                try:
                    # logger.info(f"Serializing key {key} with value {value}")
                    doc[key] = json.dumps(value, ensure_ascii=False, default=default_json_serializer)
                except (TypeError, ValueError):
                    doc[key] = str(value)
        return doc
    
    def upsert_processed_context(self, context: ProcessedContext) -> str:
        """Store a single ProcessedContext"""
        return self.batch_upsert_processed_context([context])[0]
    
    def batch_upsert_processed_context(self, contexts: List[ProcessedContext]) -> List[str]:
        """Batch store ProcessedContext to the corresponding collection"""
        if not self._initialized:
            raise RuntimeError("ChromaDB backend not initialized")
        
        # Ensure connection is available
        if not self._ensure_connection():
            raise RuntimeError("ChromaDB connection not available")

        contexts_by_type = {}
        for context in contexts:
            context_type = context.extracted_data.context_type.value
            if context_type not in contexts_by_type:
                contexts_by_type[context_type] = []
            contexts_by_type[context_type].append(context)
        
        stored_ids = []
        
        # Batch store to the corresponding collection for each context_type
        for context_type, type_contexts in contexts_by_type.items():
            collection = self._collections.get(context_type)
            if not collection:
                logger.warning(f"No collection found for context_type '{context_type}', skipping storage")
                continue
            
            ids = []
            documents = []
            metadatas = []
            embeddings = []
            
            for context in type_contexts:
                try:
                    # Ensure vectorization
                    vector = self._ensure_vectorized(context)
                    # Convert format
                    chroma_format = self._context_to_chroma_format(context)
                    # Separate id, document, embedding and metadata from the flattened document
                    doc_id = chroma_format.pop('id')
                    document = chroma_format.pop('document', '')
                    embedding = chroma_format.pop('embedding', vector)
                    # The rest are metadata
                    metadata = chroma_format
                    
                    ids.append(doc_id)
                    documents.append(document)
                    metadatas.append(metadata)
                    embeddings.append(embedding)
                    
                except Exception as e:
                    logger.exception(f"Failed to process context {context.id}: {e}")
                    continue
            
            if not ids:
                continue
            
            try:
                with self._write_lock:
                    collection.upsert(
                        ids=ids,
                        documents=documents,
                        metadatas=metadatas,
                        embeddings=embeddings
                    )
                    stored_ids.extend(ids)
                    
                    # Persist immediately to prevent data loss
                    if self._client and hasattr(self._client, 'persist'):
                        self._client.persist()
                
            except Exception as e:
                logger.error(f"Batch storing context to {context_type} collection failed: {e}")
                
                # If write fails, record pending writes for later retry
                with self._write_lock:
                    self._pending_writes.append({
                        'collection': collection,
                        'ids': ids,
                        'documents': documents,
                        'metadatas': metadatas,
                        'embeddings': embeddings,
                        'context_type': context_type
                    })
                continue
        
        return stored_ids
    
    def get_processed_context(self, id: str, context_type: str, need_vector: bool = False) -> Optional[ProcessedContext]:
        """Get ProcessedContext by ID"""
        if not self._initialized:
            return None

        if context_type not in self._collections:
            return None
        # Search in all collections
        try:
            result = self._collections[context_type].get(
                ids=[id], 
                include=["metadatas", "documents", "embeddings"] if need_vector else ["metadatas", "documents"]
            )
            
            if result and result['ids']:
                doc = {
                    'id': result['ids'][0],
                    'document': result['documents'][0],
                    'metadata': result['metadatas'][0],
                }
                if need_vector:
                    doc['embedding'] = result['embeddings'][0]
                return self._chroma_result_to_context(doc)
            
        except Exception as e:
            logger.debug(f"Failed to search context {id} in {context_type} collection: {e}")
            return None

    def get_all_processed_contexts(self, 
                                  context_types: Optional[List[str]] = None,
                                  limit: int = 100, offset: int = 0, 
                                  filter: Optional[Dict[str, Any]] = None,
                                  need_vector: bool = False) -> Dict[str, List[ProcessedContext]]:
        """Get all ProcessedContexts, grouped by context_type"""
        if not self._initialized:
            return {}
        
        result = {}
        if not context_types:
            context_types = list(self._collections.keys())
        
        for context_type in context_types:
            if context_type not in self._collections:
                continue
            collection = self._collections[context_type]
            try:
                where_clause = self._build_where_clause(filter)
                
                # ChromaDB's get method does not directly support offset, so pagination needs to be implemented in other ways
                results = collection.get(
                    limit=limit + offset,  # Get more data to simulate offset
                    where=where_clause,
                    include=["metadatas", "documents", "embeddings"] if need_vector else ["metadatas", "documents"]
                )
                
                contexts = []
                if results and results['ids']:
                    # Manually apply offset
                    start_idx = min(offset, len(results['ids']))
                    end_idx = min(start_idx + limit, len(results['ids']))
                    
                    for i in range(start_idx, end_idx):
                        doc = {
                            'id': results['ids'][i],
                            'document': results['documents'][i],
                            'metadata': results['metadatas'][i],
                        }
                        if need_vector:
                            doc['embedding'] = results['embeddings'][i]
                        context = self._chroma_result_to_context(doc, need_vector)
                        if context:
                            contexts.append(context)
                
                if contexts:
                    result[context_type] = contexts
                        
            except Exception as e:
                logger.exception(f"Failed to get contexts from {context_type} collection: {e}")
                continue
        
        return result

    def delete_processed_context(self, id: str, context_type: str) -> bool:
        """Delete ProcessedContext by ID"""
        return self.delete_contexts([id], context_type)
    
    def search(self, query: Vectorize, top_k: int = 10, context_types: Optional[List[str]] = None,
              filters: Optional[Dict[str, Any]] = None, need_vector: bool = False) -> List[Tuple[ProcessedContext, float]]:
        """Vector search for ProcessedContext"""
        if not self._initialized:
            return []

        # Determine which collections to search
        target_collections = {}
        if context_types:
            for context_type in context_types:
                if context_type in self._collections:
                    target_collections[context_type] = self._collections[context_type]
                else:
                    logger.warning(f"Collection not found: {context_type}")
        else:
            target_collections = self._collections

        # Ensure query is vectorized
        query_vector = None
        if query.vector and len(query.vector) > 0:
            query_vector = query.vector
        else:
            do_vectorize(query)
            query_vector = query.vector

        if not query_vector:
            logger.warning("Unable to get query vector, search failed")
            return []
        
        all_results = []
        
        for context_type, collection in target_collections.items():
            try:
                # Check if collection is empty
                try:
                    count = collection.count()
                    if count == 0:
                        continue
                except Exception as count_error:
                    logger.debug(f"Unable to get count for collection '{context_type}': {count_error}")
                    # If count fails, collection has issues, skip
                    continue
                
                where_clause = self._build_where_clause(filters)
                
                results = collection.query(
                    query_embeddings=[query_vector],
                    n_results=top_k,
                    where=where_clause,
                    include=["metadatas", "documents", "distances", "embeddings"] if need_vector else ["metadatas", "documents", "distances"]
                )
                
                if results and results['ids'][0]:
                    for i in range(len(results['ids'][0])):
                        doc = {
                            'id': results['ids'][0][i],
                            'document': results['documents'][0][i],
                            'metadata': results['metadatas'][0][i],
                        }
                        if need_vector:
                            doc['embedding'] = results['embeddings'][0][i]
                        context = self._chroma_result_to_context(doc, need_vector)
                        if context:
                            distance = results['distances'][0][i]
                            score = 1 - distance  # Convert to similarity score
                            all_results.append((context, score))
                        
            except Exception as e:
                # Special handling for HNSW index errors
                if "hnsw segment reader" in str(e).lower() or "nothing found on disk" in str(e).lower():
                    logger.error(f"Collection '{context_type}' index not initialized (no data), skipping search: {e}")
                    continue
                else:
                    logger.exception(f"Vector search failed in {context_type} collection: {e}")
                    continue

        # Sort by score and limit results
        all_results.sort(key=lambda x: x[1], reverse=True)
        # logger.info(f"Found {len(all_results)} results, returning top {top_k}")
        return all_results[:top_k]
    
    def _chroma_result_to_context(self, doc: Dict[str, Any], need_vector: bool = True) -> Optional[ProcessedContext]:
        """Convert ChromaDB query result to ProcessedContext"""
        try:
            if not doc.get('id'):
                logger.warning("ChromaDB result missing id field")
                return None
            extracted_data_field_names = set(ExtractedData.model_fields.keys())
            properties_field_names = set(ContextProperties.model_fields.keys())
            vectorize_field_names = set(Vectorize.model_fields.keys())

            extracted_data_dict = {}
            properties_dict = {}
            context_dict = {}
            vectorize_dict = {}
            metadata_dict = {}

            # All fields are now at the same level
            document = doc.pop('document', None)
            embedding = doc.pop('embedding', None)
            metadata = doc.pop('metadata', {})
            doc_id = doc.pop('id')

            # Process vectorize data
            if document:
                vectorize_dict['text'] = document
            vectorize_dict['vector'] = embedding

            # Determine metadata fields based on context_type
            metadata_field_names = set()
            context_type_value = metadata.get('context_type')
            
            if context_type_value == ContextType.ENTITY_CONTEXT.value:
                # Import ProfileContextMetadata to get its field names
                from opencontext.models.context import ProfileContextMetadata
                metadata_field_names = set(ProfileContextMetadata.model_fields.keys())
            # Other context_types can add corresponding metadata models here
            # elif context_type_value == ContextType.ACTIVITY_CONTEXT.value:
            #     from opencontext.models.context import ActivityContextMetadata
            #     metadata_field_names = set(ActivityContextMetadata.model_fields.keys())

            # Reconstruct objects from flattened fields
            for key, value in metadata.items():
                # timestamp fields are redundant
                if key.endswith('_ts'):
                    continue

                # Try to deserialize if it looks like a JSON string
                val = value
                if isinstance(value, str) and value.startswith(('{', '[')):
                    try:
                        val = json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        pass  # Keep original value if not valid JSON
                # Assign to appropriate dictionary
                if key in extracted_data_field_names:
                    extracted_data_dict[key] = val
                elif key in properties_field_names:
                    properties_dict[key] = val
                elif key in vectorize_field_names:
                    vectorize_dict[key] = val
                elif metadata_field_names and key in metadata_field_names:
                    # This is a metadata field
                    metadata_dict[key] = val
                else:
                    context_dict[key] = val

            # logger.info(f"extracted_data_dict: {extracted_data_dict}")
            # Create the nested Pydantic models and add them to the main context dict
            context_dict['id'] = doc_id
            context_dict['extracted_data'] = ExtractedData.model_validate(extracted_data_dict)
            context_dict['properties'] = ContextProperties.model_validate(properties_dict)
            context_dict['vectorize'] = Vectorize.model_validate(vectorize_dict)

            # If there are metadata fields, add to context_dict
            if metadata_dict:
                context_dict['metadata'] = metadata_dict
            # Validate the final ProcessedContext object
            context = ProcessedContext.model_validate(context_dict)
            if not need_vector:
                context.vectorize.vector = None
            return context

        except Exception as e:
            logger.exception(f"Failed to convert ChromaDB result to ProcessedContext: {e}")
            return None
    
    def _build_where_clause(self, filters: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Build ChromaDB where query conditions"""
        if not filters:
            return None

        where_conditions = []

        for key, value in filters.items():
            if key == 'context_type':
                # context_type is selected through collection, skip here
                continue
            elif key == 'entities':
                continue
            elif not value:
                continue
            elif key.endswith('_ts') and isinstance(value, dict):
                # Time range query
                if "$gte" in value:
                    where_conditions.append({key: {"$gte": value["$gte"]}})
                if "$lte" in value:
                    where_conditions.append({key: {"$lte": value["$lte"]}})
            else:
                if isinstance(value, list):
                    where_conditions.append({key: {"$in": value}})
                else:
                    where_conditions.append({key: value})
        if not where_conditions:
            return None
        elif len(where_conditions) == 1:
            return where_conditions[0]
        else:
            return {"$and": where_conditions}
    
    def delete_contexts(self, ids: List[str], context_type: str) -> bool:
        """Delete contexts of specified type"""
        if not self._initialized:
            return False

        if context_type not in self._collections:
            return False

        collection = self._collections[context_type]
        try:
            collection.delete(ids=ids)
            return True
        except Exception as e:
            logger.exception(f"Failed to delete ChromaDB contexts: {e}")
            return False

    def get_processed_context_count(self, context_type: str) -> int:
        """Get record count for specified context_type"""
        if not self._initialized:
            return 0

        if context_type not in self._collections:
            return 0

        try:
            collection = self._collections[context_type]
            # Use count method to get the number of documents in the collection
            count = collection.count()
            return count
        except Exception as e:
            logger.warning(f"Failed to get record count for {context_type}: {e}")
            return 0

    def get_all_processed_context_counts(self) -> Dict[str, int]:
        """Get record counts for all context_types"""
        if not self._initialized:
            return {}

        result = {}
        for context_type in self._collections.keys():
            result[context_type] = self.get_processed_context_count(context_type)

        return result