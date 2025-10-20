# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Get todos tool
Retrieves todo items from SQLite todo table
"""

from typing import Any, Dict, List

from opencontext.tools.retrieval_tools.base_document_retrieval_tool import BaseDocumentRetrievalTool
from opencontext.utils.logging_utils import get_logger

logger = get_logger(__name__)


class GetTodosTool(BaseDocumentRetrievalTool):
    """
    Get todos tool

    Retrieves todo items from the todo table.
    Supports filtering by status, urgency, and time range.
    """

    TABLE_NAME = "todo"
    DOCUMENT_TYPE_NAME = "todos"

    @classmethod
    def get_name(cls) -> str:
        """Get tool name"""
        return "get_todos"

    @classmethod
    def get_description(cls) -> str:
        """Get tool description"""
        return """Retrieve todo items from the todo storage.

**What this tool retrieves:**
- Todo items and tasks
- Task content and descriptions
- Start and end times
- Status (0=pending, 1=completed)
- Urgency levels
- Assignee information
- Creation reasons

**When to use this tool:**
- When you need to check pending or completed tasks
- When looking for todos with specific status or urgency
- When searching for tasks within a time period
- When reviewing task assignments and reasons

**Filter options:**
- Status filtering (pending=0, completed=1)
- Urgency filtering (priority levels)
- Time range filtering (by start_time and end_time)
- Pagination support (limit and offset)

**Returns:**
- Todo ID, content
- Status, urgency, assignee, reason
- Creation, start, and end timestamps"""

    @classmethod
    def get_parameters(cls) -> Dict[str, Any]:
        """Get tool parameters"""
        base_params = super().get_parameters()

        # Add todos-specific parameters
        base_params["properties"].update(
            {
                "status": {
                    "type": "integer",
                    "enum": [0, 1],
                    "description": "Filter by status: 0=pending, 1=completed. Leave empty to retrieve all statuses.",
                },
                "urgency": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 10,
                    "description": "Filter by minimum urgency level (0-10). Leave empty for all urgency levels.",
                },
                "start_time": {
                    "type": "integer",
                    "description": "Filter todos that start after this timestamp (Unix epoch seconds)",
                },
                "end_time": {
                    "type": "integer",
                    "description": "Filter todos that end before this timestamp (Unix epoch seconds)",
                },
            }
        )

        return base_params

    def _format_document_result(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Format single document result"""
        return {
            "id": doc.get("id"),
            "content": doc.get("content"),
            "status": doc.get("status"),
            "status_label": "completed" if doc.get("status") == 1 else "pending",
            "urgency": doc.get("urgency"),
            "assignee": doc.get("assignee"),
            "reason": doc.get("reason"),
            "created_at": doc.get("created_at"),
            "start_time": doc.get("start_time"),
            "end_time": doc.get("end_time"),
            "document_type": self.DOCUMENT_TYPE_NAME,
        }

    def execute(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Execute todos retrieval

        Args:
            status: Optional status filter (0=pending, 1=completed)
            urgency: Optional minimum urgency filter
            start_time: Optional start time filter (timestamp)
            end_time: Optional end time filter (timestamp)
            limit: Number of results to return (default 20)
            offset: Offset for pagination (default 0)

        Returns:
            List of formatted todo items
        """
        status = kwargs.get("status")
        urgency = kwargs.get("urgency")
        start_time = kwargs.get("start_time")
        end_time = kwargs.get("end_time")
        limit = kwargs.get("limit", 20)
        offset = kwargs.get("offset", 0)

        try:
            # Call SQLite backend to get todos
            documents = self.storage.get_todos(
                status=status,
                start_time=self._parse_datetime(start_time),
                end_time=self._parse_datetime(end_time),
                limit=limit,
                offset=offset,
            )

            # Apply urgency filter if specified (SQLite backend doesn't support this directly)
            if urgency is not None:
                documents = [doc for doc in documents if doc.get("urgency", 0) >= urgency]

            # Format and return results
            return self._format_results(documents)

        except Exception as e:
            logger.error(f"GetTodosTool execute exception: {str(e)}")
            return [{"error": f"Error occurred while retrieving todos: {str(e)}"}]
