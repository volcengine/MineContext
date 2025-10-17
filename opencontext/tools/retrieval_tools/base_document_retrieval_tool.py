# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Base document retrieval tool class for SQLite-based document retrieval
Provides common functionality for querying structured document data
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from opencontext.storage.global_storage import get_storage
from opencontext.tools.base import BaseTool
from opencontext.utils.logging_utils import get_logger

logger = get_logger(__name__)


class BaseDocumentRetrievalTool(BaseTool):
    """
    Base class for document retrieval tools
    Provides common functionality for SQLite-based document queries
    """

    # Subclasses should override these
    TABLE_NAME: str = None
    DOCUMENT_TYPE_NAME: str = None

    def __init__(self):
        super().__init__()

        if self.TABLE_NAME is None:
            raise ValueError("Subclass must define TABLE_NAME")

    @property
    def storage(self):
        """Get storage from global singleton"""
        return get_storage()

    def _parse_datetime(self, dt_param: Any) -> Optional[datetime]:
        """
        Parse datetime parameter

        Args:
            dt_param: Can be int (timestamp), str (ISO format), or datetime object

        Returns:
            datetime object or None
        """
        if dt_param is None:
            return None

        if isinstance(dt_param, datetime):
            return dt_param
        elif isinstance(dt_param, int):
            return datetime.fromtimestamp(dt_param)
        elif isinstance(dt_param, str):
            try:
                return datetime.fromisoformat(dt_param)
            except ValueError:
                logger.warning(f"Failed to parse datetime string: {dt_param}")
                return None
        else:
            logger.warning(f"Unsupported datetime type: {type(dt_param)}")
            return None

    def _format_document_result(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format single document result

        Args:
            doc: Raw document dict from SQLite

        Returns:
            Formatted document dict
        """
        # Base formatting - subclasses can override
        return {
            "id": doc.get("id"),
            "content": doc.get("content"),
            "created_at": doc.get("created_at"),
            "document_type": self.DOCUMENT_TYPE_NAME,
        }

    def _format_results(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Format list of document results

        Args:
            documents: List of raw document dicts

        Returns:
            List of formatted document dicts
        """
        return [self._format_document_result(doc) for doc in documents]

    @classmethod
    def get_parameters(cls) -> Dict[str, Any]:
        """
        Get tool parameter definitions
        Subclasses should override to add specific parameters
        """
        return {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "default": 20,
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Number of results to return",
                },
                "offset": {
                    "type": "integer",
                    "default": 0,
                    "minimum": 0,
                    "description": "Offset for pagination",
                },
            },
            "required": [],
        }

    def execute(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Execute document retrieval
        Subclasses should override this method

        Args:
            **kwargs: Tool-specific parameters

        Returns:
            List of formatted document results
        """
        raise NotImplementedError("Subclass must implement execute method")
