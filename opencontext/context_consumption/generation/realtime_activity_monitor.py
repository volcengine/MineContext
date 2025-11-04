#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Real-time Activity Monitor - Generates a snapshot of recent activity.
"""

import datetime
import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, TypedDict

from opencontext.config.global_config import get_prompt_group
from opencontext.context_consumption.generation.debug_helper import DebugHelper
from opencontext.llm.global_vlm_client import generate_with_messages
from opencontext.models.context import ProcessedContext
from opencontext.models.enums import ContentFormat, ContextType
from opencontext.storage.global_storage import get_storage
from opencontext.tools.tool_definitions import (
    ALL_PROFILE_TOOL_DEFINITIONS,
    ALL_RETRIEVAL_TOOL_DEFINITIONS,
    ALL_TOOL_DEFINITIONS,
)
from opencontext.utils.logging_utils import get_logger

logger = get_logger(__name__)


@dataclass
class ActivityInsight:
    """Activity insight data structure."""

    potential_todos: List[Dict[str, str]] = field(default_factory=list)
    tip_suggestions: List[Dict[str, str]] = field(default_factory=list)
    key_entities: List[str] = field(default_factory=list)
    focus_areas: List[str] = field(default_factory=list)
    work_patterns: Dict[str, Any] = field(default_factory=dict)


class ActivitySummaryResult(TypedDict):
    """Activity summary result type."""

    title: str
    description: str
    representative_context_ids: List[str]
    category_distribution: Dict[str, float]
    extracted_insights: Dict[str, Any]


class RealtimeActivityMonitor:
    """
    Real-time Activity Monitor
    Generates a summary of recent activity, including the most valuable context information.
    """

    def generate_realtime_activity_summary(
        self, start_time: int, end_time: int
    ) -> Optional[Dict[str, Any]]:
        """Generate a real-time activity summary."""
        try:
            # Get context data
            contexts = self._get_recent_contexts(start_time, end_time)
            if not contexts:
                logger.info("No activity records found in the time range %s to %s.", start_time, end_time)
                return None

            # Generate an activity summary, including categories, insights, and the most valuable context IDs
            all_context = []
            for context_type, ctx_list in contexts.items():
                all_context.extend(ctx_list)
            logger.info(f"{len(all_context)} activity records found in the time range {start_time} to {end_time}.")
            summary_result = self._generate_concise_summary(contexts, start_time, end_time)

            if not summary_result:
                return None

            resource_data = self._extract_resource_data_from_contexts(
                all_context, summary_result.get("representative_context_ids", []), max_count=20
            )

            # Prepare metadata
            metadata = {
                "category_distribution": summary_result.get("category_distribution", {}),
                "extracted_insights": summary_result.get("extracted_insights", {}),
            }

            # Save to the activity table, including metadata
            activity_id = get_storage().insert_activity(
                title=summary_result["title"],
                content=summary_result["description"],
                resources=json.dumps(resource_data, ensure_ascii=False) if resource_data else None,
                metadata=json.dumps(metadata, ensure_ascii=False),
                start_time=datetime.datetime.fromtimestamp(start_time),
                end_time=datetime.datetime.fromtimestamp(end_time),
            )

            from opencontext.managers.event_manager import EventType, publish_event

            publish_event(
                event_type=EventType.ACTIVITY_GENERATED,
                data={
                    "doc_id": str(activity_id),
                    "doc_type": "activity",
                    "title": summary_result.get("title", ""),
                    "content": summary_result.get("content", ""),
                },
            )

            # Reset recording statistics after activity is generated
            from opencontext.monitoring import increment_recording_stat, reset_recording_stats

            increment_recording_stat("activity", 1)
            reset_recording_stats()

            logger.info(
                f"Real-time activity summary saved to the activity table, ID: {activity_id}"
            )
            return {
                "doc_id": str(activity_id),
                "title": summary_result["title"],
                "content": summary_result["description"],
                "category_distribution": summary_result.get("category_distribution", {}),
                "extracted_insights": summary_result.get("extracted_insights", {}),
            }

        except Exception as e:
            logger.exception(f"Failed to generate real-time activity summary: {e}")
            return None

    def _get_recent_contexts(
        self, start_time: int, end_time: int
    ) -> Dict[str, List[ProcessedContext]]:
        """Get a dictionary of recent context data, with context type as the key and a list of contexts as the value."""
        try:
            filters = {"update_time_ts": {"$gte": start_time, "$lte": end_time}}
            context_types = [
                ContextType.ACTIVITY_CONTEXT.value,
                ContextType.INTENT_CONTEXT.value,
            ]
            all_contexts = get_storage().get_all_processed_contexts(
                context_types=context_types, limit=10000, offset=0, filter=filters
            )
            return all_contexts

        except Exception as e:
            logger.exception(f"Failed to get recent contexts: {e}")
            return []

    def _generate_concise_summary(
        self, contexts: Dict[str, List[ProcessedContext]], start_time: int, end_time: int
    ) -> ActivitySummaryResult:
        """Generate an activity summary, including categories, insights, and the most valuable context IDs."""
        try:
            # Get the prompt template for the real-time activity monitor
            prompt_group = get_prompt_group("generation.realtime_activity_monitor")
            system_prompt = prompt_group["system"]
            user_prompt_template = prompt_group["user"]
            # Prepare context data
            context_data = {}
            for context_type, context_list in contexts.items():
                try:
                    context_data[context_type] = [
                        context.get_llm_context_string() for context in context_list
                    ]
                except Exception as e:
                    logger.debug(f"Failed to process context data: {e} {context_list}")
                    continue
            # Format time information
            start_time_str = datetime.datetime.fromtimestamp(start_time).strftime("%H:%M")
            end_time_str = datetime.datetime.fromtimestamp(end_time).strftime("%H:%M")
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Build the user prompt
            user_prompt = user_prompt_template.format(
                current_time=current_time,
                start_time_str=start_time_str,
                end_time_str=end_time_str,
                context_data=json.dumps(context_data, ensure_ascii=False, indent=2),
            )
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            response = generate_with_messages(messages)
            # print(f"user len prompt: {len(user_prompt)} response: {response}")

            # Save debug information
            DebugHelper.save_generation_debug(
                task_type="activity",
                messages=messages,
                response=response,
                metadata={
                    "start_time": start_time,
                    "end_time": end_time,
                    "num_context_types": len(context_data),
                    "total_contexts": (
                        sum(len(v) for v in context_data.values()) if context_data else 0
                    ),
                },
            )

            try:
                from opencontext.utils.json_parser import parse_json_from_response

                summary_result = parse_json_from_response(response)

                # Validate and normalize the category distribution
                category_dist = summary_result.get("category_distribution", {})
                if category_dist:
                    total = sum(category_dist.values())
                    if total > 0:
                        category_dist = {k: round(v / total, 2) for k, v in category_dist.items()}

                return {
                    "title": summary_result.get("title", "Recent Activities"),
                    "description": summary_result.get(
                        "description", "Detected various user activities."
                    ),
                    "representative_context_ids": summary_result.get(
                        "representative_context_ids", []
                    ),
                    "category_distribution": category_dist,
                    "extracted_insights": summary_result.get(
                        "extracted_insights",
                        {
                            "potential_todos": [],
                            "tip_suggestions": [],
                            "key_entities": [],
                            "focus_areas": [],
                            "work_patterns": {},
                        },
                    ),
                }
            except Exception as e:
                logger.error(f"Failed to parse JSON response: {e}")
                # Fallback: generate a basic summary
                return None

        except Exception as e:
            logger.exception(f"Failed to generate concise activity summary: {e}")
            return None

    def _find_contexts_by_ids(
        self, contexts: List[ProcessedContext], recommended_ids: List[str]
    ) -> List[ProcessedContext]:
        """Find the corresponding contexts based on a list of IDs."""
        try:
            found_contexts = []
            context_dict = {ctx.id: ctx for ctx in contexts}

            # Find in the recommended order
            for ctx_id in recommended_ids[:5]:  # At most 5
                if ctx_id in context_dict:
                    found_contexts.append(context_dict[ctx_id])

            if len(found_contexts) < 5:
                remaining_contexts = [
                    ctx for ctx in contexts if ctx.id not in [fc.id for fc in found_contexts]
                ]
                remaining_contexts.sort(
                    key=lambda x: getattr(x.properties, "importance", 5), reverse=True
                )

                needed = 5 - len(found_contexts)
                found_contexts.extend(remaining_contexts[:needed])

            logger.info(f"Found {len(found_contexts)} representative contexts.")
            return found_contexts

        except Exception as e:
            logger.exception(f"Failed to find representative contexts: {e}")
            # Fallback: return the first 5 contexts
            return contexts[:5]

    def _extract_resource_data_from_contexts(
        self, contexts: List[ProcessedContext], recommended_ids: List[str], max_count: int = 20
    ) -> List[Dict[str, Any]]:
        """Extract screenshots from contexts, prioritizing the most relevant ones."""
        sources_data: List[Dict[str, Any]] = []
        sources: Set[str] = set()
        context_dict = {ctx.id: ctx for ctx in contexts}
        for id in recommended_ids:
            if id in context_dict and context_dict[id].properties.raw_properties:
                for prop in context_dict[id].properties.raw_properties:
                    if prop.object_id in sources:
                        continue
                    if prop.content_format == ContentFormat.IMAGE:
                        if not self._is_exist_screenshot(prop.content_path):
                            continue
                        sources_data.append(
                            {"type": "image", "id": prop.object_id, "path": prop.content_path}
                        )
                    else:
                        continue
                    sources.add(prop.object_id)
                    if len(sources_data) >= max_count:
                        return sources_data
        for context in contexts:
            if context.id in recommended_ids:
                continue
            if context.extracted_data.context_type != ContextType.ACTIVITY_CONTEXT:
                continue
            if context.properties.raw_properties:
                for prop in context.properties.raw_properties:
                    if prop.content_format != ContentFormat.IMAGE:
                        continue
                    if prop.object_id in sources:
                        continue
                    if not self._is_exist_screenshot(prop.content_path):
                        continue
                    sources_data.append(
                        {"type": "image", "id": prop.object_id, "path": prop.content_path}
                    )
                    sources.add(prop.object_id)
                    break
            if len(sources_data) >= max_count:
                return sources_data
        return sources_data

    def _is_exist_screenshot(self, screenshot_path: str) -> bool:
        """
        Verify that the screenshot is valid and not duplicated.
        """
        if not screenshot_path or not isinstance(screenshot_path, str):
            return False

        # Check if it is an image file
        image_extensions = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp")
        if not any(screenshot_path.lower().endswith(ext) for ext in image_extensions):
            return False

        import os

        if os.path.isfile(screenshot_path):
            return True
        else:
            logger.debug(f"Screenshot file does not exist: {screenshot_path}")
            return False
