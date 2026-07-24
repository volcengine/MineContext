#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""Storage backend package with lazy provider imports."""

from importlib import import_module

__all__ = ["SQLiteBackend", "ChromaDBBackend", "QdrantBackend", "MilvusBackend"]

_BACKEND_MODULES = {
    "SQLiteBackend": ".sqlite_backend",
    "ChromaDBBackend": ".chromadb_backend",
    "QdrantBackend": ".qdrant_backend",
    "MilvusBackend": ".milvus_backend",
}


def __getattr__(name: str):
    if name not in _BACKEND_MODULES:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    backend = getattr(import_module(_BACKEND_MODULES[name], __name__), name)
    globals()[name] = backend
    return backend
