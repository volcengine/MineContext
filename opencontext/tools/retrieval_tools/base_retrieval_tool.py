# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Base retrieval tool class, provides common retrieval functions and formatting methods
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from opencontext.models.context import ProcessedContext, Vectorize
from opencontext.storage.global_storage import get_storage
from opencontext.tools.base import BaseTool
from opencontext.tools.profile_tools.profile_entity_tool import ProfileEntityTool


@dataclass
class TimeRangeFilter:
    """Time range filter conditions"""

    start: Optional[int] = None
    end: Optional[int] = None
    timezone: Optional[str] = None
    time_type: Optional[str] = "event_time_ts"


@dataclass
class RetrievalToolFilter:
    """Retrieval tool filter conditions"""

    time_range: Optional[TimeRangeFilter] = None
    entities: List[str] = field(default_factory=list)


class BaseRetrievalTool(BaseTool):
    """Base class for retrieval tools, provides common retrieval functions"""

    def __init__(self):
        super().__init__()
        # Initialize user entity unification tool
        self.profile_entity_tool = ProfileEntityTool()

    @property
    def storage(self):
        """Get storage from global singleton"""
        return get_storage()

    def _build_filters(self, filters: RetrievalToolFilter) -> Dict[str, Any]:
        """Build filter conditions"""
        build_filter = {}
        if filters.time_range is not None and filters.time_range.time_type:
            time_type = filters.time_range.time_type
            build_filter[time_type] = {}
            if filters.time_range.start:
                build_filter[time_type]["$gte"] = filters.time_range.start
            if filters.time_range.end:
                build_filter[time_type]["$lte"] = filters.time_range.end
        if filters.entities is not None and filters.entities:
            # Use Profile entity tool to handle entity unification
            unify_result = self.profile_entity_tool.execute(
                entities=filters.entities, operation="match_entities", context_info=""
            )
            if unify_result.get("success"):
                # Extract matched standardized entity names
                matches = unify_result.get("matches", [])
                unified_entities = [
                    match.get("entity_canonical_name", match["input_entity"]) for match in matches
                ]
                if not unified_entities:
                    unified_entities = filters.entities
                build_filter["entities"] = unified_entities
            else:
                build_filter["entities"] = filters.entities
        return build_filter

    def _execute_search(
        self, query: str, context_types: List[str], filters: RetrievalToolFilter, top_k: int = 10
    ) -> List[Tuple[ProcessedContext, float]]:
        """Execute search operation"""

        filters = self._build_filters(filters)

        if query:
            # Semantic search
            vectorize = Vectorize(text=query)
            return self.storage.search(
                query=vectorize, context_types=context_types, filters=filters, top_k=top_k
            )
        else:
            # Pure filter query
            results_dict = self.storage.get_all_processed_contexts(
                context_types=context_types, limit=top_k, filter=filters
            )

            # Convert results to (context, score) format
            results = []
            for context_type in context_types:
                contexts = results_dict.get(context_type, [])
                for ctx in contexts:
                    results.append((ctx, 1.0))

            return results[:top_k]

    def _format_context_result(
        self, context: ProcessedContext, score: float, additional_fields: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Format single context result"""
        result = {"similarity_score": score}
        result["context"] = context.get_llm_context_string()
        # Add additional fields
        if additional_fields:
            result.update(additional_fields)

        return result

    def _format_results(
        self,
        search_results: List[Tuple[ProcessedContext, float]],
        additional_processing: callable = None,
    ) -> List[Dict[str, Any]]:
        """Format search results"""
        formatted_results = []

        for context, score in search_results:
            result = self._format_context_result(context, score)

            # Execute additional processing logic
            if additional_processing:
                result = additional_processing(result, context, score)

            formatted_results.append(result)

        return formatted_results

    def execute_with_error_handling(self, **kwargs) -> List[Dict[str, Any]]:
        """Execute method with error handling"""
        try:
            return self.execute(**kwargs)
        except Exception as e:
            error_message = f"Error occurred while executing {self.get_name()}: {str(e)}"
            return [{"error": error_message}]
