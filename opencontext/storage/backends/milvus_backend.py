#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

import copy
import datetime
import importlib
import importlib.metadata
import json
import math
import platform
import re
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from opencontext.models.context import ProcessedContext, Vectorize
from opencontext.models.enums import ContextType
from opencontext.storage.base_storage import IVectorStorageBackend, StorageType
from opencontext.utils.logging_utils import get_logger

logger = get_logger(__name__)

TODO_COLLECTION = "todo"

FIELD_ID = "id"
FIELD_VECTOR = "vector"
FIELD_DOCUMENT = "document"
FIELD_CONTEXT_DATA = "context_data"
FIELD_FILTER_DATA = "filter_data"
FIELD_TODO_ID = "todo_id"
FIELD_CONTENT = "content"
FIELD_CREATED_AT = "created_at"
FIELD_METADATA = "metadata"

MAX_ID_LENGTH = 512
MAX_TEXT_LENGTH = 65535
_FILTER_FIELD_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_REMOTE_URI_PATTERN = re.compile(r"^https?://", re.IGNORECASE)


def _load_pymilvus():
    try:
        pymilvus = importlib.import_module("pymilvus")
    except ImportError as exc:
        raise ImportError(
            "The Milvus backend requires the optional 'milvus' dependency. "
            "Install it with 'uv sync --extra milvus'."
        ) from exc
    return pymilvus.MilvusClient, pymilvus.DataType


def _is_remote_uri(uri: str) -> bool:
    return bool(_REMOTE_URI_PATTERN.match(uri))


def _validate_uri_for_platform(uri: str, system: Optional[str] = None) -> None:
    current_system = system or platform.system()
    if current_system == "Windows" and not _is_remote_uri(uri):
        raise RuntimeError(
            "Milvus Lite is not supported on Windows. Configure a remote Milvus or "
            "Zilliz Cloud URI beginning with 'http://' or 'https://' instead."
        )


class MilvusBackend(IVectorStorageBackend):
    """Milvus vector storage backend using the MilvusClient API."""

    def __init__(self):
        self._MilvusClient, self._DataType = _load_pymilvus()
        self._client = None
        self._collections: Dict[str, str] = {}
        self._initialized = False
        self._config: Optional[Dict[str, Any]] = None
        self._uri = "./milvus.db"
        self._is_local = True
        self._vector_size = 1536
        self._collection_prefix = ""
        self._consistency_level = "Session"

    def initialize(self, config: Dict[str, Any]) -> bool:
        try:
            self._config = config
            milvus_config = config.get("config", {})
            self._uri = str(milvus_config.get("uri", "./milvus.db"))
            _validate_uri_for_platform(self._uri)
            self._is_local = not _is_remote_uri(self._uri)
            self._vector_size = int(milvus_config.get("vector_size", 1536))
            if self._vector_size <= 0:
                raise ValueError("Milvus vector_size must be greater than zero")

            self._collection_prefix = str(milvus_config.get("collection_prefix", "")).strip("_")
            if self._collection_prefix and not _FILTER_FIELD_PATTERN.fullmatch(
                self._collection_prefix
            ):
                raise ValueError(
                    "Milvus collection_prefix must contain only letters, numbers, and underscores"
                )

            self._consistency_level = str(milvus_config.get("consistency_level", "Session"))
            token = milvus_config.get("token")

            if self._is_local and self._uri != ":memory:":
                local_path = Path(self._uri).expanduser()
                local_path.parent.mkdir(parents=True, exist_ok=True)
                self._uri = str(local_path)

            client_config: Dict[str, Any] = {"uri": self._uri}
            if token:
                client_config["token"] = token
            if milvus_config.get("db_name"):
                client_config["db_name"] = milvus_config["db_name"]

            self._client = self._MilvusClient(**client_config)
            self._client.list_collections()

            for context_type in (context_type.value for context_type in ContextType):
                collection_name = self._collection_name(context_type)
                self._ensure_context_collection(collection_name)
                self._collections[context_type] = collection_name

            todo_collection_name = self._collection_name(TODO_COLLECTION)
            self._ensure_todo_collection(todo_collection_name)
            self._collections[TODO_COLLECTION] = todo_collection_name

            self._initialized = True
            logger.info(
                f"Milvus vector backend initialized successfully with "
                f"{len(self._collections)} collections"
            )
            return True
        except Exception as exc:
            logger.exception(f"Milvus vector backend initialization failed: {exc}")
            return False

    def _collection_name(self, logical_name: str) -> str:
        if not self._collection_prefix:
            return logical_name
        return f"{self._collection_prefix}_{logical_name}"

    def _ensure_context_collection(self, collection_name: str) -> None:
        if self._client.has_collection(collection_name=collection_name):
            self._validate_collection(
                collection_name,
                {
                    FIELD_ID: self._DataType.VARCHAR,
                    FIELD_VECTOR: self._DataType.FLOAT_VECTOR,
                    FIELD_DOCUMENT: self._DataType.VARCHAR,
                    FIELD_CONTEXT_DATA: self._DataType.JSON,
                    FIELD_FILTER_DATA: self._DataType.JSON,
                },
            )
            return

        schema = self._client.create_schema(auto_id=False, enable_dynamic_field=False)
        schema.add_field(
            field_name=FIELD_ID,
            datatype=self._DataType.VARCHAR,
            is_primary=True,
            max_length=MAX_ID_LENGTH,
        )
        schema.add_field(
            field_name=FIELD_VECTOR,
            datatype=self._DataType.FLOAT_VECTOR,
            dim=self._vector_size,
        )
        schema.add_field(
            field_name=FIELD_DOCUMENT,
            datatype=self._DataType.VARCHAR,
            max_length=MAX_TEXT_LENGTH,
        )
        schema.add_field(field_name=FIELD_CONTEXT_DATA, datatype=self._DataType.JSON)
        schema.add_field(field_name=FIELD_FILTER_DATA, datatype=self._DataType.JSON)

        self._create_collection(collection_name, schema)

    def _ensure_todo_collection(self, collection_name: str) -> None:
        if self._client.has_collection(collection_name=collection_name):
            self._validate_collection(
                collection_name,
                {
                    FIELD_TODO_ID: self._DataType.INT64,
                    FIELD_VECTOR: self._DataType.FLOAT_VECTOR,
                    FIELD_CONTENT: self._DataType.VARCHAR,
                    FIELD_CREATED_AT: self._DataType.VARCHAR,
                    FIELD_METADATA: self._DataType.JSON,
                },
                primary_field=FIELD_TODO_ID,
            )
            return

        schema = self._client.create_schema(auto_id=False, enable_dynamic_field=False)
        schema.add_field(
            field_name=FIELD_TODO_ID,
            datatype=self._DataType.INT64,
            is_primary=True,
        )
        schema.add_field(
            field_name=FIELD_VECTOR,
            datatype=self._DataType.FLOAT_VECTOR,
            dim=self._vector_size,
        )
        schema.add_field(
            field_name=FIELD_CONTENT,
            datatype=self._DataType.VARCHAR,
            max_length=MAX_TEXT_LENGTH,
        )
        schema.add_field(
            field_name=FIELD_CREATED_AT,
            datatype=self._DataType.VARCHAR,
            max_length=64,
        )
        schema.add_field(field_name=FIELD_METADATA, datatype=self._DataType.JSON)

        self._create_collection(collection_name, schema)

    def _create_collection(self, collection_name: str, schema: Any) -> None:
        index_params = self._client.prepare_index_params()
        index_params.add_index(
            field_name=FIELD_VECTOR,
            index_type="AUTOINDEX",
            metric_type="COSINE",
        )
        self._client.create_collection(
            collection_name=collection_name,
            schema=schema,
            index_params=index_params,
            consistency_level=self._consistency_level,
        )
        logger.info(f"Created Milvus collection: {collection_name}")

    def _validate_collection(
        self,
        collection_name: str,
        expected_fields: Dict[str, Any],
        primary_field: str = FIELD_ID,
    ) -> None:
        description = self._client.describe_collection(collection_name=collection_name)
        if description.get("enable_dynamic_field"):
            raise RuntimeError(
                f"Existing Milvus collection '{collection_name}' enables dynamic fields, "
                "which is incompatible with the MineContext storage schema"
            )

        fields = {field["name"]: field for field in description.get("fields", [])}
        missing_fields = sorted(set(expected_fields) - set(fields))
        if missing_fields:
            raise RuntimeError(
                f"Existing Milvus collection '{collection_name}' is missing required fields: "
                f"{', '.join(missing_fields)}"
            )

        for field_name, expected_type in expected_fields.items():
            actual_type = fields[field_name].get("type")
            if int(actual_type) != int(expected_type):
                raise RuntimeError(
                    f"Existing Milvus collection '{collection_name}' has an incompatible "
                    f"type for field '{field_name}'"
                )

        if not fields[primary_field].get("is_primary"):
            raise RuntimeError(
                f"Existing Milvus collection '{collection_name}' does not use "
                f"'{primary_field}' as its primary key"
            )

        vector_dim = int(fields[FIELD_VECTOR].get("params", {}).get("dim", 0))
        if vector_dim != self._vector_size:
            raise RuntimeError(
                f"Existing Milvus collection '{collection_name}' uses vector dimension "
                f"{vector_dim}, but MineContext is configured for {self._vector_size}"
            )

        vector_indexes = [
            self._client.describe_index(collection_name=collection_name, index_name=index_name)
            for index_name in self._client.list_indexes(collection_name=collection_name)
        ]
        compatible_index = any(
            index.get("field_name") == FIELD_VECTOR
            and index.get("index_type") == "AUTOINDEX"
            and index.get("metric_type") == "COSINE"
            for index in vector_indexes
        )
        if not compatible_index:
            raise RuntimeError(
                f"Existing Milvus collection '{collection_name}' must use a COSINE "
                "AUTOINDEX on the vector field"
            )

    def _check_connection(self) -> bool:
        if not self._client:
            return False
        try:
            self._client.list_collections()
            return True
        except Exception as exc:
            logger.warning(f"Milvus health check failed: {exc}")
            return False

    def get_name(self) -> str:
        return "milvus"

    def get_collection_names(self) -> Optional[List[str]]:
        return list(self._collections.keys())

    def get_storage_type(self) -> StorageType:
        return StorageType.VECTOR_DB

    def _ensure_vectorized(self, context: ProcessedContext) -> List[float]:
        if not context.vectorize:
            raise ValueError("Vectorize not set")
        if not context.vectorize.vector:
            self._vectorize(context.vectorize)
        vector = context.vectorize.vector
        self._validate_vector(vector)
        return vector

    def _validate_vector(self, vector: Optional[List[float]]) -> None:
        if not vector:
            raise ValueError("Vector is empty")
        if len(vector) != self._vector_size:
            raise ValueError(
                f"Vector dimension {len(vector)} does not match configured "
                f"Milvus vector_size {self._vector_size}"
            )

    def _context_to_milvus_format(self, context: ProcessedContext) -> Dict[str, Any]:
        self._validate_id(context.id)
        vector = self._ensure_vectorized(context)
        context_data = context.model_dump(mode="json", exclude_none=True)
        context_data.setdefault("vectorize", {}).pop("vector", None)

        document = context.get_vectorize_content() or ""
        return {
            FIELD_ID: context.id,
            FIELD_VECTOR: vector,
            FIELD_DOCUMENT: document,
            FIELD_CONTEXT_DATA: context_data,
            FIELD_FILTER_DATA: self._context_filter_data(context),
        }

    def _validate_id(self, value: str) -> None:
        if len(value.encode("utf-8")) > MAX_ID_LENGTH:
            raise ValueError(f"Milvus context IDs must be at most {MAX_ID_LENGTH} bytes")

    def _context_filter_data(self, context: ProcessedContext) -> Dict[str, Any]:
        serialized = context.model_dump(mode="json", exclude_none=True)
        filter_data: Dict[str, Any] = {FIELD_ID: context.id}
        filter_data.update(serialized.get("extracted_data", {}))
        filter_data.update(serialized.get("metadata", {}))
        filter_data.update(serialized.get("properties", {}))

        properties = context.properties
        for field_name in ("create_time", "event_time", "update_time", "last_call_time"):
            value = getattr(properties, field_name, None)
            if isinstance(value, datetime.datetime):
                filter_data[f"{field_name}_ts"] = int(value.timestamp())
        return filter_data

    def upsert_processed_context(self, context: ProcessedContext) -> str:
        stored_ids = self.batch_upsert_processed_context([context])
        if not stored_ids:
            raise RuntimeError(f"Failed to store context {context.id}")
        return stored_ids[0]

    def batch_upsert_processed_context(self, contexts: List[ProcessedContext]) -> List[str]:
        if not self._initialized:
            raise RuntimeError("Milvus backend not initialized")
        if not self._check_connection():
            raise RuntimeError("Milvus connection not available")

        contexts_by_type: Dict[str, List[ProcessedContext]] = {}
        for context in contexts:
            context_type = context.extracted_data.context_type.value
            contexts_by_type.setdefault(context_type, []).append(context)

        stored_ids: List[str] = []
        for context_type, type_contexts in contexts_by_type.items():
            collection_name = self._collections.get(context_type)
            if not collection_name:
                logger.warning(
                    f"No collection found for context_type '{context_type}', skipping storage"
                )
                continue

            entities = []
            entity_ids = []
            for context in type_contexts:
                try:
                    entities.append(self._context_to_milvus_format(context))
                    entity_ids.append(context.id)
                except Exception as exc:
                    logger.exception(f"Failed to process context {context.id}: {exc}")

            if not entities:
                continue

            try:
                self._client.upsert(collection_name=collection_name, data=entities)
                stored_ids.extend(entity_ids)
            except Exception as exc:
                logger.error(f"Batch storing context to {context_type} collection failed: {exc}")
        return stored_ids

    def get_processed_context(
        self, id: str, context_type: str, need_vector: bool = False
    ) -> Optional[ProcessedContext]:
        if not self._initialized or context_type not in self._collections:
            return None
        try:
            output_fields = self._context_output_fields(need_vector)
            rows = self._client.get(
                collection_name=self._collections[context_type],
                ids=[id],
                output_fields=output_fields,
            )
            if rows:
                return self._milvus_result_to_context(rows[0], need_vector)
        except Exception as exc:
            logger.debug(f"Failed to retrieve context {id} from {context_type} collection: {exc}")
        return None

    def get_all_processed_contexts(
        self,
        context_types: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0,
        filter: Optional[Dict[str, Any]] = None,
        need_vector: bool = False,
    ) -> Dict[str, List[ProcessedContext]]:
        if not self._initialized or limit <= 0:
            return {}

        filter_expression = self._build_filter_expression(filter)
        target_types = context_types or [
            name for name in self._collections if name != TODO_COLLECTION
        ]
        result: Dict[str, List[ProcessedContext]] = {}
        for context_type in target_types:
            collection_name = self._collections.get(context_type)
            if not collection_name:
                continue
            try:
                rows = self._client.query(
                    collection_name=collection_name,
                    filter=filter_expression,
                    output_fields=self._context_output_fields(need_vector),
                    limit=limit,
                    offset=max(offset, 0),
                )
                contexts = [
                    context
                    for context in (
                        self._milvus_result_to_context(row, need_vector) for row in rows
                    )
                    if context is not None
                ]
                if contexts:
                    result[context_type] = contexts
            except Exception as exc:
                logger.exception(f"Failed to get contexts from {context_type} collection: {exc}")
        return result

    def delete_processed_context(self, id: str, context_type: str) -> bool:
        return self.delete_contexts([id], context_type)

    def search(
        self,
        query: Vectorize,
        top_k: int = 10,
        context_types: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        need_vector: bool = False,
    ) -> List[Tuple[ProcessedContext, float]]:
        if not self._initialized or top_k <= 0:
            return []

        if not query.vector:
            self._vectorize(query)
        self._validate_vector(query.vector)
        filter_expression = self._build_filter_expression(filters)

        target_types = context_types or [
            name for name in self._collections if name != TODO_COLLECTION
        ]
        all_results: List[Tuple[ProcessedContext, float]] = []
        for context_type in target_types:
            collection_name = self._collections.get(context_type)
            if not collection_name:
                logger.warning(f"Collection not found: {context_type}")
                continue
            try:
                if self._collection_count(collection_name) == 0:
                    continue
                search_results = self._client.search(
                    collection_name=collection_name,
                    data=[query.vector],
                    anns_field=FIELD_VECTOR,
                    filter=filter_expression,
                    limit=top_k,
                    output_fields=self._context_output_fields(need_vector),
                    search_params={"metric_type": "COSINE", "params": {}},
                )
                for hit in search_results[0] if search_results else []:
                    context = self._milvus_result_to_context(hit, need_vector)
                    if context:
                        all_results.append(
                            (context, self._normalize_similarity(float(hit["distance"])))
                        )
            except Exception as exc:
                logger.exception(f"Vector search failed in {context_type} collection: {exc}")

        all_results.sort(key=lambda item: item[1], reverse=True)
        return all_results[:top_k]

    def _vectorize(self, vectorize: Vectorize) -> None:
        from opencontext.llm.global_embedding_client import do_vectorize

        do_vectorize(vectorize)

    def _context_output_fields(self, need_vector: bool) -> List[str]:
        fields = [FIELD_CONTEXT_DATA, FIELD_DOCUMENT]
        if need_vector:
            fields.append(FIELD_VECTOR)
        return fields

    def _milvus_result_to_context(
        self, result: Dict[str, Any], need_vector: bool
    ) -> Optional[ProcessedContext]:
        try:
            entity = result.get("entity", result)
            context_data = entity.get(FIELD_CONTEXT_DATA)
            if not context_data:
                logger.warning("Milvus result missing context_data field")
                return None

            context_dict = copy.deepcopy(context_data)
            result_id = entity.get(FIELD_ID, result.get(FIELD_ID, result.get("id")))
            if result_id:
                context_dict[FIELD_ID] = str(result_id)

            vectorize = context_dict.setdefault("vectorize", {})
            vectorize[FIELD_VECTOR] = entity.get(FIELD_VECTOR) if need_vector else None
            return ProcessedContext.model_validate(context_dict)
        except Exception as exc:
            logger.exception(f"Failed to convert Milvus result to ProcessedContext: {exc}")
            return None

    def _build_filter_expression(self, filters: Optional[Dict[str, Any]]) -> str:
        if not filters:
            return ""

        conditions: List[str] = []
        for field_name, value in filters.items():
            if field_name in {"context_type", "entities"} or value is None:
                continue
            if not _FILTER_FIELD_PATTERN.fullmatch(field_name):
                raise ValueError(f"Unsupported Milvus filter field: {field_name!r}")

            field_path = f'{FIELD_FILTER_DATA}["{field_name}"]'
            if isinstance(value, dict):
                conditions.extend(self._operator_conditions(field_path, value))
            elif isinstance(value, (list, tuple)):
                condition = self._any_value_condition(field_path, list(value))
                if condition:
                    conditions.append(condition)
            else:
                conditions.append(f"{field_path} == {self._filter_literal(value)}")
        return " and ".join(f"({condition})" for condition in conditions)

    def _operator_conditions(self, field_path: str, operators: Dict[str, Any]) -> List[str]:
        operator_map = {
            "$eq": "==",
            "$ne": "!=",
            "$gt": ">",
            "$gte": ">=",
            "$lt": "<",
            "$lte": "<=",
        }
        conditions = []
        for operator, value in operators.items():
            if operator == "$in":
                condition = self._any_value_condition(field_path, value)
                if condition:
                    conditions.append(condition)
                continue
            if operator not in operator_map:
                raise ValueError(f"Unsupported Milvus filter operator: {operator}")
            conditions.append(
                f"{field_path} {operator_map[operator]} {self._filter_literal(value)}"
            )
        return conditions

    def _any_value_condition(self, field_path: str, values: Any) -> str:
        if not isinstance(values, (list, tuple)):
            raise ValueError("Milvus $in filters require a list of scalar values")
        if not values:
            return ""
        comparisons = [f"{field_path} == {self._filter_literal(value)}" for value in values]
        return " or ".join(f"({comparison})" for comparison in comparisons)

    def _filter_literal(self, value: Any) -> str:
        if isinstance(value, (dict, list, tuple)) or value is None:
            raise ValueError("Milvus filters only support scalar comparison values")
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("Milvus filters do not support non-finite numbers")
        if isinstance(value, Enum):
            value = value.value
        return json.dumps(value, ensure_ascii=False)

    def _normalize_similarity(self, score: float) -> float:
        if self._is_local and self._milvus_lite_uses_cosine_distance():
            return 1.0 - score
        return score

    def _milvus_lite_uses_cosine_distance(self) -> bool:
        try:
            version = importlib.metadata.version("milvus-lite")
        except importlib.metadata.PackageNotFoundError:
            return False
        return version in {"3.0", "3.0.0"}

    def delete_contexts(self, ids: List[str], context_type: str) -> bool:
        if not self._initialized or context_type not in self._collections:
            return False
        if not ids:
            return True
        try:
            self._client.delete(
                collection_name=self._collections[context_type],
                ids=ids,
            )
            return True
        except Exception as exc:
            logger.exception(f"Failed to delete Milvus contexts: {exc}")
            return False

    def _collection_count(self, collection_name: str) -> int:
        stats = self._client.get_collection_stats(collection_name=collection_name)
        return int(stats.get("row_count", 0))

    def get_processed_context_count(self, context_type: str) -> int:
        if not self._initialized or context_type not in self._collections:
            return 0
        try:
            return self._collection_count(self._collections[context_type])
        except Exception as exc:
            logger.warning(f"Failed to get record count for {context_type}: {exc}")
            return 0

    def get_all_processed_context_counts(self) -> Dict[str, int]:
        if not self._initialized:
            return {}
        return {
            context_type: self.get_processed_context_count(context_type)
            for context_type in self._collections
            if context_type != TODO_COLLECTION
        }

    def upsert_todo_embedding(
        self,
        todo_id: int,
        content: str,
        embedding: List[float],
        metadata: Optional[Dict] = None,
    ) -> bool:
        if not self._initialized:
            logger.warning("Milvus not initialized, cannot store todo embedding")
            return False
        try:
            self._validate_vector(embedding)
            entity = {
                FIELD_TODO_ID: todo_id,
                FIELD_VECTOR: embedding,
                FIELD_CONTENT: content,
                FIELD_CREATED_AT: datetime.datetime.now().isoformat(),
                FIELD_METADATA: self._json_compatible(metadata or {}),
            }
            self._client.upsert(
                collection_name=self._collections[TODO_COLLECTION],
                data=[entity],
            )
            return True
        except Exception as exc:
            logger.error(f"Failed to store todo embedding (id={todo_id}): {exc}")
            return False

    def search_similar_todos(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        similarity_threshold: float = 0.85,
    ) -> List[Tuple[int, str, float]]:
        if not self._initialized or top_k <= 0:
            return []
        try:
            self._validate_vector(query_embedding)
            collection_name = self._collections[TODO_COLLECTION]
            if self._collection_count(collection_name) == 0:
                return []
            results = self._client.search(
                collection_name=collection_name,
                data=[query_embedding],
                anns_field=FIELD_VECTOR,
                limit=top_k,
                output_fields=[FIELD_TODO_ID, FIELD_CONTENT],
                search_params={"metric_type": "COSINE", "params": {}},
            )
            similar_todos = []
            for hit in results[0] if results else []:
                similarity = self._normalize_similarity(float(hit["distance"]))
                if similarity >= similarity_threshold:
                    entity = hit.get("entity", {})
                    similar_todos.append(
                        (
                            int(entity.get(FIELD_TODO_ID, hit.get("id"))),
                            entity[FIELD_CONTENT],
                            similarity,
                        )
                    )
            return similar_todos
        except Exception as exc:
            logger.error(f"Failed to search similar todos: {exc}")
            return []

    def delete_todo_embedding(self, todo_id: int) -> bool:
        if not self._initialized:
            return False
        try:
            self._client.delete(
                collection_name=self._collections[TODO_COLLECTION],
                ids=[todo_id],
            )
            return True
        except Exception as exc:
            logger.error(f"Failed to delete todo embedding (id={todo_id}): {exc}")
            return False

    def _json_compatible(self, value: Any) -> Any:
        def default_serializer(item: Any) -> Any:
            if isinstance(item, datetime.datetime):
                return item.isoformat()
            if isinstance(item, Enum):
                return item.value
            raise TypeError(f"Unsupported JSON value: {type(item).__name__}")

        return json.loads(json.dumps(value, default=default_serializer, ensure_ascii=False))
