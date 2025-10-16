# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
State context retrieval tool
Retrieves status and progress monitoring records from ChromaDB
"""

from opencontext.models.enums import ContextType
from opencontext.tools.retrieval_tools.base_context_retrieval_tool import BaseContextRetrievalTool


class StateContextTool(BaseContextRetrievalTool):
    """
    State context retrieval tool

    Retrieves state monitoring information including:
    - Current execution status
    - Progress tracking and completion status
    - Performance indicators and metrics
    - Exception conditions and risk warnings

    Supports both semantic search (with query) and filter-based retrieval (without query)
    """

    CONTEXT_TYPE = ContextType.STATE_CONTEXT

    @classmethod
    def get_name(cls) -> str:
        """Get tool name"""
        return "retrieve_state_context"

    @classmethod
    def get_description(cls) -> str:
        """Get tool description"""
        return """Retrieve status and progress monitoring records from the state context.

**What this tool retrieves:**
- Current execution status and completion state
- Project progress and milestone tracking
- Performance indicators and quantitative metrics
- System status and health monitoring
- Exception conditions and risk warnings
- Real-time and dynamic change information

**When to use this tool:**
- When you need to know "how is the progress" or "what is the current state"
- When looking for project progress and status updates
- When searching for performance metrics and indicators
- When you want to monitor execution status and track milestones
- When analyzing system health and identifying issues

**Two modes of operation:**
1. **With query** (semantic search): Provide a natural language query to find semantically relevant status records
   - Example: "project progress updates", "system performance metrics"
2. **Without query** (filter-only): Retrieve status records based on time range and/or entities
   - Example: Get all status updates from this week, or progress reports for specific projects

**Filter options:**
- Time range filtering (by event_time, create_time, or update_time)
- Entity filtering (find status records mentioning specific projects, systems, tasks)
- Configurable result count (top_k: 1-100, default 20)

**Best for:**
- Monitoring project progress and completion status
- Tracking performance metrics and indicators
- Understanding current execution state
- Identifying exceptions and potential risks"""

    @classmethod
    def get_parameters(cls):
        """Get tool parameters with state-specific descriptions"""
        base_params = super().get_parameters()

        # Customize query description for state context
        base_params["properties"]["query"]["description"] = (
            "Natural language query for semantic search of status and progress records. "
            "Examples: 'project completion status', 'system performance metrics', 'error reports'. "
            "Leave empty to perform filter-only retrieval."
        )

        return base_params
