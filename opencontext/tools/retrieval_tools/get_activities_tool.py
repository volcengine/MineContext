# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Get activities tool
Retrieves real-time activity records from SQLite activity table
"""

from typing import Any, Dict, List

from opencontext.tools.retrieval_tools.base_document_retrieval_tool import BaseDocumentRetrievalTool
from opencontext.utils.logging_utils import get_logger

logger = get_logger(__name__)


class GetActivitiesTool(BaseDocumentRetrievalTool):
    """
    Get activities tool

    Retrieves real-time activity records from the activity table.
    Supports filtering by time range.
    """

    TABLE_NAME = "activity"
    DOCUMENT_TYPE_NAME = "activities"

    @classmethod
    def get_name(cls) -> str:
        """Get tool name"""
        return "get_activities"

    @classmethod
    def get_description(cls) -> str:
        """Get tool description"""
        return """Retrieve real-time activity records from the activity storage.

**What this tool retrieves:**
- Real-time activity records and events
- Activity titles and detailed content
- Associated resources and metadata
- Activity time ranges (start and end times)

**When to use this tool:**
- When you need to review recent activities
- When looking for activities within a specific time period
- When analyzing activity patterns and frequency
- When searching for activities with specific metadata

**Filter options:**
- Time range filtering (by start_time and end_time)
- Pagination support (limit and offset)

**Returns:**
- Activity ID, title, content
- Resources and metadata (JSON format)
- Start time and end time
- Activity insights and categorization"""

    @classmethod
    def get_parameters(cls) -> Dict[str, Any]:
        """Get tool parameters"""
        base_params = super().get_parameters()

        # Add activity-specific parameters
        base_params["properties"].update(
            {
                "start_time": {
                    "type": "integer",
                    "description": "Filter activities that started after this timestamp (Unix epoch seconds)",
                },
                "end_time": {
                    "type": "integer",
                    "description": "Filter activities that ended before this timestamp (Unix epoch seconds)",
                },
            }
        )

        return base_params

    def _format_document_result(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Format single document result"""
        return {
            "id": doc.get("id"),
            "title": doc.get("title"),
            "content": doc.get("content"),
            "resources": doc.get("resources"),
            "metadata": doc.get("metadata"),
            "start_time": doc.get("start_time"),
            "end_time": doc.get("end_time"),
            "document_type": self.DOCUMENT_TYPE_NAME,
        }

    def execute(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Execute activities retrieval

        Args:
            start_time: Optional activity start time filter (timestamp)
            end_time: Optional activity end time filter (timestamp)
            limit: Number of results to return (default 20)
            offset: Offset for pagination (default 0)

        Returns:
            List of formatted activity records
        """
        start_time = kwargs.get("start_time")
        end_time = kwargs.get("end_time")
        limit = kwargs.get("limit", 20)
        offset = kwargs.get("offset", 0)

        try:
            # Call SQLite backend to get activities
            documents = self.storage.get_activities(
                start_time=self._parse_datetime(start_time),
                end_time=self._parse_datetime(end_time),
                limit=limit,
                offset=offset,
            )

            # Format and return results
            return self._format_results(documents)

        except Exception as e:
            logger.error(f"GetActivitiesTool execute exception: {str(e)}")
            return [{"error": f"Error occurred while retrieving activities: {str(e)}"}]
