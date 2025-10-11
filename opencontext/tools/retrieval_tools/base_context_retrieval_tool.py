# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Base context retrieval tool class for ChromaDB-based context retrieval
Provides common functionality for searching and filtering processed contexts
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple, Optional
from opencontext.tools.base import BaseTool
from opencontext.models.context import Vectorize, ProcessedContext
from opencontext.storage.global_storage import get_storage
from opencontext.tools.profile_tools.profile_entity_tool import ProfileEntityTool
from opencontext.models.enums import ContextType, ContextSimpleDescriptions
from opencontext.utils.logging_utils import get_logger

logger = get_logger(__name__)


@dataclass
class TimeRangeFilter:
    """Time range filter conditions"""
    start: Optional[int] = None
    end: Optional[int] = None
    timezone: Optional[str] = None
    time_type: Optional[str] = "event_time_ts"


@dataclass
class ContextRetrievalFilter:
    """Context retrieval filter conditions"""
    time_range: Optional[TimeRangeFilter] = None
    entities: List[str] = field(default_factory=list)


class BaseContextRetrievalTool(BaseTool):
    """
    Base class for context retrieval tools
    Provides common functionality for ChromaDB-based context search and filtering
    """

    # Subclasses should override this to specify their context type
    CONTEXT_TYPE: ContextType = None

    def __init__(self):
        super().__init__()
        # Initialize user entity unification tool
        self.profile_entity_tool = ProfileEntityTool()

        if self.CONTEXT_TYPE is None:
            raise ValueError("Subclass must define CONTEXT_TYPE")

    @property
    def storage(self):
        """Get storage from global singleton"""
        return get_storage()

    def _build_filters(self, filters: ContextRetrievalFilter) -> Dict[str, Any]:
        """Build filter conditions for storage backend"""
        build_filter = {}

        # Time range filter
        if filters.time_range is not None and filters.time_range.time_type:
            time_type = filters.time_range.time_type
            build_filter[time_type] = {}
            if filters.time_range.start:
                build_filter[time_type]["$gte"] = filters.time_range.start
            if filters.time_range.end:
                build_filter[time_type]["$lte"] = filters.time_range.end

        # Entity filter with normalization
        if filters.entities is not None and filters.entities:
            # Use Profile entity tool to handle entity unification
            unify_result = self.profile_entity_tool.execute(
                entities=filters.entities,
                operation="match_entities",
                context_info=""
            )
            if unify_result.get("success"):
                # Extract matched standardized entity names
                matches = unify_result.get("matches", [])
                unified_entities = [match.get("entity_canonical_name", match["input_entity"]) for match in matches]
                if not unified_entities:
                    unified_entities = filters.entities
                build_filter["entities"] = unified_entities
            else:
                build_filter["entities"] = filters.entities

        return build_filter

    def _execute_search(self,
                       query: Optional[str],
                       filters: ContextRetrievalFilter,
                       top_k: int = 20) -> List[Tuple[ProcessedContext, float]]:
        """
        Execute search operation

        Args:
            query: Optional search query. If provided, performs semantic search.
                  If None, performs filter-only retrieval.
            filters: Filter conditions
            top_k: Number of results to return

        Returns:
            List of (context, score) tuples
        """
        context_type_str = self.CONTEXT_TYPE.value
        built_filters = self._build_filters(filters)

        if query:
            # Semantic search with query
            vectorize = Vectorize(text=query)
            return self.storage.search(
                query=vectorize,
                context_types=[context_type_str],
                filters=built_filters,
                top_k=top_k
            )
        else:
            # Filter-only retrieval without query
            results_dict = self.storage.get_all_processed_contexts(
                context_types=[context_type_str],
                limit=top_k,
                filter=built_filters
            )

            # Convert results to (context, score) format
            results = []
            contexts = results_dict.get(context_type_str, [])
            for ctx in contexts:
                results.append((ctx, 1.0))  # No similarity score for filter-only

            return results[:top_k]

    def _format_context_result(self,
                              context: ProcessedContext,
                              score: float,
                              additional_fields: Dict[str, Any] = None) -> Dict[str, Any]:
        """Format single context result"""
        result = {
            "similarity_score": score,
            "context": context.get_llm_context_string(),
            "context_type": self.CONTEXT_TYPE.value
        }

        # Add context type description
        context_desc = ContextSimpleDescriptions.get(self.CONTEXT_TYPE.value, {})
        if context_desc:
            result["context_description"] = context_desc.get("description", "")

        # Add additional fields
        if additional_fields:
            result.update(additional_fields)

        return result

    def _format_results(self,
                       search_results: List[Tuple[ProcessedContext, float]]) -> List[Dict[str, Any]]:
        """Format search results"""
        formatted_results = []

        for context, score in search_results:
            result = self._format_context_result(context, score)
            formatted_results.append(result)

        return formatted_results

    @classmethod
    def get_parameters(cls) -> Dict[str, Any]:
        """
        Get tool parameter definitions
        Subclasses can override to customize parameters
        """
        context_desc = ContextSimpleDescriptions.get(cls.CONTEXT_TYPE.value, {})

        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Optional natural language query for semantic search. If not provided, will perform filter-only retrieval."
                },
                "entities": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Entity list for filtering records containing specific entities (e.g., person names, project names). For current user, use 'current_user'"
                },
                "time_range": {
                    "type": "object",
                    "properties": {
                        "start": {
                            "type": "integer",
                            "description": "Start timestamp in seconds (Unix epoch). MUST be a calculated integer, not a string or expression"
                        },
                        "end": {
                            "type": "integer",
                            "description": "End timestamp in seconds (Unix epoch). MUST be a calculated integer, not a string or expression"
                        },
                        "time_type": {
                            "type": "string",
                            "enum": ["create_time_ts", "update_time_ts", "event_time_ts"],
                            "default": "event_time_ts",
                            "description": "Time type: create_time_ts (creation time), update_time_ts (update time), event_time_ts (event time)"
                        }
                    },
                    "description": f"Time range filter for {cls.CONTEXT_TYPE.value}. Context: {context_desc.get('description', '')}. Start and end must be pre-calculated integer timestamps."
                },
                "top_k": {
                    "type": "integer",
                    "default": 20,
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Number of results to return"
                }
            },
            "required": []
        }

    def execute(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Execute context retrieval

        Args:
            query: Optional search query
            entities: Optional entity list for filtering
            time_range: Optional time range filter
            top_k: Number of results to return (default 20)

        Returns:
            List of formatted context results
        """
        query = kwargs.get("query")
        entities = kwargs.get("entities", [])
        time_range = kwargs.get("time_range")
        top_k = kwargs.get("top_k", 20)

        # Build filter conditions
        filters = ContextRetrievalFilter()
        filters.entities = entities

        if time_range:
            filters.time_range = TimeRangeFilter(**time_range)

        try:
            # Execute search
            search_results = self._execute_search(
                query=query,
                filters=filters,
                top_k=top_k
            )

            # Format and return results
            return self._format_results(search_results)

        except Exception as e:
            logger.error(f"{self.get_name()} execute exception: {str(e)}")
            return [{"error": f"Error occurred during {self.CONTEXT_TYPE.value} retrieval: {str(e)}"}]
