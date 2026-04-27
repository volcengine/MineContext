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
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from opencontext.models.context import ProcessedContext, RawContextProperties, Vectorize
from opencontext.models.enums import (
    ContentFormat,
    ContextSource,
    ContextType,
    get_context_type_options,
)
from opencontext.storage.global_storage import get_storage
from opencontext.utils.logging_utils import get_logger

logger = get_logger(__name__)


# Path components / locations that must never be ingested by /api/documents/upload,
# regardless of the configured allow-list. These hold credentials, keys, or system
# state whose contents would be sent to the configured (potentially remote)
# VLM/embedding provider for processing.
_SENSITIVE_PATH_COMPONENTS = frozenset(
    {
        ".ssh",
        ".aws",
        ".gnupg",
        ".azure",
        ".gcloud",
        ".kube",
        ".docker",
        ".password-store",
        "Keychains",
    }
)

_SENSITIVE_FILENAMES = frozenset(
    {
        ".env",
        "id_rsa",
        "id_ed25519",
        "id_ecdsa",
        "id_dsa",
        "shadow",
    }
)

_SENSITIVE_PATH_PREFIXES = (
    "/etc",
    "/proc",
    "/sys",
    "/dev",
    "/root",
    "/var/log",
    "/var/db",
    "/private/etc",
    "/private/var/log",
    "/private/var/db",
)


def _is_sensitive_path(path: Path) -> Tuple[bool, str]:
    """Defense-in-depth deny check for clearly sensitive locations."""
    for part in path.parts:
        if part in _SENSITIVE_PATH_COMPONENTS:
            return True, f"path contains sensitive directory '{part}'"
    if path.name in _SENSITIVE_FILENAMES:
        return True, f"file '{path.name}' is on sensitive-filename deny list"
    path_str = str(path)
    for prefix in _SENSITIVE_PATH_PREFIXES:
        if path_str == prefix or path_str.startswith(prefix + os.sep):
            return True, f"path is under sensitive system directory '{prefix}'"
    return False, ""


def _resolve_paths_from_config(values: Any) -> List[Path]:
    """Coerce a config value (string, list of strings, or None) into a list of
    resolved absolute Paths. Silently skips entries that fail to resolve."""
    if values is None:
        return []
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, list):
        return []
    out: List[Path] = []
    for raw in values:
        if not isinstance(raw, str) or not raw:
            continue
        try:
            out.append(Path(raw).expanduser().resolve())
        except Exception:
            continue
    return out


def _resolve_allowed_upload_roots(config: Optional[Dict[str, Any]]) -> List[Path]:
    """Compute the set of directories under which a path passed to
    /api/documents/upload is permitted to live.

    Sources, in order:
      1. capture.folder_monitor.watch_folder_paths — directories the user has
         already opted in to having watched/processed.
      2. security.document_upload_allowed_paths — explicit allow-list extension
         point for the upload endpoint.
      3. Fallback if neither is set: ~/Documents, ~/Downloads, ~/Desktop.
    """
    cfg = config or {}
    roots: List[Path] = []

    capture_cfg = cfg.get("capture") or {}
    folder_monitor_cfg = capture_cfg.get("folder_monitor") or {}
    roots.extend(_resolve_paths_from_config(folder_monitor_cfg.get("watch_folder_paths")))

    security_cfg = cfg.get("security") or {}
    roots.extend(_resolve_paths_from_config(security_cfg.get("document_upload_allowed_paths")))

    if not roots:
        try:
            home = Path.home().resolve()
            for sub in ("Documents", "Downloads", "Desktop"):
                candidate = home / sub
                if candidate.exists():
                    roots.append(candidate)
        except Exception:
            pass

    # De-duplicate while preserving order.
    seen = set()
    unique: List[Path] = []
    for r in roots:
        key = str(r)
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return unique


def _is_path_under_any_root(path: Path, roots: List[Path]) -> bool:
    for root in roots:
        try:
            path.relative_to(root)
            return True
        except ValueError:
            continue
    return False


class ContextOperations:
    """Handles context CRUD and search operations."""

    def __init__(self):
        self.storage = get_storage()

    def get_all_contexts(
        self,
        limit: int = 10,
        offset: int = 0,
        filter_criteria: Optional[Dict[str, Any]] = None,
        need_vector: bool = False,
    ) -> Dict[str, List[ProcessedContext]]:
        """Get all processed contexts with pagination and filtering."""
        limit = min(limit, 1000)  # Prevent excessive memory usage
        if self.storage:
            return self.storage.get_all_processed_contexts(
                limit=limit, offset=offset, filter=filter_criteria or {}, need_vector=need_vector
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
        self, path: str, window: str, create_time: str, app: str, context_processor_callback
    ) -> Optional[str]:
        """Add a screenshot to the system."""

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
            if create_time.endswith("Z"):
                create_time = create_time[:-1] + "+00:00"

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
                },
            )

            if not context_processor_callback(raw_context):
                return "Failed to add screenshot"
            return None
        except Exception as e:
            error_msg = f"Failed to process screenshot: {e}"
            logger.error(error_msg)
            return error_msg

    def add_document(self, file_path: str, context_processor_callback) -> Optional[str]:
        """Add a document to the system."""
        import uuid

        from opencontext.config.global_config import get_config

        # Validate inputs
        if not file_path:
            return "Document path cannot be empty"

        expanded = Path(file_path).expanduser()
        if not expanded.is_absolute():
            return "Document path must be absolute"

        try:
            path = expanded.resolve(strict=False)
        except Exception as e:
            return f"Cannot resolve document path: {e}"

        if not path.exists():
            return f"Document path {file_path} does not exist"

        if not path.is_file():
            return f"Path {file_path} is not a file"

        # The contents of any file accepted here are forwarded to the configured
        # VLM / embedding provider for processing, so this endpoint must not be
        # usable as an arbitrary file-read primitive against the host.
        sensitive, reason = _is_sensitive_path(path)
        if sensitive:
            logger.warning(
                "Rejected document upload from sensitive path: %s (%s)", file_path, reason
            )
            return f"Document path is not allowed: {reason}"

        allowed_roots = _resolve_allowed_upload_roots(get_config())
        if not _is_path_under_any_root(path, allowed_roots):
            roots_pretty = ", ".join(str(r) for r in allowed_roots) if allowed_roots else "<none>"
            logger.warning(
                "Rejected document upload from path outside allow-list: %s "
                "(allowed roots: [%s])",
                file_path,
                roots_pretty,
            )
            return (
                f"Document path is not within an allowed directory. "
                f"Allowed roots: [{roots_pretty}]. "
                f"To permit additional directories, set "
                f"'security.document_upload_allowed_paths' in config.yaml."
            )

        try:
            # Create RawContextProperties
            object_id = f"doc_{uuid.uuid4()}"

            raw_context = RawContextProperties(
                source=ContextSource.LOCAL_FILE,
                content_format=ContentFormat.FILE,
                create_time=datetime.datetime.now(),
                object_id=object_id,
                content_path=str(path),
                additional_info={
                    "filename": path.name,
                    "file_size": path.stat().st_size,
                    "file_extension": path.suffix,
                },
            )

            # Call processor
            if not context_processor_callback(raw_context):
                return "Failed to add document"
            return None
        except Exception as e:
            error_msg = f"Failed to process document: {e}"
            logger.error(error_msg)
            return error_msg

    def search(
        self,
        query: str,
        top_k: int = 10,
        context_types: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
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
                query=query_vectorize, top_k=top_k, context_types=context_types, filters=filters
            )

            # Format results
            results = []
            for context, score in search_results:
                results.append(
                    {
                        "context": {
                            "id": context.id,
                            "extracted_data": {
                                "title": context.extracted_data.title,
                                "summary": context.extracted_data.summary,
                                "context_type": context.extracted_data.context_type.value,
                                "keywords": context.extracted_data.keywords,
                            },
                            "properties": {"create_time": context.properties.create_time},
                        },
                        "score": score,
                    }
                )

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
            collection_names = self.storage.get_vector_collection_names()
            valid_types = get_context_type_options()
            return [name for name in collection_names if name in valid_types]
        except Exception as e:
            logger.exception(f"Failed to get context types: {e}")
            raise RuntimeError(f"Failed to get context types: {str(e)}") from e
