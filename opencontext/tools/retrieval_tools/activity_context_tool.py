# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Activity context retrieval tool
Retrieves behavioral activity history records from ChromaDB
"""

from opencontext.models.enums import ContextType
from opencontext.tools.retrieval_tools.base_context_retrieval_tool import BaseContextRetrievalTool


class ActivityContextTool(BaseContextRetrievalTool):
    """
    Activity context retrieval tool

    Retrieves behavioral activity history records including:
    - Completed tasks
    - Participated meetings and activities
    - Historical user actions and operations

    Supports both semantic search (with query) and filter-based retrieval (without query)
    """

    CONTEXT_TYPE = ContextType.ACTIVITY_CONTEXT

    @classmethod
    def get_name(cls) -> str:
        """Get tool name"""
        return "retrieve_activity_context"

    @classmethod
    def get_description(cls) -> str:
        """Get tool description"""
        return """Retrieve behavioral activity history records from the activity context.

**What this tool retrieves:**
- Historical actions and operations performed by users
- Completed tasks and their outcomes
- Meetings, training sessions, and learning activities attended
- Communication records and interactions with others
- Task execution processes and results with clear timestamps

**When to use this tool:**
- When you need to know "what has been done" or "what activities occurred"
- When looking for historical user behaviors and action patterns
- When searching for past completed tasks or events
- When you want to understand temporal sequences of user actions
- When analyzing behavioral patterns and experience accumulation

**Two modes of operation:**
1. **With query** (semantic search): Provide a natural language query to find semantically relevant activities
   - Example: "meetings about product planning", "learning activities on Python"
2. **Without query** (filter-only): Retrieve activities based on time range and/or entities
   - Example: Get all activities from last week, or activities involving specific people

**Filter options:**
- Time range filtering (by event_time, create_time, or update_time)
- Entity filtering (find activities mentioning specific people, projects, teams)
- Configurable result count (top_k: 1-100, default 20)

**Best for:**
- Reviewing what happened in the past
- Understanding user behavior patterns
- Tracking task completion history
- Analyzing collaboration and interaction records"""

    @classmethod
    def get_parameters(cls):
        """Get tool parameters with activity-specific descriptions"""
        base_params = super().get_parameters()

        # Customize query description for activity context
        base_params["properties"]["query"]["description"] = (
            "Natural language query for semantic search of activity records. "
            "Examples: 'meetings about Q4 planning', 'coding activities last week', 'discussions with team members'. "
            "Leave empty to perform filter-only retrieval."
        )

        return base_params
