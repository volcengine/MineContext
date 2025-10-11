# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Filter context retrieval tool
Supports directly retrieving processed context records through various filter conditions without semantic search
"""

from typing import Any, Dict, List
from opencontext.tools.retrieval_tools.base_retrieval_tool import BaseRetrievalTool, RetrievalToolFilter, TimeRangeFilter
from opencontext.models.enums import ContextType, ContextSimpleDescriptions, get_context_type_options
from opencontext.utils.logging_utils import get_logger

logger = get_logger(__name__)


class FilterContextTool(BaseRetrievalTool):
    """Filter context retrieval tool"""
    
    def __init__(self):
        super().__init__()
    
    @classmethod
    def get_name(cls) -> str:
        return "filter_context"
    
    @classmethod
    def get_description(cls) -> str:
        """Dynamically generate tool description including all supported context types"""
        context_descriptions = []
        for context_type in ContextType:
            desc_info = ContextSimpleDescriptions[context_type]
            context_descriptions.append(f"- {context_type.value}: {desc_info['description']}")
        descriptions_text = '\n'.join(context_descriptions)
        return f"""Direct filter-based retrieval tool that returns records matching exact criteria without semantic analysis. Uses structured filtering for precise, deterministic results.

**When to use this tool:**
- When you need records from a specific time range (e.g., "all activities from yesterday", "contexts between 10am-2pm")
- When filtering by specific entities (e.g., "contexts mentioning person X", "all records related to project Y")
- When you need to retrieve all records of a specific context type without searching by content
- When combining multiple exact filters (time + entities + type)
- When you want chronologically sorted results (newest/oldest first)

**When NOT to use this tool:**
- For semantic or conceptual searches → use text_search instead
- When query involves understanding meaning or intent → use text_search instead

**Key features:**
- Supports precise time range filtering with flexible time types (event_time, create_time, update_time)
- Supports entity-based filtering (find all contexts mentioning specific people/projects)
- Configurable sort order (time ascending/descending, update time ascending/descending)
- Returns results deterministically based on filter criteria
- Efficient for large-scale filtering operations
- Configurable result count (top_k: 1-100, default 20)

**Supported context types:**
{descriptions_text}"""
    
    @classmethod
    def get_parameters(cls) -> Dict[str, Any]:
        """Get tool parameter definitions"""
        context_descriptions = []
        for context_type in ContextType:
            desc_info = ContextSimpleDescriptions[context_type]
            context_descriptions.append(f"- {context_type.value}: {desc_info['description']}. {desc_info['purpose']}")
        context_type_desc = "Detailed description of context types:\n" + '\n'.join(context_descriptions)

        return {
            "type": "object",
            "properties": {
                "context_type": {
                    "type": "string",
                    "enum": get_context_type_options(),
                    "description": context_type_desc
                },
                "entities": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Entity list for filtering records containing specific entities (e.g., person names, project names, concept names). For queries related to the current user, always use 'current_user' as the entity name (aliases: 'me', 'user', 'myself')"
                },
                "time_range": {
                    "type": "object",
                    "properties": {
                        "start": {"type": "integer", "description": "Start timestamp in seconds (Unix epoch). MUST be an integer like 1760148653, NOT a string or expression like '1760170253-86400'. Calculate the value first, then pass the integer result. Leave empty if no lower bound"},
                        "end": {"type": "integer", "description": "End timestamp in seconds (Unix epoch). MUST be an integer like 1760170253, NOT a string or expression. Calculate the value first, then pass the integer result. Leave empty if no upper bound"},
                        # "timezone": {"type": "string", "default": "local"},
                        "time_type": {
                            "type": "string",
                            "enum": ["create_time_ts", "update_time_ts", "event_time_ts"],
                            "default": "event_time_ts",
                            "description": "Time type: create_time_ts (creation time), update_time_ts (update time), event_time_ts (event time)"
                        }
                    },
                    "description": "Time range filter. **CRITICAL**: start and end MUST be calculated integers before calling this tool. Examples: (1) 'Last 24 hours' when now=1760171602: calculate start=1760085202 (=1760171602-86400), end=1760171602; (2) 'October 11th' or 'today': start=beginning of that day (00:00:00), end=end of that day (23:59:59) or current time if today. For a specific day, ALWAYS use the day's start time (00:00:00) as start, not current time. Never pass strings like '1760171602-86400'. Durations: 1h=3600s, 6h=21600s, 24h=86400s, 7d=604800s. Ensure start < end",
                },
                "sort_by": {
                    "type": "string",
                    "enum": ["time_desc", "time_asc", "update_desc", "update_asc"],
                    "default": "time_desc",
                    "description": "Sort method: time_desc (descending by event time), time_asc (ascending by event time), update_desc (descending by update time), update_asc (ascending by update time)"
                },
                "top_k": {
                    "type": "integer",
                    "default": 20,
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Number of results to return"
                }
            },
            "required": ["context_type"]
        }
    
    def execute(self, **kwargs) -> List[Dict[str, Any]]:
        """Execute filter retrieval"""
        context_type_str = kwargs.get("context_type")
        entities = kwargs.get("entities", [])
        time_range = kwargs.get("time_range")
        metadata_filters = kwargs.get("metadata_filters", {})
        sort_by = kwargs.get("sort_by", "time_desc")
        top_k = kwargs.get("top_k", 20)
        
        # Validate context_type
        if not context_type_str or context_type_str not in get_context_type_options():
            return [{
                "error": f"Invalid context_type: {context_type_str}. Must be one of: {', '.join(get_context_type_options())}"
            }]
        
        # Build filter conditions
        filters = RetrievalToolFilter()
        filters.entities = entities
        
        if time_range:
            filters.time_range = TimeRangeFilter(**time_range)
        
        # Merge additional metadata filter conditions
        build_filters = self._build_filters(filters)
        if metadata_filters:
            build_filters.update(metadata_filters)
        
        try:
            # Directly get processed contexts
            results_dict = self.storage.get_all_processed_contexts(
                context_types=[context_type_str],
                limit=top_k,
                filter=build_filters
            )
            
            # Convert results to standard format
            results = []
            contexts = results_dict.get(context_type_str, [])
            
            # Sort based on sort_by
            if sort_by == "time_desc":
                contexts.sort(key=lambda x: getattr(x, 'event_time_ts', 0), reverse=True)
            elif sort_by == "time_asc":
                contexts.sort(key=lambda x: getattr(x, 'event_time_ts', 0))
            elif sort_by == "update_desc":
                contexts.sort(key=lambda x: getattr(x, 'update_time_ts', 0), reverse=True)
            elif sort_by == "update_asc":
                contexts.sort(key=lambda x: getattr(x, 'update_time_ts', 0))
            
            # Format results
            for ctx in contexts[:top_k]:
                result = self._format_context_result(ctx, 1.0)  # No similarity score, use 1.0
                result["context_type"] = context_type_str
                context_desc = ContextSimpleDescriptions.get(ContextType(context_type_str), {})
                if context_desc:
                    result["context_description"] = context_desc.get("description", "")
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"FilterContextTool execute exception for {context_type_str}: {str(e)}")
            return [{"error": f"Error occurred during filter retrieval: {str(e)}"}]