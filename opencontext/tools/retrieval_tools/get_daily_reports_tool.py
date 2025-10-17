# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Get daily reports tool
Retrieves daily/weekly reports from SQLite vaults table
"""

from typing import Any, Dict, List

from opencontext.tools.retrieval_tools.base_document_retrieval_tool import BaseDocumentRetrievalTool
from opencontext.utils.logging_utils import get_logger

logger = get_logger(__name__)


class GetDailyReportsTool(BaseDocumentRetrievalTool):
    """
    Get daily reports tool

    Retrieves daily/weekly reports and notes from the vaults table.
    Supports filtering by document type, creation time, and update time.
    """

    TABLE_NAME = "vaults"
    DOCUMENT_TYPE_NAME = "daily_reports"

    @classmethod
    def get_name(cls) -> str:
        """Get tool name"""
        return "get_daily_reports"

    @classmethod
    def get_description(cls) -> str:
        """Get tool description"""
        return """Retrieve daily reports, weekly reports, and notes from the vaults storage.

**What this tool retrieves:**
- Daily reports and summaries
- Weekly reports and retrospectives
- Personal notes and documentation
- Structured markdown documents

**When to use this tool:**
- When you need to review past daily/weekly reports
- When looking for specific notes or documentation
- When analyzing work summaries over time
- When searching for reports within a specific time range

**Filter options:**
- Time range filtering (by creation time or update time)
- Document type filtering (DailyReport, WeeklyReport, Note)
- Pagination support (limit and offset)

**Returns:**
- Report ID, title, summary, content
- Creation and update timestamps
- Document type and tags"""

    @classmethod
    def get_parameters(cls) -> Dict[str, Any]:
        """Get tool parameters"""
        base_params = super().get_parameters()

        # Add document-specific parameters
        base_params["properties"].update(
            {
                "document_type": {
                    "type": "string",
                    "enum": ["DailyReport", "WeeklyReport", "Note"],
                    "description": "Filter by document type. Leave empty to retrieve all types.",
                },
                "created_after": {
                    "type": "integer",
                    "description": "Filter reports created after this timestamp (Unix epoch seconds)",
                },
                "created_before": {
                    "type": "integer",
                    "description": "Filter reports created before this timestamp (Unix epoch seconds)",
                },
                "updated_after": {
                    "type": "integer",
                    "description": "Filter reports updated after this timestamp (Unix epoch seconds)",
                },
                "updated_before": {
                    "type": "integer",
                    "description": "Filter reports updated before this timestamp (Unix epoch seconds)",
                },
            }
        )

        return base_params

    def _format_document_result(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Format single document result"""
        return {
            "id": doc.get("id"),
            "title": doc.get("title"),
            "summary": doc.get("summary"),
            "content": doc.get("content"),
            "tags": doc.get("tags"),
            "document_type": doc.get("document_type"),
            "created_at": doc.get("created_at"),
            "updated_at": doc.get("updated_at"),
            "is_folder": doc.get("is_folder", False),
        }

    def execute(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Execute daily reports retrieval

        Args:
            document_type: Optional document type filter
            created_after: Optional creation time lower bound (timestamp)
            created_before: Optional creation time upper bound (timestamp)
            updated_after: Optional update time lower bound (timestamp)
            updated_before: Optional update time upper bound (timestamp)
            limit: Number of results to return (default 20)
            offset: Offset for pagination (default 0)

        Returns:
            List of formatted report documents
        """
        document_type = kwargs.get("document_type")
        created_after = kwargs.get("created_after")
        created_before = kwargs.get("created_before")
        updated_after = kwargs.get("updated_after")
        updated_before = kwargs.get("updated_before")
        limit = kwargs.get("limit", 20)
        offset = kwargs.get("offset", 0)

        try:
            # Call SQLite backend to get vaults
            documents = self.storage.get_vaults(
                limit=limit,
                offset=offset,
                is_deleted=False,
                document_type=document_type,
                created_after=self._parse_datetime(created_after),
                created_before=self._parse_datetime(created_before),
                updated_after=self._parse_datetime(updated_after),
                updated_before=self._parse_datetime(updated_before),
            )

            # Format and return results
            return self._format_results(documents)

        except Exception as e:
            logger.error(f"GetDailyReportsTool execute exception: {str(e)}")
            return [{"error": f"Error occurred while retrieving daily reports: {str(e)}"}]
