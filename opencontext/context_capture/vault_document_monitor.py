#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Vault document monitoring component that monitors changes in the vaults table and generates context capture events
"""

import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from opencontext.context_capture import BaseCaptureComponent
from opencontext.models.context import RawContextProperties
from opencontext.models.enums import ContentFormat, ContextSource
from opencontext.storage.global_storage import get_storage
from opencontext.utils.logging_utils import get_logger

logger = get_logger(__name__)


class VaultDocumentMonitor(BaseCaptureComponent):
    """
    Vault document monitoring component that monitors changes in the vaults table and generates context capture events
    """

    def __init__(self):
        """Initialize Vault document monitoring component"""
        super().__init__(
            name="VaultDocumentMonitor",
            description="Monitor document changes in vaults table",
            source_type=ContextSource.TEXT,
        )
        self._storage = None
        self._monitor_interval = 5  # Monitor interval (seconds)
        self._last_scan_time = None
        self._processed_vault_ids: Set[int] = set()
        self._document_events = []
        self._event_lock = threading.RLock()
        self._monitor_thread = None
        self._stop_event = threading.Event()

        # Statistics
        self._total_processed = 0
        self._last_activity_time = None

    def _initialize_impl(self, config: Dict[str, Any]) -> bool:
        """
        Initialize document monitoring component

        Args:
            config: Component configuration

        Returns:
            bool: Whether initialization was successful
        """
        try:
            self._storage = get_storage()
            self._monitor_interval = config.get("monitor_interval", 5)

            # Set initial scan time to current time
            self._last_scan_time = datetime.now()

            logger.info(
                f"Vault document monitoring component initialized successfully, monitor interval: {self._monitor_interval}s"
            )
            return True
        except Exception as e:
            logger.exception(f"Failed to initialize Vault document monitoring component: {str(e)}")
            return False

    def _start_impl(self) -> bool:
        """
        Start document monitoring

        Returns:
            bool: Whether startup was successful
        """
        try:
            # If initial scan is configured, scan existing documents first
            if self._config.get("initial_scan", True):
                self._scan_existing_documents()

            # Start monitoring thread
            self._monitor_thread = threading.Thread(
                target=self._monitor_loop, name="vault_document_monitor", daemon=True
            )
            self._monitor_thread.start()

            logger.info("Vault document monitoring started")
            return True
        except Exception as e:
            logger.exception(f"Failed to start Vault document monitoring: {str(e)}")
            return False

    def _stop_impl(self, graceful: bool = True) -> bool:
        """
        Stop document monitoring

        Returns:
            bool: Whether stopping was successful
        """
        try:
            self._stop_event.set()

            if self._monitor_thread and self._monitor_thread.is_alive():
                self._monitor_thread.join(timeout=10 if graceful else 1)

            logger.info("Vault document monitoring stopped")
            return True
        except Exception as e:
            logger.exception(f"Failed to stop Vault document monitoring: {str(e)}")
            return False

    def _capture_impl(self) -> List[RawContextProperties]:
        """
        Execute document capture

        Returns:
            List[RawContextProperties]: List of captured context data
        """
        try:
            result = []

            # Get document events and process them
            with self._event_lock:
                events = self._document_events.copy()
                self._document_events.clear()

            for event in events:
                context_data = self._create_context_from_event(event)
                if context_data:
                    result.append(context_data)
                    self._total_processed += 1

            return result
        except Exception as e:
            logger.exception(f"Document capture failed: {str(e)}")
            return []

    def _monitor_loop(self):
        """Monitor loop that periodically checks changes in the vaults table"""
        while not self._stop_event.is_set():
            try:
                self._scan_vault_changes()
                time.sleep(self._monitor_interval)
            except Exception as e:
                logger.exception(f"Monitor loop error: {e}")
                time.sleep(self._monitor_interval)

    def _scan_existing_documents(self):
        """Scan existing documents (initial scan)"""
        try:
            logger.info("Starting initial scan of existing vault documents")
            documents = self._storage.get_vaults(limit=1000, offset=0, is_deleted=False)

            for doc in documents:
                if doc["id"] not in self._processed_vault_ids:
                    event = {
                        "event_type": "existing",
                        "vault_id": doc["id"],
                        "document_data": doc,
                        "timestamp": datetime.now(),
                    }

                    with self._event_lock:
                        self._document_events.append(event)

                    self._processed_vault_ids.add(doc["id"])

            logger.info(f"Initial scan completed, found {len(documents)} documents")
        except Exception as e:
            logger.exception(f"Initial scan failed: {e}")

    def _scan_vault_changes(self):
        """Scan changes in the vaults table"""
        try:
            # Get recent documents (based on created_at and updated_at)
            current_time = datetime.now()
            documents = self._storage.get_vaults(limit=100, offset=0, is_deleted=False)

            new_documents = []
            updated_documents = []

            for doc in documents:
                vault_id = doc["id"]
                created_at = datetime.fromisoformat(doc["created_at"].replace("Z", "+00:00"))
                updated_at = (
                    datetime.fromisoformat(doc["updated_at"].replace("Z", "+00:00"))
                    if doc.get("updated_at")
                    else created_at
                )

                # Check if it's a new document
                if vault_id not in self._processed_vault_ids:
                    if created_at > self._last_scan_time:
                        new_documents.append(doc)
                    self._processed_vault_ids.add(vault_id)
                # Check if it's an updated document
                elif updated_at > self._last_scan_time:
                    updated_documents.append(doc)

            # Process new documents
            for doc in new_documents:
                event = {
                    "event_type": "created",
                    "vault_id": doc["id"],
                    "document_data": doc,
                    "timestamp": current_time,
                }

                with self._event_lock:
                    self._document_events.append(event)

                logger.debug(
                    f"Detected new document: vault_id={doc['id']}, title={doc.get('title', '')}"
                )

            # Process updated documents
            for doc in updated_documents:
                event = {
                    "event_type": "updated",
                    "vault_id": doc["id"],
                    "document_data": doc,
                    "timestamp": current_time,
                }

                with self._event_lock:
                    self._document_events.append(event)

                logger.debug(
                    f"Detected document update: vault_id={doc['id']}, title={doc.get('title', '')}"
                )

            # Update scan time
            self._last_scan_time = current_time
            self._last_activity_time = current_time

            if new_documents or updated_documents:
                logger.info(
                    f"Scan completed: {len(new_documents)} new documents, {len(updated_documents)} updated documents"
                )

        except Exception as e:
            logger.exception(f"Failed to scan vault changes: {e}")

    def _create_context_from_event(self, event: Dict[str, Any]) -> Optional[RawContextProperties]:
        """
        Create RawContextProperties from event

        Args:
            event: Document event

        Returns:
            RawContextProperties: Context properties object
        """
        try:
            doc = event["document_data"]
            vault_id = event["vault_id"]

            # Create context data
            context_data = RawContextProperties(
                source=ContextSource.VAULT,
                content_format=ContentFormat.TEXT,
                content_text=doc.get("title", "") + doc.get("summary", "") + doc.get("content", ""),
                create_time=datetime.fromisoformat(doc["created_at"].replace("Z", "+00:00")),
                filter_path=self._get_document_path(doc),
                additional_info={
                    "vault_id": vault_id,
                    "title": doc.get("title", ""),
                    "summary": doc.get("summary", ""),
                    "tags": doc.get("tags", ""),
                    "document_type": doc.get("document_type", "vaults"),
                    "event_type": event["event_type"],
                },
                enable_merge=False,
            )

            return context_data
        except Exception as e:
            logger.exception(f"Failed to create context from event: {e}")
            return None

    def _get_document_path(self, doc: Dict[str, Any]) -> str:
        """
        Get complete path of document (based on parent_id hierarchy)

        Args:
            doc: Document data

        Returns:
            str: Document path
        """
        try:
            if not doc.get("parent_id"):
                return f"/{doc.get('title', 'untitled')}"

            # TODO: Implement complete path building logic
            # This requires recursive lookup of parent_id to build complete path
            # Return simple path for now
            return f"/folder/{doc.get('title', 'untitled')}"
        except Exception as e:
            logger.debug(f"Failed to build document path: {e}")
            return f"/{doc.get('title', 'untitled')}"

    def _get_config_schema_impl(self) -> Dict[str, Any]:
        """
        Get configuration schema implementation

        Returns:
            Dict[str, Any]: Configuration schema
        """
        return {
            "properties": {
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
            }
        }

    def _validate_config_impl(self, config: Dict[str, Any]) -> bool:
        """
        Validate configuration implementation

        Args:
            config: Configuration to validate

        Returns:
            bool: Whether configuration is valid
        """
        try:
            monitor_interval = config.get("monitor_interval", 5)
            if not isinstance(monitor_interval, int) or monitor_interval < 1:
                logger.error("monitor_interval must be an integer greater than 0")
                return False

            return True
        except Exception as e:
            logger.exception(f"Configuration validation failed: {e}")
            return False

    def _get_status_impl(self) -> Dict[str, Any]:
        """
        Get status implementation

        Returns:
            Dict[str, Any]: Status information
        """
        return {
            "monitor_interval": self._monitor_interval,
            "processed_vault_count": len(self._processed_vault_ids),
            "pending_events": len(self._document_events),
            "last_scan_time": self._last_scan_time.isoformat() if self._last_scan_time else None,
            "is_monitoring": not self._stop_event.is_set(),
        }

    def _get_statistics_impl(self) -> Dict[str, Any]:
        """
        Get statistics implementation

        Returns:
            Dict[str, Any]: Statistics information
        """
        return {
            "total_processed": self._total_processed,
            "last_activity_time": (
                self._last_activity_time.isoformat() if self._last_activity_time else None
            ),
        }

    def _reset_statistics_impl(self) -> None:
        """Reset statistics implementation"""
        self._total_processed = 0
        self._last_activity_time = None
        with self._event_lock:
            self._document_events.clear()
