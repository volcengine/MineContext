# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Semantic context retrieval tool
Retrieves knowledge concepts and technical principles from ChromaDB
"""

from opencontext.models.enums import ContextType
from opencontext.tools.retrieval_tools.base_context_retrieval_tool import BaseContextRetrievalTool


class SemanticContextTool(BaseContextRetrievalTool):
    """
    Semantic context retrieval tool

    Retrieves knowledge and conceptual information including:
    - Technical concepts and definitions
    - System architectures and design patterns
    - Theoretical principles and mechanisms
    - Core knowledge points and explanations

    Supports both semantic search (with query) and filter-based retrieval (without query)
    """

    CONTEXT_TYPE = ContextType.SEMANTIC_CONTEXT

    @classmethod
    def get_name(cls) -> str:
        """Get tool name"""
        return "retrieve_semantic_context"

    @classmethod
    def get_description(cls) -> str:
        """Get tool description"""
        return """Retrieve knowledge concepts and technical principles from the semantic context.

**What this tool retrieves:**
- Technical concept definitions and explanations
- System architectures and technical stacks
- Design patterns and best practices
- Theoretical principles and technical mechanisms
- Core knowledge points with educational value
- Reusable technical reference information

**When to use this tool:**
- When you need to know "what is this" or "how does it work"
- When looking for technical knowledge and concept explanations
- When searching for system architecture or design information
- When you want to understand principles and mechanisms
- When needing reference knowledge for learning or documentation

**Two modes of operation:**
1. **With query** (semantic search): Provide a natural language query to find semantically relevant knowledge
   - Example: "React Hooks explanation", "microservices architecture patterns"
2. **Without query** (filter-only): Retrieve knowledge based on time range and/or entities
   - Example: Get all concepts added last month, or knowledge about specific technologies

**Filter options:**
- Time range filtering (by event_time, create_time, or update_time)
- Entity filtering (find knowledge mentioning specific technologies, concepts, frameworks)
- Configurable result count (top_k: 1-100, default 20)

**Best for:**
- Understanding technical concepts and principles
- Learning system architectures and design patterns
- Finding reference knowledge and documentation
- Exploring theoretical foundations and mechanisms"""

    @classmethod
    def get_parameters(cls):
        """Get tool parameters with semantic-specific descriptions"""
        base_params = super().get_parameters()

        # Customize query description for semantic context
        base_params["properties"]["query"]["description"] = (
            "Natural language query for semantic search of knowledge and concepts. "
            "Examples: 'Docker container principles', 'authentication mechanisms', 'database indexing'. "
            "Leave empty to perform filter-only retrieval."
        )

        return base_params
