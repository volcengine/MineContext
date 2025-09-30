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
        return f"""Directly retrieve context records of specified types through precise filter conditions without semantic matching. Suitable for exact retrieval scenarios with clear query conditions, such as searching by time range, filtering by entities, retrieving by context type, and other structured queries. Supports multi-dimensional combination filtering and flexible sorting methods, efficiently locating target records from large amounts of data. Supports the following context types:\n{descriptions_text}"""
    
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
                    "description": "Entity list for filtering records containing specific entities (e.g., person names, project names, concept names)"
                },
                "time_range": {
                    "type": "object",
                    "properties": {
                        "start": {"type": "integer", "description": "Start time in seconds timestamp, leave empty if no limit"},
                        "end": {"type": "integer", "description": "End time in seconds timestamp, leave empty if no limit"},
                        # "timezone": {"type": "string", "default": "local"},
                        "time_type": {
                            "type": "string", 
                            "enum": ["create_time_ts", "update_time_ts", "event_time_ts"], 
                            "default": "event_time_ts",
                            "description": "Time type: create_time_ts (creation time), update_time_ts (update time), event_time_ts (event time)"
                        }
                    },
                    "description": "Time range filter",
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