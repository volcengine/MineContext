import importlib
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

from opencontext.models.context import (
    ContextProperties,
    ExtractedData,
    ProcessedContext,
    RawContextProperties,
    Vectorize,
)
from opencontext.models.enums import ContentFormat, ContextSource, ContextType
from opencontext.storage.base_storage import StorageType
from opencontext.storage.unified_storage import StorageBackendFactory


def make_context(
    context_id: str,
    context_type: ContextType,
    vector: list[float],
    created_at: datetime,
    *,
    metadata: dict | None = None,
    has_compression: bool = False,
    enable_merge: bool = True,
    raw_type: str | None = None,
    raw_id: str | None = None,
) -> ProcessedContext:
    raw_context = RawContextProperties(
        content_format=ContentFormat.TEXT,
        source=ContextSource.INPUT,
        create_time=created_at,
        content_text=f"Raw content for {context_id}",
    )
    return ProcessedContext(
        id=context_id,
        properties=ContextProperties(
            raw_properties=[raw_context],
            create_time=created_at,
            event_time=created_at + timedelta(minutes=1),
            update_time=created_at + timedelta(minutes=2),
            has_compression=has_compression,
            enable_merge=enable_merge,
            raw_type=raw_type,
            raw_id=raw_id,
        ),
        extracted_data=ExtractedData(
            title=f"Title {context_id}",
            summary=f"Summary {context_id}",
            keywords=["milvus", context_id],
            entities=["MineContext"],
            context_type=context_type,
            confidence=9,
            importance=8,
        ),
        vectorize=Vectorize(text=f"Document {context_id}", vector=vector),
        metadata=metadata or {},
    )


def test_factory_registers_milvus_lazily():
    module_name = "opencontext.storage.backends.milvus_backend"
    sys.modules.pop(module_name, None)

    factory = StorageBackendFactory()

    assert "milvus" in factory._backends[StorageType.VECTOR_DB]
    assert module_name not in sys.modules


def test_missing_optional_dependency_has_actionable_error(monkeypatch):
    module = importlib.import_module("opencontext.storage.backends.milvus_backend")
    real_import_module = module.importlib.import_module

    def missing_pymilvus(name: str, *args, **kwargs):
        if name == "pymilvus":
            raise ModuleNotFoundError("No module named 'pymilvus'", name="pymilvus")
        return real_import_module(name, *args, **kwargs)

    monkeypatch.setattr(module.importlib, "import_module", missing_pymilvus)

    with pytest.raises(ImportError, match="uv sync --extra milvus"):
        module.MilvusBackend()


def test_windows_rejects_lite_but_allows_remote_uri():
    module = importlib.import_module("opencontext.storage.backends.milvus_backend")

    with pytest.raises(RuntimeError, match="not supported on Windows"):
        module._validate_uri_for_platform("./milvus.db", system="Windows")

    module._validate_uri_for_platform("https://example.api.zillizcloud.com", system="Windows")


def test_default_config_keeps_chromadb_and_documents_milvus():
    config_path = Path(__file__).parents[1] / "config" / "config.yaml"
    config_text = config_path.read_text(encoding="utf-8")
    config = yaml.safe_load(config_text)

    vector_backends = [
        backend
        for backend in config["storage"]["backends"]
        if backend["storage_type"] == "vector_db"
    ]
    assert vector_backends[0]["backend"] == "chromadb"
    assert 'backend: "milvus"' in config_text
    assert 'uri: "${MILVUS_URI:./persist/milvus.db}"' in config_text


@pytest.fixture
def milvus_backend(tmp_path):
    pytest.importorskip("pymilvus")
    backend = StorageBackendFactory().create_backend(
        StorageType.VECTOR_DB,
        {
            "name": "test_vector",
            "storage_type": "vector_db",
            "backend": "milvus",
            "config": {
                "uri": str(tmp_path / "minecontext.db"),
                "vector_size": 3,
                "collection_prefix": "minecontext_test",
                "consistency_level": "Strong",
            },
        },
    )
    assert backend is not None
    assert backend.get_name() == "milvus"
    return backend


def test_real_milvus_lite_provider_parity(milvus_backend):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    entity = make_context(
        "entity-1",
        ContextType.ENTITY_CONTEXT,
        [1.0, 0.0, 0.0],
        now,
        metadata={
            "entity_type": "project",
            "entity_canonical_name": "MineContext",
            "entity_aliases": ["OpenContext"],
        },
    )
    semantic = make_context(
        "semantic-1",
        ContextType.SEMANTIC_CONTEXT,
        [0.9, 0.1, 0.0],
        now + timedelta(hours=1),
        metadata={"knowledge_file_path": "/tmp/milvus.md"},
        raw_type="vaults",
        raw_id="42",
    )
    semantic_other = make_context(
        "semantic-2",
        ContextType.SEMANTIC_CONTEXT,
        [0.0, 1.0, 0.0],
        now + timedelta(hours=2),
        has_compression=True,
        enable_merge=False,
        raw_type="vaults",
        raw_id="99",
    )

    assert set(milvus_backend.get_collection_names()) == {
        *(context_type.value for context_type in ContextType),
        "todo",
    }
    for collection_name in milvus_backend._collections.values():
        description = milvus_backend._client.describe_collection(collection_name=collection_name)
        assert description["enable_dynamic_field"] is False
        index_name = milvus_backend._client.list_indexes(collection_name=collection_name)[0]
        index = milvus_backend._client.describe_index(
            collection_name=collection_name, index_name=index_name
        )
        assert index["index_type"] == "AUTOINDEX"
        assert index["metric_type"] == "COSINE"

    for context_type, collection_name in milvus_backend._collections.items():
        if context_type == "todo":
            milvus_backend._ensure_todo_collection(collection_name)
        else:
            milvus_backend._ensure_context_collection(collection_name)

    with pytest.raises(ValueError, match="Unsupported Milvus filter field"):
        milvus_backend._build_filter_expression({'unsafe"]': "value"})

    assert milvus_backend.batch_upsert_processed_context([entity, semantic, semantic_other]) == [
        "entity-1",
        "semantic-1",
        "semantic-2",
    ]

    stored = milvus_backend.get_processed_context("entity-1", ContextType.ENTITY_CONTEXT.value)
    assert stored == entity.model_copy(
        update={"vectorize": entity.vectorize.model_copy(update={"vector": None})}
    )

    stored_with_vector = milvus_backend.get_processed_context(
        "entity-1", ContextType.ENTITY_CONTEXT.value, need_vector=True
    )
    assert stored_with_vector.vectorize.vector == pytest.approx([1.0, 0.0, 0.0])
    assert stored_with_vector.metadata["entity_aliases"] == ["OpenContext"]

    updated_entity = entity.model_copy(deep=True)
    updated_entity.extracted_data.summary = "Updated entity summary"
    assert milvus_backend.upsert_processed_context(updated_entity) == "entity-1"
    assert (
        milvus_backend.get_processed_context(
            "entity-1", ContextType.ENTITY_CONTEXT.value
        ).extracted_data.summary
        == "Updated entity summary"
    )

    page_one = milvus_backend.get_all_processed_contexts(
        context_types=[ContextType.SEMANTIC_CONTEXT.value], limit=1, offset=0
    )
    page_two = milvus_backend.get_all_processed_contexts(
        context_types=[ContextType.SEMANTIC_CONTEXT.value], limit=1, offset=1
    )
    page_one_ids = {item.id for item in page_one[ContextType.SEMANTIC_CONTEXT.value]}
    page_two_ids = {item.id for item in page_two[ContextType.SEMANTIC_CONTEXT.value]}
    assert len(page_one_ids) == len(page_two_ids) == 1
    assert page_one_ids.isdisjoint(page_two_ids)

    time_filtered = milvus_backend.get_all_processed_contexts(
        context_types=[ContextType.SEMANTIC_CONTEXT.value],
        filter={
            "create_time_ts": {
                "$gte": int((now + timedelta(minutes=30)).timestamp()),
                "$lte": int((now + timedelta(hours=1, minutes=30)).timestamp()),
            },
            "has_compression": False,
            "enable_merge": True,
        },
    )
    assert [item.id for item in time_filtered[ContextType.SEMANTIC_CONTEXT.value]] == ["semantic-1"]

    entity_filtered = milvus_backend.get_all_processed_contexts(
        context_types=[ContextType.ENTITY_CONTEXT.value],
        filter={"entity_canonical_name": ["Unknown", "MineContext"]},
    )
    assert [item.id for item in entity_filtered[ContextType.ENTITY_CONTEXT.value]] == ["entity-1"]

    document_filtered = milvus_backend.get_all_processed_contexts(
        context_types=[ContextType.SEMANTIC_CONTEXT.value],
        filter={"raw_type": {"$eq": "vaults"}, "raw_id": {"$eq": "42"}},
    )
    assert [item.id for item in document_filtered[ContextType.SEMANTIC_CONTEXT.value]] == [
        "semantic-1"
    ]

    search_results = milvus_backend.search(
        Vectorize(vector=[1.0, 0.0, 0.0]),
        top_k=3,
        context_types=[
            ContextType.ENTITY_CONTEXT.value,
            ContextType.SEMANTIC_CONTEXT.value,
        ],
        need_vector=True,
    )
    assert [item.id for item, _ in search_results[:2]] == ["entity-1", "semantic-1"]
    assert search_results[0][1] >= search_results[1][1] >= search_results[2][1]
    assert search_results[0][1] == pytest.approx(1.0, abs=1e-5)
    assert search_results[0][0].vectorize.vector == pytest.approx([1.0, 0.0, 0.0])

    filtered_search = milvus_backend.search(
        Vectorize(vector=[1.0, 0.0, 0.0]),
        context_types=[ContextType.SEMANTIC_CONTEXT.value],
        filters={"raw_id": {"$eq": "99"}},
    )
    assert [item.id for item, _ in filtered_search] == ["semantic-2"]

    assert milvus_backend.get_processed_context_count(ContextType.SEMANTIC_CONTEXT.value) == 2
    counts = milvus_backend.get_all_processed_context_counts()
    assert counts[ContextType.ENTITY_CONTEXT.value] == 1
    assert counts[ContextType.SEMANTIC_CONTEXT.value] == 2
    assert "todo" not in counts

    assert milvus_backend.delete_processed_context("semantic-1", ContextType.SEMANTIC_CONTEXT.value)
    assert milvus_backend.delete_contexts(["semantic-2"], ContextType.SEMANTIC_CONTEXT.value)
    assert milvus_backend.get_processed_context_count(ContextType.SEMANTIC_CONTEXT.value) == 0


def test_real_milvus_lite_todo_lifecycle(milvus_backend):
    assert milvus_backend.upsert_todo_embedding(
        1, "Review the Milvus backend", [1.0, 0.0, 0.0], {"priority": "high"}
    )
    assert milvus_backend.upsert_todo_embedding(2, "Unrelated task", [0.0, 1.0, 0.0])

    results = milvus_backend.search_similar_todos(
        [1.0, 0.0, 0.0], top_k=2, similarity_threshold=0.8
    )
    assert len(results) == 1
    assert results[0][0] == 1
    assert results[0][1] == "Review the Milvus backend"
    assert results[0][2] == pytest.approx(1.0, abs=1e-5)

    assert milvus_backend.upsert_todo_embedding(
        1, "Review and document the Milvus backend", [1.0, 0.0, 0.0]
    )
    updated = milvus_backend.search_similar_todos(
        [1.0, 0.0, 0.0], top_k=1, similarity_threshold=0.8
    )
    assert updated[0][1] == "Review and document the Milvus backend"

    assert milvus_backend.delete_todo_embedding(1)
    assert (
        milvus_backend.search_similar_todos([1.0, 0.0, 0.0], top_k=2, similarity_threshold=0.8)
        == []
    )
