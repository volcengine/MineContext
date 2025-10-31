#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Smart Tip Generator - Generates personalized reminders and suggestions based on user activity.
"""

import datetime
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TypedDict

from opencontext.config.global_config import get_prompt_group
from opencontext.context_consumption.generation.debug_helper import DebugHelper
from opencontext.llm.global_vlm_client import generate_with_messages
from opencontext.models.context import ProcessedContext
from opencontext.models.enums import ContextType
from opencontext.storage.base_storage import DocumentData
from opencontext.storage.global_storage import get_storage
from opencontext.tools.tool_definitions import ALL_TOOL_DEFINITIONS
from opencontext.utils.logging_utils import get_logger

logger = get_logger(__name__)


@dataclass
class ActivityPattern:
    """Activity pattern data structure."""

    work_time_distribution: Dict[str, float]
    category_trends: List[Dict[str, Any]]
    key_entities: List[str]
    focus_shifts: List[str]
    continuous_work_periods: List[int]


class SmartTipGenerator:
    """
    Smart Tip Generator
    Generates personalized reminders and suggestions based on the user's recent activity patterns.
    """

    def generate_smart_tip(self, start_time: int, end_time: int) -> Optional[str]:
        """
        Generate a smart tip, combining activity patterns and multi-dimensional information.
        """
        try:
            # 1. Get real-time context
            contexts = self._get_comprehensive_contexts(start_time, end_time)

            # 2. Analyze activity patterns
            activity_patterns = self._analyze_activity_patterns(hours=6)

            # 3. Get historical tips to avoid repetition
            recent_tips = self._get_recent_tips(days=1)

            # 5. Generate a reminder through comprehensive analysis
            tip_content = self._generate_intelligent_tip_with_patterns(
                contexts, activity_patterns, recent_tips, start_time, end_time
            )

            if not tip_content or len(tip_content.strip()) < 10:
                logger.info("No valuable tip content was generated.")
                return None

            # Store in the SQLite tips table
            tip_id = get_storage().insert_tip(content=tip_content)
            logger.info(f"Smart tip saved to the tips table, ID: {tip_id}")
            from opencontext.managers.event_manager import EventType, publish_event

            publish_event(
                event_type=EventType.TIP_GENERATED,
                data={
                    "doc_id": str(tip_id),
                    "doc_type": "tips",
                    "title": "intelligence reminder",
                    "content": tip_content,
                },
            )
            return {"doc_id": str(tip_id), "title": "intelligence reminder", "content": tip_content}

        except Exception as e:
            logger.exception(f"Failed to generate smart tip: {e}")
            return None

    def _analyze_activity_patterns(self, hours: int = 6) -> Dict[str, Any]:
        """Analyze activity patterns to find content that needs a reminder."""
        try:
            # Calculate the time range
            end_time = datetime.datetime.now()
            start_time = end_time - datetime.timedelta(hours=hours)

            # Query recent activity records
            activities = get_storage().get_activities(
                start_time=start_time, end_time=end_time, limit=20
            )
            if not activities:
                return {}
            patterns = {
                "work_patterns": {},
                "category_distribution": {},
                "key_entities": [],
                "tip_suggestions": [],
                "continuous_work_time": 0,
                "task_switching_count": 0,
            }

            category_counts = {}
            all_entities = []
            all_suggestions = []

            for activity in activities:
                if activity.get("metadata"):
                    try:
                        metadata = json.loads(activity["metadata"])
                        category_dist = metadata.get("category_distribution", {})
                        for category, weight in category_dist.items():
                            category_counts[category] = category_counts.get(category, 0) + weight
                        insights = metadata.get("extracted_insights", {})
                        if "key_entities" in insights:
                            all_entities.extend(insights["key_entities"])
                        if "tip_suggestions" in insights:
                            all_suggestions.extend(insights["tip_suggestions"])
                        if "work_patterns" in insights:
                            patterns["work_patterns"] = insights["work_patterns"]
                    except json.JSONDecodeError:
                        continue

            # Calculate the category distribution percentage
            total_weight = sum(category_counts.values())
            if total_weight > 0:
                patterns["category_distribution"] = {
                    k: round(v / total_weight, 2) for k, v in category_counts.items()
                }

            # Extract the most important entities
            from collections import Counter

            entity_counter = Counter(all_entities)
            patterns["key_entities"] = [entity for entity, _ in entity_counter.most_common(10)]

            # Merge suggestions
            patterns["tip_suggestions"] = all_suggestions[:5]

            # Analyze work time patterns
            if activities:
                # Calculate continuous work time
                time_diffs = []
                for i in range(1, len(activities)):
                    try:
                        prev_time = datetime.datetime.fromisoformat(
                            activities[i - 1]["end_time"].replace("Z", "+00:00")
                        )
                        curr_time = datetime.datetime.fromisoformat(
                            activities[i]["start_time"].replace("Z", "+00:00")
                        )
                        diff = (curr_time - prev_time).total_seconds() / 60  # Convert to minutes
                        time_diffs.append(diff)
                    except Exception:
                        continue

                if time_diffs:
                    # If the activity interval is less than 30 minutes, it is considered continuous work
                    continuous_periods = [d for d in time_diffs if d < 30]
                    if continuous_periods:
                        patterns["continuous_work_time"] = sum(continuous_periods)

                patterns["task_switching_count"] = len(activities)

            return patterns

        except Exception as e:
            logger.exception(f"Failed to analyze activity patterns: {e}")
            return {}

    def _get_recent_tips(self, days: int = 1) -> List[Dict[str, Any]]:
        """Get recent tips to avoid repetition."""
        try:
            end_time = datetime.datetime.now()
            today_start = end_time.replace(hour=0, minute=0, second=0, microsecond=0)
            start_time = today_start - datetime.timedelta(days=days - 1)

            # Use time parameters to filter and get recent tips
            recent_tips = get_storage().get_tips(start_time=start_time, end_time=end_time, limit=24)

            return recent_tips

        except Exception as e:
            logger.exception(f"Failed to get historical tips: {e}")
            return []

    def _get_comprehensive_contexts(self, start_time: int, end_time: int) -> List[Any]:
        """Get comprehensive context data for analysis."""
        try:
            filters = {"create_time_ts": {"$gte": start_time, "$lte": end_time}}

            # Get multiple types of context for comprehensive analysis
            context_types = [
                ContextType.ACTIVITY_CONTEXT.value,
                ContextType.SEMANTIC_CONTEXT.value,
                ContextType.INTENT_CONTEXT.value,
                ContextType.ENTITY_CONTEXT.value,
                ContextType.PROCEDURAL_CONTEXT.value,
                ContextType.STATE_CONTEXT.value,
            ]

            all_contexts = get_storage().get_all_processed_contexts(
                context_types=context_types, limit=10000, offset=0, filter=filters
            )

            contexts = []
            for context_type, context_list in all_contexts.items():
                contexts.extend(context_list)

            # Sort by time, with the newest first
            contexts.sort(key=lambda x: x.properties.create_time, reverse=True)

            return contexts

        except Exception as e:
            logger.exception(f"Failed to get context data: {e}")
            return []

    def _generate_intelligent_tip_with_patterns(
        self,
        contexts: List[Any],
        activity_patterns: Dict[str, Any],
        recent_tips: List[Dict[str, Any]],
        start_time: int,
        end_time: int,
    ) -> str:
        """
        Generate a smart tip, combining activity patterns and multi-dimensional information.

        Args:
            contexts: List of contexts.
            activity_patterns: Analysis results of activity patterns.
            recent_tips: Recent tip records.
            start_time: Start timestamp.
            end_time: End timestamp.

        Returns:
            str: Smart tip content in Markdown format.
        """
        # Get the prompt template for tip generation
        prompt_group = get_prompt_group("generation.smart_tip_generation")
        system_prompt = prompt_group["system"]
        user_prompt_template = prompt_group["user"]

        # Prepare context data
        context_data = self._prepare_context_data_for_analysis(contexts) if contexts else []

        # Format time information
        start_time_str = datetime.datetime.fromtimestamp(start_time).strftime("%H:%M:%S")
        end_time_str = datetime.datetime.fromtimestamp(end_time).strftime("%H:%M:%S")
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Build the user prompt
        user_prompt = user_prompt_template.format(
            current_time=current_time,
            start_time_str=start_time_str,
            end_time_str=end_time_str,
            context_data=(
                json.dumps(context_data, ensure_ascii=False, indent=2) if context_data else "[]"
            ),
            activity_patterns_info=(
                json.dumps(activity_patterns, ensure_ascii=False, indent=2)
                if activity_patterns
                else "{}"
            ),
            recent_tips_info=(
                json.dumps(recent_tips, ensure_ascii=False, indent=2) if recent_tips else "[]"
            ),
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        # Call the large model to generate a reminder, enabling tools to get relevant background information
        tip_content = generate_with_messages(
            messages,
            max_calls=2,
            tools=ALL_TOOL_DEFINITIONS,
        )

        # Save debug information
        DebugHelper.save_generation_debug(
            task_type="tips",
            messages=messages,
            response=tip_content,
            metadata={
                "start_time": start_time,
                "end_time": end_time,
                "num_contexts": len(context_data) if context_data else 0,
                "num_activity_patterns": len(activity_patterns) if activity_patterns else 0,
                "num_recent_tips": len(recent_tips) if recent_tips else 0,
            },
        )

        return tip_content

    def _prepare_context_data_for_analysis(self, contexts: List[ProcessedContext]) -> List[Dict]:
        """Prepare context data for analysis."""
        context_data = []
        for context in contexts:
            try:
                context_data.append(context.get_llm_context_string())

            except Exception as e:
                logger.debug(f"Failed to process context {getattr(context, 'id', 'unknown')}: {e}")
                continue
        return context_data

    def get_recent_tips(self, limit: int = 10) -> List[DocumentData]:
        """
        Get recent smart tips.

        Args:
            limit: The number of results to return.

        Returns:
            List[DocumentData]: A list of recent smart tips.
        """
        try:
            results = self.activity_manager.search_activities(
                query="", limit=limit, filters={"activity_type": "smart_tip"}
            )

            if results:
                return results.documents
            return []

        except Exception as e:
            logger.exception(f"Failed to get recent smart tips: {e}")
            return []

    def cleanup_old_tips(self, keep_hours: int = 48):
        """
        Clean up old smart tips.

        Args:
            keep_hours: The number of hours to keep, default is 48 hours.
        """
        try:
            cutoff_time = datetime.datetime.now() - datetime.timedelta(hours=keep_hours)
            cutoff_timestamp = int(cutoff_time.timestamp())

            # Get all tips
            tips = self.get_recent_tips(limit=1000)

            deleted_count = 0
            for tip in tips:
                try:
                    if "start_time" in tip.metadata:
                        tip_time = tip.metadata["start_time"]
                        if tip_time < cutoff_timestamp:
                            # Delete old tips
                            get_storage().delete_document(tip.id)
                            deleted_count += 1
                except Exception as e:
                    logger.debug(f"Failed to delete tip {tip.id}: {e}")

            if deleted_count > 0:
                logger.info(
                    f"Cleaned up {deleted_count} old smart tips over {keep_hours} hours old."
                )

        except Exception as e:
            logger.exception(f"Failed to clean up old smart tips: {e}")
