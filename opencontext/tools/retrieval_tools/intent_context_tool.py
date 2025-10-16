# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Intent context retrieval tool
Retrieves intent planning and goal records from ChromaDB
"""

from opencontext.models.enums import ContextType
from opencontext.tools.retrieval_tools.base_context_retrieval_tool import BaseContextRetrievalTool


class IntentContextTool(BaseContextRetrievalTool):
    """
    Intent context retrieval tool

    Retrieves forward-looking intent and planning records including:
    - Future plans and goals
    - Action intentions and strategies
    - Expected results and outcomes
    - Priority settings and time planning

    Supports both semantic search (with query) and filter-based retrieval (without query)
    """

    CONTEXT_TYPE = ContextType.INTENT_CONTEXT

    @classmethod
    def get_name(cls) -> str:
        """Get tool name"""
        return "retrieve_intent_context"

    @classmethod
    def get_description(cls) -> str:
        """Get tool description"""
        return """Retrieve intent planning and goal records from the intent context.

**What this tool retrieves:**
- Future plans and goal settings
- Action intentions and execution strategies
- Expected results and desired outcomes
- Priority rankings and time planning
- Forward-looking guidance and objectives

**When to use this tool:**
- When you need to know "what is planned" or "what are the goals"
- When looking for future intentions and action plans
- When searching for goal settings and expected outcomes
- When you want to understand strategic thinking and planning
- When analyzing priorities and execution strategies

**Two modes of operation:**
1. **With query** (semantic search): Provide a natural language query to find semantically relevant intentions
   - Example: "plans for next quarter", "goals about skill improvement"
2. **Without query** (filter-only): Retrieve intentions based on time range and/or entities
   - Example: Get all plans created last month, or goals involving specific projects

**Filter options:**
- Time range filtering (by event_time, create_time, or update_time)
- Entity filtering (find intentions mentioning specific people, projects, teams)
- Configurable result count (top_k: 1-100, default 20)

**Best for:**
- Understanding future plans and goals
- Reviewing strategic intentions and priorities
- Tracking goal setting and planning history
- Analyzing execution strategies and expected outcomes"""

    @classmethod
    def get_parameters(cls):
        """Get tool parameters with intent-specific descriptions"""
        base_params = super().get_parameters()

        # Customize query description for intent context
        base_params["properties"]["query"]["description"] = (
            "Natural language query for semantic search of intent and planning records. "
            "Examples: 'goals for Q4', 'plans about team building', 'learning objectives'. "
            "Leave empty to perform filter-only retrieval."
        )

        return base_params
