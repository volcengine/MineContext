# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Procedural context retrieval tool
Retrieves operation flows and task procedures from ChromaDB
"""

from opencontext.models.enums import ContextType
from opencontext.tools.retrieval_tools.base_context_retrieval_tool import BaseContextRetrievalTool


class ProceduralContextTool(BaseContextRetrievalTool):
    """
    Procedural context retrieval tool

    Retrieves procedural information including:
    - Sequential operation steps
    - Task completion workflows
    - User interaction patterns
    - Repeatable operation procedures

    Supports both semantic search (with query) and filter-based retrieval (without query)
    """

    CONTEXT_TYPE = ContextType.PROCEDURAL_CONTEXT

    @classmethod
    def get_name(cls) -> str:
        """Get tool name"""
        return "retrieve_procedural_context"

    @classmethod
    def get_description(cls) -> str:
        """Get tool description"""
        return """Retrieve operation flows and task procedures from the procedural context.

**What this tool retrieves:**
- Sequential operation steps and workflows
- Task completion procedures and methods
- User interaction patterns with tools and interfaces
- Learnable and repeatable operation procedures
- Step-by-step guides based on temporal order

**When to use this tool:**
- When you need to know "how to do something" or "what are the steps"
- When looking for operation workflows and procedures
- When searching for task completion methods
- When you want to learn repeatable patterns and workflows
- When analyzing user interaction patterns and operation sequences

**Two modes of operation:**
1. **With query** (semantic search): Provide a natural language query to find semantically relevant procedures
   - Example: "Git workflow steps", "Docker deployment procedure"
2. **Without query** (filter-only): Retrieve procedures based on time range and/or entities
   - Example: Get all procedures documented last month, or workflows involving specific tools

**Filter options:**
- Time range filtering (by event_time, create_time, or update_time)
- Entity filtering (find procedures mentioning specific tools, technologies, processes)
- Configurable result count (top_k: 1-100, default 20)

**Best for:**
- Learning how to complete specific tasks
- Understanding operation workflows and sequences
- Finding step-by-step guides and procedures
- Analyzing user interaction patterns and best practices"""

    @classmethod
    def get_parameters(cls):
        """Get tool parameters with procedural-specific descriptions"""
        base_params = super().get_parameters()

        # Customize query description for procedural context
        base_params["properties"]["query"]["description"] = (
            "Natural language query for semantic search of operation procedures and workflows. "
            "Examples: 'Git merge workflow', 'debugging procedure', 'deployment steps'. "
            "Leave empty to perform filter-only retrieval."
        )

        return base_params
