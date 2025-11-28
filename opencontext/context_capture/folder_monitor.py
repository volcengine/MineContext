#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Folder monitoring component that monitors local folder changes and generates context capture events.
"""

import hashlib
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from opencontext.context_capture.base import BaseCaptureComponent
from opencontext.context_processing.processor.document_processor import DocumentProcessor
from opencontext.models.context import RawContextProperties
from opencontext.models.enums import ContentFormat, ContextSource, ContextType
from opencontext.storage.global_storage import get_storage
from opencontext.utils.logging_utils import get_logger

logger = get_logger(__name__)


class FolderMonitorCapture(BaseCaptureComponent):
    """
    Folder monitoring component that monitors local folder changes and generates context capture events.
    """

    def __init__(self):
        """Initialize Folder monitoring component"""
        super().__init__(
            name="FolderMonitorCapture",
            description="Monitor document changes in local folders",
            source_type=ContextSource.LOCAL_FILE,
        )
        self._storage = None
        self._monitor_interval = 5
        self._watch_folder_paths: List[str] = []
        self._recursive = True
        self._max_file_size = 104857600  # 100MB
        self._initial_scan = True  # Initialize initial_scan
        self._file_info_cache: Dict[str, Dict[str, Any]] = {}
        self._supported_formats: Set[str] = set()

        self._document_events: List[Dict[str, Any]] = []
        self._event_lock = threading.RLock()
        self._monitor_thread = None
        self._stop_event = threading.Event()

        self._total_processed = 0
        self._last_activity_time = None
        self._last_scan_time = None

    def _initialize_impl(self, config: Dict[str, Any]) -> bool:
        """
        Initialize folder monitoring component.
        """
        try:
            self._storage = get_storage()
            self._monitor_interval = config.get("monitor_interval", 5)
            self._watch_folder_paths = config.get("watch_folder_paths", ["./watch_folder"])
            self._recursive = config.get("recursive", True)
            self._max_file_size = config.get("max_file_size", 104857600)
            self._initial_scan = config.get("initial_scan", True)  # Get initial_scan from config
            self._supported_formats = set(DocumentProcessor.get_supported_formats())

            self._file_info_cache.clear()
            self._last_scan_time = datetime.now()

            logger.info(
                f"Watching folders: {self._watch_folder_paths}, recursive: {self._recursive}, max file size: {self._max_file_size} bytes"
            )
            return True
        except Exception as e:
            logger.exception(f"Failed to initialize FolderMonitor component: {e}")
            return False

    def _start_impl(self) -> bool:
        """
        Start folder monitoring.
        """
        try:
            if self._initial_scan:  # Use self._initial_scan
                self._scan_existing_folders()

            self._monitor_thread = threading.Thread(
                target=self._monitor_loop, name="folder_monitor", daemon=True
            )
            self._monitor_thread.start()

            logger.info("Folder monitoring started")
            return True
        except Exception as e:
            logger.exception(f"Failed to start Folder monitoring: {e}")
            return False

    def _stop_impl(self, graceful: bool = True) -> bool:
        """
        Stop folder monitoring.
        """
        try:
            self._stop_event.set()
            if self._monitor_thread and self._monitor_thread.is_alive():
                self._monitor_thread.join(timeout=10 if graceful else 1)
            logger.info("Folder monitoring stopped")
            return True
        except Exception as e:
            logger.exception(f"Failed to stop Folder monitoring: {e}")
            return False

    def _capture_impl(self) -> List[RawContextProperties]:
        """
        Execute document capture by processing queued events.
        """
        try:
            result = []
            with self._event_lock:
                events = self._document_events.copy()
                self._document_events.clear()

            for event in events:
                self._process_file_event(event)
                context_data = self._create_context_from_event(event)
                if context_data:
                    result.append(context_data)
                    self._total_processed += 1
            return result
        except Exception as e:
            logger.exception(f"Document capture failed: {e}")
            return []

    def _monitor_loop(self):
        """Monitor loop that periodically checks for folder changes."""
        while not self._stop_event.is_set():
            try:
                self._scan_folder_file_changes()
                time.sleep(self._monitor_interval)
            except Exception as e:
                logger.exception(f"Monitor loop error: {e}")
                time.sleep(self._monitor_interval * 2)  # Backoff on error

    def _scan_existing_folders(self):
        """Scan existing folders for initial state."""
        logger.info("Starting initial scan of watched folders.")
        for folder_path in self._watch_folder_paths:
            files = self._scan_folder_files(folder_path, self._recursive)
            for file_path in files:
                try:
                    file_stat = os.stat(file_path)
                    file_hash = self._get_file_hash(file_path)
                    self._file_info_cache[file_path] = {
                        "mtime": file_stat.st_mtime,
                        "size": file_stat.st_size,
                        "hash": file_hash,
                    }
                except OSError as e:
                    logger.warning(f"Failed to get initial stats for {file_path}: {e}")
        logger.info(f"Initial scan completed, found {len(self._file_info_cache)} files.")

    def _scan_folder_file_changes(self):
        """Scan configured folders for file changes."""
        try:
            current_time = datetime.now()
            current_files = set()
            for folder_path in self._watch_folder_paths:
                folder_files = self._scan_folder_files(folder_path, self._recursive)
                current_files.update(folder_files)

            new_files, updated_files = self._detect_new_and_updated_files(current_files)
            deleted_files = self._detect_deleted_files(current_files)

            self._generate_events(new_files, "file_created", current_time)
            self._generate_events(updated_files, "file_updated", current_time)
            self._generate_events(deleted_files, "file_deleted", current_time)

            self._last_scan_time = current_time
            if new_files or updated_files or deleted_files:
                self._last_activity_time = current_time
                logger.info(
                    f"File scan completed: {len(new_files)} new, {len(updated_files)} updated, {len(deleted_files)} deleted."
                )
        except Exception as e:
            logger.exception(f"Folder scan failed: {e}")

    def _detect_new_and_updated_files(self, current_files: set) -> Tuple[List[str], List[str]]:
        new_files, updated_files = [], []
        for file_path in current_files:
            try:
                file_stat = os.stat(file_path)
                file_mtime = file_stat.st_mtime
                file_size = file_stat.st_size

                if file_path not in self._file_info_cache:
                    file_hash = self._get_file_hash(file_path)
                    self._file_info_cache[file_path] = {
                        "mtime": file_mtime,
                        "size": file_size,
                        "hash": file_hash,
                    }
                    new_files.append(file_path)
                    logger.debug(f"Detected new file: {file_path}")
                else:
                    cached_info = self._file_info_cache[file_path]
                    if file_mtime > cached_info["mtime"] or file_size != cached_info["size"]:
                        file_hash = self._get_file_hash(file_path)
                        if file_hash != cached_info["hash"]:
                            self._file_info_cache[file_path] = {
                                "mtime": file_mtime,
                                "size": file_size,
                                "hash": file_hash,
                            }
                            updated_files.append(file_path)
                            logger.debug(f"Detected file update: {file_path}")
            except OSError as e:
                logger.warning(f"Failed to get file stats for {file_path}: {e}")
                continue
        return new_files, updated_files

    def _detect_deleted_files(self, current_files: set) -> List[str]:
        cached_files = set(self._file_info_cache.keys())
        deleted_files = list(cached_files - current_files)
        for file_path in deleted_files:
            del self._file_info_cache[file_path]
            # todo 不仅仅要删cache，还要删除对应的向量信息等
            logger.debug(f"Detected file deletion: {file_path}")
        return deleted_files

    def _generate_events(self, file_paths: List[str], event_type: str, timestamp: datetime):
        for file_path in file_paths:
            event = {
                "event_type": event_type,
                "file_path": file_path,
                "timestamp": timestamp,
            }
            if event_type != "file_deleted":
                event["file_info"] = self._file_info_cache.get(file_path, {})
            with self._event_lock:
                self._document_events.append(event)

    def _process_file_event(self, event: Dict[str, Any]):
        """Process file events, handling deletions."""
        if event["event_type"] == "file_deleted":
            file_path = event["file_path"]
            logger.info(f"File deleted, cleaning up context: {file_path}")
            deleted_count = self._cleanup_file_context(file_path)
            logger.info(f"Cleaned up {deleted_count} context entries for deleted file: {file_path}")

    def _cleanup_file_context(self, file_path: str) -> int:
        """Clean up processed contexts associated with a deleted file."""
        try:
            # Find contexts by file_path
            contexts_dict = self._storage.get_all_processed_contexts(
                context_types=[ContextType.KNOWLEDGE_CONTEXT],
                filter={
                    "knowledge_file_path": file_path,
                },
            )
            if not contexts_dict:
                return 0

            count = 0
            # Iterate over context types and their context lists
            for context_type, contexts in contexts_dict.items():
                # 二次校验
                if context_type != ContextType.KNOWLEDGE_CONTEXT:
                    continue
                for ctx in contexts:
                    # Get ID from ProcessedContext object (or dict if applicable)
                    ctx_id = (
                        getattr(ctx, "id", None) if not isinstance(ctx, dict) else ctx.get("id")
                    )

                    if ctx_id:
                        # Delete using id and the correct context_type
                        if self._storage.delete_processed_context(
                            id=ctx_id, context_type=context_type
                        ):
                            count += 1
            return count
        except Exception as e:
            logger.exception(f"Failed to clean up context for file {file_path}: {e}")
            return 0

    def _create_context_from_event(self, event: Dict[str, Any]) -> Optional[RawContextProperties]:
        """Create RawContextProperties from a file event."""
        event_type = event.get("event_type", "")
        if event_type in ["file_created", "file_updated"]:
            file_path = event["file_path"]
            file_ext = os.path.splitext(file_path)[1].lower()

            content_format = self._get_content_format(file_ext)
            if content_format is None:
                logger.debug(f"Skipping unsupported file type: {file_path}")
                return None

            content_text = ""
            if content_format == ContentFormat.TEXT:
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content_text = f.read()
                except Exception as e:
                    logger.warning(f"Could not read text content from {file_path}: {e}")

            return RawContextProperties(
                source=ContextSource.LOCAL_FILE,
                content_format=content_format,
                content_text=content_text,
                content_path=file_path,
                create_time=event["timestamp"],
                filter_path=file_path,
                additional_info={
                    "file_path": file_path,
                    "file_name": os.path.basename(file_path),
                    "file_type": file_ext,
                    "event_type": event_type,
                    "file_info": event.get("file_info", {}),
                },
                enable_merge=False,
            )
        return None

    def _get_content_format(self, file_ext: str) -> Optional[ContentFormat]:
        """Map file extension to ContentFormat."""
        if file_ext in {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}:
            return ContentFormat.IMAGE
        if file_ext in {
            ".pdf",
            ".docx",
            ".doc",
            ".pptx",
            ".ppt",
            ".xlsx",
            ".xls",
            ".csv",
            ".jsonl",
        }:
            return ContentFormat.FILE
        if file_ext in {".md", ".txt"}:
            return ContentFormat.TEXT
        return None

    def _scan_folder_files(self, folder_path: str, recursive: bool) -> List[str]:
        """Scan a folder for supported files."""
        files = []
        try:
            folder_path = Path(folder_path)
            if not folder_path.exists() or not folder_path.is_dir():
                logger.warning(f"Folder does not exist or is not a directory: {folder_path}")
                return files

            iterator = folder_path.rglob("*") if recursive else folder_path.iterdir()
            for file_path in iterator:
                if file_path.is_file() and self._is_supported_file_type(str(file_path)):
                    try:
                        if file_path.stat().st_size <= self._max_file_size:
                            files.append(str(file_path.absolute()))
                    except OSError as e:
                        logger.warning(f"Failed to get file stats for {file_path}: {e}")
        except Exception as e:
            logger.exception(f"Error scanning folder {folder_path}: {e}")
        return files

    def _is_supported_file_type(self, file_path: str) -> bool:
        """Check if the file type is supported."""
        return os.path.splitext(file_path)[1].lower() in self._supported_formats

    def _get_file_hash(self, file_path: str) -> str:
        """Calculate the SHA-256 hash of a file."""
        try:
            hash_sha256 = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            logger.warning(f"Failed to calculate hash for file {file_path}: {e}")
            return ""

    def _get_config_schema_impl(self) -> Dict[str, Any]:
        """Get configuration schema implementation."""
        return {
            "properties": {
                "capture_interval": {
                    "type": "integer",
                    "description": "Capture interval (seconds)",
                    "minimum": 1,
                    "default": 3,
                },
                "monitor_interval": {
                    "type": "integer",
                    "description": "Monitor interval (seconds)",
                    "minimum": 1,
                    "default": 5,
                },
                "initial_scan": {
                    "type": "boolean",
                    "description": "Whether to perform initial scan",
                    "default": True,
                },
                "watch_folder_paths": {
                    "type": "array",
                    "description": "List of folder paths to monitor",
                    "items": {"type": "string"},
                    "default": ["./watch_folder"],
                },
                "recursive": {
                    "type": "boolean",
                    "description": "Whether to scan folders recursively",
                    "default": True,
                },
                "max_file_size": {
                    "type": "integer",
                    "description": "Maximum file size to process (bytes)",
                    "minimum": 1,
                    "default": 104857600,  # 100MB
                },
            }
        }

    def _validate_config_impl(self, config: Dict[str, Any]) -> bool:
        """Validate configuration implementation."""
        try:
            for key in ["capture_interval", "monitor_interval", "max_file_size"]:
                val = config.get(key)
                if val is not None and (not isinstance(val, int) or val < 1):
                    logger.error(f"{key} must be an integer greater than 0")
                    return False

            watch_folder_paths = config.get("watch_folder_paths", [])
            if not isinstance(watch_folder_paths, list) or not all(
                isinstance(p, str) for p in watch_folder_paths
            ):
                logger.error("watch_folder_paths must be a list of strings")
                return False

            return True
        except Exception as e:
            logger.exception(f"Configuration validation failed: {e}")
            return False

    def _get_status_impl(self) -> Dict[str, Any]:
        """Get status implementation."""
        return {
            "monitor_interval": self._monitor_interval,
            "pending_events": len(self._document_events),
            "last_scan_time": self._last_scan_time.isoformat() if self._last_scan_time else None,
            "is_monitoring": not self._stop_event.is_set(),
            "watched_folders": self._watch_folder_paths,
            "cached_files": len(self._file_info_cache),
        }

    def _get_statistics_impl(self) -> Dict[str, Any]:
        """Get statistics implementation."""
        return {
            "total_processed": self._total_processed,
            "last_activity_time": (
                self._last_activity_time.isoformat() if self._last_activity_time else None
            ),
        }

    def _reset_statistics_impl(self) -> None:
        """Reset statistics implementation."""
        self._total_processed = 0
        self._last_activity_time = None
        with self._event_lock:
            self._document_events.clear()
