# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Get tips tool
Retrieves tips from SQLite tips table
"""

from typing import Any, Dict, List

from opencontext.tools.retrieval_tools.base_document_retrieval_tool import BaseDocumentRetrievalTool
from opencontext.utils.logging_utils import get_logger

logger = get_logger(__name__)


class GetTipsTool(BaseDocumentRetrievalTool):
    """
    Get tips tool

    Retrieves tips and suggestions from the tips table.
    Supports filtering by creation time.
    """

    TABLE_NAME = "tips"
    DOCUMENT_TYPE_NAME = "tips"

    @classmethod
    def get_name(cls) -> str:
        """Get tool name"""
        return "get_tips"

    @classmethod
    def get_description(cls) -> str:
        """Get tool description"""
        return """Retrieve tips and suggestions from the tips storage.

**What this tool retrieves:**
- Helpful tips and suggestions
- Best practices and recommendations
- Quick hints and reminders
- User guidance and advice

**When to use this tool:**
- When you need to review helpful tips
- When looking for suggestions within a time period
- When searching for specific guidance or recommendations
- When gathering best practices and advice

**Filter options:**
- Time range filtering (by creation time)
- Pagination support (limit and offset)

**Returns:**
- Tip ID and content
- Creation timestamp"""

    @classmethod
    def get_parameters(cls) -> Dict[str, Any]:
        """Get tool parameters"""
        base_params = super().get_parameters()

        # Add tips-specific parameters
        base_params["properties"].update(
            {
                "created_after": {
                    "type": "integer",
                    "description": "Filter tips created after this timestamp (Unix epoch seconds)",
                },
                "created_before": {
                    "type": "integer",
                    "description": "Filter tips created before this timestamp (Unix epoch seconds)",
                },
            }
        )

        return base_params

    def _format_document_result(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Format single document result"""
        return {
            "id": doc.get("id"),
            "content": doc.get("content"),
            "created_at": doc.get("created_at"),
            "document_type": self.DOCUMENT_TYPE_NAME,
        }

    def execute(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Execute tips retrieval

        Args:
            created_after: Optional creation time lower bound (timestamp)
            created_before: Optional creation time upper bound (timestamp)
            limit: Number of results to return (default 20)
            offset: Offset for pagination (default 0)

        Returns:
            List of formatted tip records
        """
        created_after = kwargs.get("created_after")
        created_before = kwargs.get("created_before")
        limit = kwargs.get("limit", 20)
        offset = kwargs.get("offset", 0)

        try:
            # Call SQLite backend to get tips
            documents = self.storage.get_tips(
                start_time=self._parse_datetime(created_after),
                end_time=self._parse_datetime(created_before),
                limit=limit,
                offset=offset,
            )

            # Format and return results
            return self._format_results(documents)

        except Exception as e:
            logger.error(f"GetTipsTool execute exception: {str(e)}")
            return [{"error": f"Error occurred while retrieving tips: {str(e)}"}]
