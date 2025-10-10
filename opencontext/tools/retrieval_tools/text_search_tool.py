# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Text semantic search tool
Supports semantic search using natural language queries, returning relevant context records
"""

from typing import Any, Dict, List
from opencontext.tools.retrieval_tools.base_retrieval_tool import BaseRetrievalTool, RetrievalToolFilter, TimeRangeFilter
from opencontext.models.enums import ContextType, ContextSimpleDescriptions, get_context_type_options
from opencontext.models.context import Vectorize
from opencontext.utils.logging_utils import get_logger

logger = get_logger(__name__)


class TextSearchTool(BaseRetrievalTool):
    """Text semantic search tool"""
    
    def __init__(self):
        super().__init__()
    
    @classmethod
    def get_name(cls) -> str:
        return "text_search"
    
    @classmethod
    def get_description(cls) -> str:
        context_descriptions = []
        for context_type in ContextType:
            desc_info = ContextSimpleDescriptions[context_type]
            context_descriptions.append(f"- {context_type.value}: {desc_info['description']}")
        descriptions_text = '\n'.join(context_descriptions)
        return f"""Semantic search tool for finding contextually relevant information using natural language queries. Returns ranked results based on meaning and relevance rather than exact keyword matches.

**When to use this tool:**
- When the query involves concepts, themes, or topics (e.g., "learning activities about machine learning", "discussions about project planning")
- When looking for information semantically related to a description or question
- When exact keywords are unknown but the general topic or meaning is clear
- When exploring historical activities, knowledge, or discussions by topic
- When filtering by context type (activity, intent, semantic, procedural, state, entity)
- When time-based filtering or entity screening is needed

**When NOT to use this tool:**
- For precise entity lookups → use profile_entity instead
- For structured data filtering → use filter_context instead

**Key features:**
- Understands query intent and finds semantically similar content
- Supports time range filtering (start/end timestamps with timezone)
- Supports entity-based filtering (find contexts mentioning specific people/projects)
- Configurable result count (top_k: 1-100, default 20)

**Supported context types:**
{descriptions_text}"""
    
    @classmethod
    def get_parameters(cls) -> Dict[str, Any]:
        """Get tool parameter definitions"""
        # Dynamically generate context_type description
        context_descriptions = []
        for context_type in ContextType:
            if context_type == ContextType.ENTITY_CONTEXT:
                continue
            desc_info = ContextSimpleDescriptions[context_type.value]
            context_descriptions.append(f"- {context_type.value}: {desc_info['description']}. {desc_info['purpose']}")
        context_type_desc = "Detailed description of context types:\n" + '\n'.join(context_descriptions)

        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language query text for semantic search"
                },
                "context_type": {
                    "type": "string",
                    "enum": get_context_type_options(),
                    "description": context_type_desc
                },
                "entities": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Entity list for filtering records containing specific entities (e.g., person names, project names, concept names)"
                },
                "time_range": {
                    "type": "object",
                    "properties": {
                        "start": {"type": "integer", "description": "Start time in seconds timestamp, leave empty if no limit"},
                        "end": {"type": "integer", "description": "End time in seconds timestamp, leave empty if no limit"},
                        "timezone": {"type": "string", "default": "local"},
                        "time_type": {
                            "type": "string", 
                            "enum": ["create_time_ts", "update_time_ts", "event_time_ts"], 
                            "default": "event_time_ts",
                            "description": "Choose appropriate time type based on query"
                        }
                    },
                    "description": "Time range filter"
                },
                "top_k": {
                    "type": "integer",
                    "default": 20,
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Number of results to return"
                }
            },
            "required": ["query", "context_type"]
        }
    
    def execute(self, **kwargs) -> List[Dict[str, Any]]:
        """Execute semantic search"""
        query = kwargs.get("query")
        context_type_str = kwargs.get("context_type")
        entities = kwargs.get("entities", [])
        time_range = kwargs.get("time_range")
        top_k = kwargs.get("top_k", 20)
        
        # Validate required parameters
        if not query:
            return [{"error": "query parameter is required"}]
        
        if not context_type_str or context_type_str not in get_context_type_options():
            return [{
                "error": f"Invalid context_type: {context_type_str}. Must be one of: {', '.join(get_context_type_options())}"
            }]
        filters = RetrievalToolFilter()
        filters.entities = entities
        
        if time_range:
            filters.time_range = TimeRangeFilter(**time_range)
        
        try:
            vectorize = Vectorize(text=query)
            search_results = self.storage.search(
                query=vectorize,
                context_types=[context_type_str],
                filters=self._build_filters(filters),
                top_k=top_k
            )
            formatted_results = self._format_results(search_results)
            for result in formatted_results:
                result["context_type"] = context_type_str
                context_desc = ContextSimpleDescriptions.get(ContextType(context_type_str), {})
                if context_desc:
                    result["context_description"] = context_desc.get("description", "")
            return formatted_results
        except Exception as e:
            logger.error(f"TextSearchTool execute exception for {context_type_str}: {str(e)}")
            return [{"error": f"Error occurred during semantic search: {str(e)}"}]