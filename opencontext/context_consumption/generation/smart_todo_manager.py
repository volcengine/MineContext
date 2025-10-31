#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Smart Todo Manager - Intelligently identifies and manages to-do items based on user activity.
"""

import datetime
import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TypedDict

from opencontext.config.global_config import get_prompt_group
from opencontext.context_consumption.generation.debug_helper import DebugHelper
from opencontext.llm.global_vlm_client import generate_with_messages
from opencontext.models.context import ContextType, Vectorize
from opencontext.storage.global_storage import get_storage
from opencontext.utils.json_parser import parse_json_from_response
from opencontext.utils.logging_utils import get_logger

logger = get_logger(__name__)


@dataclass
class TodoTask:
    """To-do task data structure."""

    title: str
    description: str
    category: str = "general"
    priority: str = "normal"
    due_date: Optional[str] = None
    due_time: Optional[str] = None
    estimated_duration: Optional[str] = None
    assignee: Optional[str] = None
    participants: List[str] = field(default_factory=list)
    context_reference: Optional[str] = None
    reason: Optional[str] = None
    created_at: Optional[str] = None


class SmartTodoManager:
    """
    Smart Todo Manager
    Intelligently identifies and generates to-do items based on user activity context.
    """

    def _map_priority_to_urgency(self, priority: str) -> int:
        """Map priority to a numerical urgency value."""
        priority_map = {"low": 0, "medium": 1, "high": 2, "urgent": 3}
        return priority_map.get(priority.lower(), 0)

    def generate_todo_tasks(self, start_time: int, end_time: int) -> Optional[str]:
        """
        Generate Todo tasks based on recent activity, combining activity insights and historical todo information.
        """
        try:
            # 1. Get insights from recent activities
            activity_insights = self._get_recent_activity_insights(start_time, end_time)
            # 2. Get regular context data
            contexts = self._get_task_relevant_contexts(start_time, end_time, activity_insights)
            # 3. Get historical todo completion status
            # historical_todos = self._get_historical_todos()
            historical_todos  = []
            # 4. Synthesize all information to generate high-quality todos
            tasks = self._extract_tasks_from_contexts_enhanced(
                contexts, start_time, end_time, activity_insights, historical_todos
            )

            if not tasks:
                return None
            # Store in the SQLite todo table
            todo_ids = []
            for task in tasks:
                participants_str = ""
                if task.get("participants") and len(task["participants"]) > 0:
                    participants_str = ",".join(task["participants"])

                content = task.get("description", "")
                reason = task.get("reason", "")
                urgency = self._map_priority_to_urgency(task.get("priority", "normal"))

                deadline = None
                if task.get("due_date"):
                    try:
                        if task.get("due_time"):
                            deadline_str = f"{task['due_date']} {task['due_time']}"
                            deadline = datetime.datetime.strptime(deadline_str, "%Y-%m-%d %H:%M")
                        else:
                            deadline = datetime.datetime.strptime(task["due_date"], "%Y-%m-%d")
                    except:
                        pass

                todo_id = get_storage().insert_todo(
                    content=content,
                    urgency=urgency,
                    end_time=deadline,
                    assignee=participants_str,
                    reason=reason,
                )
                todo_ids.append(todo_id)

                # Store todo embedding to vector database for future deduplication
                if task.get("_embedding"):
                    try:
                        get_storage().upsert_todo_embedding(
                            todo_id=todo_id,
                            content=content,
                            embedding=task["_embedding"],
                            metadata={
                                "urgency": urgency,
                                "priority": task.get("priority", "medium"),
                            },
                        )
                        logger.debug(f"Stored embedding for todo {todo_id}")
                    except Exception as e:
                        logger.warning(f"Failed to store todo embedding for {todo_id}: {e}")

            # Return the complete result for external event processing
            return {
                "content": f"{len(todo_ids)} tasks have been generated.",
                "todo_ids": todo_ids,
                "tasks": tasks,
            }

        except Exception as e:
            logger.exception(f"Failed to generate smart Todo tasks: {e}")
            return None

    def _get_recent_activity_insights(self, start: int, end: int) -> Dict[str, Any]:
        """Get insights extracted from recent activities."""
        try:
            start_time = datetime.datetime.fromtimestamp(start)
            end_time = datetime.datetime.fromtimestamp(end)
            # Query recent activity records
            activities = get_storage().get_activities(
                start_time=start_time, end_time=end_time, limit=100
            )
            if not activities:
                return {}
            merged_insights = {"potential_todos": [], "key_entities": [], "focus_areas": []}

            for activity in activities:
                # Parse metadata
                if activity.get("metadata"):
                    try:
                        metadata = json.loads(activity["metadata"])
                        insights = metadata.get("extracted_insights", {})
                        if "potential_todos" in insights:
                            merged_insights["potential_todos"].extend(insights["potential_todos"])
                        if "key_entities" in insights:
                            merged_insights["key_entities"].extend(insights["key_entities"])
                        if "focus_areas" in insights:
                            merged_insights["focus_areas"].extend(insights["focus_areas"])
                    except json.JSONDecodeError:
                        logger.debug(f"Failed to parse activity metadata: {activity.get('id')}")
                        continue
            merged_insights["key_entities"] = list(set(merged_insights["key_entities"]))[:10]
            merged_insights["focus_areas"] = list(set(merged_insights["focus_areas"]))[:5]
            return merged_insights

        except Exception as e:
            logger.exception(f"Failed to get activity insights: {e}")
            return {}

    def _get_historical_todos(self, days: int = 7, limit: int = 50) -> List[Dict[str, Any]]:
        """Get historical todo records."""
        try:
            start_time = datetime.datetime.now() - datetime.timedelta(days=days)
            todos = get_storage().get_todos(limit=limit, start_time=start_time)
            return todos
        except Exception as e:
            logger.exception(f"Failed to get historical todos: {e}")
            return []

    def _get_task_relevant_contexts(
        self, start_time: int, end_time: int, activity_insights: Dict[str, Any] = None
    ) -> List[Any]:
        """Get context data relevant to the task."""
        try:
            context_types = [
                ContextType.ACTIVITY_CONTEXT.value,
                ContextType.SEMANTIC_CONTEXT.value,
                ContextType.INTENT_CONTEXT.value,
                ContextType.ENTITY_CONTEXT.value,
            ]
            filters = {"update_time_ts": {"$gte": start_time, "$lte": end_time}}
            all_contexts = []
            if activity_insights.get("potential_todos", []):
                for todo in activity_insights["potential_todos"]:
                    text = todo["description"]
                    contexts = get_storage().search(
                        query=Vectorize(text=text),
                        top_k=5,
                        context_types=context_types,
                        filters=filters,
                    )
                    ctxs = [ctx[0] for ctx in contexts]
                    all_contexts.extend(ctxs)
            else:
                contexts = get_storage().get_all_processed_contexts(
                    context_types=context_types, limit=80, offset=0, filter=filters
                )
                for context_type, context_list in contexts.items():
                    all_contexts.extend(context_list)

            # Sort by time, with the newest first
            all_contexts.sort(key=lambda x: x.properties.create_time, reverse=True)
            logger.info(
                f"Retrieved {len(all_contexts)} context records relevant to task identification."
            )
            all_contexts_data = [ctx.get_llm_context_string() for ctx in all_contexts]
            return all_contexts_data

        except Exception as e:
            logger.exception(f"Failed to get task-relevant context: {e}")
            return []

    def _extract_tasks_from_contexts_enhanced(
        self,
        context_data: List[Any],
        start_time: int,
        end_time: int,
        activity_insights: Dict[str, Any] = None,
        historical_todos: List[Dict[str, Any]] = None,
    ) -> List[Dict]:
        """
        Task extraction, combining multiple information sources.
        """
        try:
            # Get the prompt template for task extraction
            prompt_group = get_prompt_group("generation.todo_extraction")
            system_prompt = prompt_group["system"]
            user_prompt_template = prompt_group["user"]

            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Build the user prompt
            user_prompt = user_prompt_template.format(
                current_time=current_time,
                historical_todos=(
                    json.dumps(historical_todos, ensure_ascii=False, indent=2)
                    if historical_todos
                    else "[]"
                ),
                potential_todos=(
                    json.dumps(
                        activity_insights.get("potential_todos", []), ensure_ascii=False, indent=2
                    )
                    if activity_insights
                    else "[]"
                ),
                context_data=(
                    json.dumps(context_data, ensure_ascii=False, indent=2) if context_data else "[]"
                ),
            )
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            # Call the large model to extract tasks, enabling tools to get relevant background information
            task_response = generate_with_messages(
                messages,
            )

            # Save debug information
            DebugHelper.save_generation_debug(
                task_type="todo",
                messages=messages,
                response=task_response,
                metadata={
                    "start_time": start_time,
                    "end_time": end_time,
                    "num_contexts": len(context_data) if context_data else 0,
                    "num_historical_todos": len(historical_todos) if historical_todos else 0,
                },
            )

            tasks = parse_json_from_response(task_response)
            tasks = self._post_process_tasks(tasks)

            # Apply vector-based deduplication
            tasks = self._deduplicate_with_vector_search(tasks, similarity_threshold=0.85)

            logger.info(f"Identified {len(tasks)} tasks from the context after deduplication.")
            return tasks

        except Exception as e:
            logger.exception(f"Failed to extract tasks from context: {e}")
            return []

    def _post_process_tasks(self, tasks: List[Dict]) -> List[Dict]:
        """Post-process tasks to complete information."""
        processed_tasks = []

        for task in tasks:
            try:
                if not task.get("description", "") or not task.get("description", "").strip():
                    continue
                # Ensure necessary fields exist
                processed_task = {
                    "title": task.get("title", "Untitled Task"),
                    "description": task.get("description", ""),
                    "category": task.get("category", "General Task"),
                    "priority": task.get("priority", "Medium Priority"),
                    "due_date": task.get("due_date", ""),
                    "due_time": task.get("due_time", ""),
                    "estimated_duration": task.get("estimated_duration", ""),
                    "assignee": task.get("assignee", ""),  # Task assignee
                    "participants": task.get("participants", []),  # List of participants
                    "context_reference": task.get("context_reference", ""),
                    "created_at": datetime.datetime.now().isoformat(),
                    "reason": task.get("reason", ""),
                }

                # Process the deadline
                processed_task = self._process_task_deadline(processed_task)

                # Process personnel information
                processed_task = self._process_task_people(processed_task)

                processed_tasks.append(processed_task)

            except Exception as e:
                logger.debug(f"Failed to post-process task: {e}")
                continue

        return processed_tasks

    def _process_task_deadline(self, task: Dict) -> Dict:
        """Process the task deadline."""
        try:
            current_time = datetime.datetime.now()

            # If there is no due date, set a default deadline based on priority
            if not task["due_date"]:
                if task["priority"] == "High Priority":
                    # High-priority task: today or tomorrow
                    due_date = current_time + datetime.timedelta(days=1)
                    task["due_date"] = due_date.strftime("%Y-%m-%d")
                    if not task["due_time"]:
                        task["due_time"] = "18:00"
                elif task["priority"] == "Medium Priority":
                    # Medium-priority task: within 3 days
                    due_date = current_time + datetime.timedelta(days=3)
                    task["due_date"] = due_date.strftime("%Y-%m-%d")
                else:
                    # Low-priority task: within a week
                    due_date = current_time + datetime.timedelta(days=7)
                    task["due_date"] = due_date.strftime("%Y-%m-%d")

            # If there is a date but no time, set a default time
            if task["due_date"] and not task["due_time"]:
                if task["priority"] == "High Priority":
                    task["due_time"] = "12:00"
                else:
                    task["due_time"] = "17:00"

            return task

        except Exception as e:
            logger.debug(f"Failed to process deadline for task {task.get('title', 'unknown')}: {e}")
            return task

    def _deduplicate_with_vector_search(
        self, new_tasks: List[Dict], similarity_threshold: float = 0.85
    ) -> List[Dict]:
        """Deduplicate new todos using vector similarity search"""
        from opencontext.llm.global_embedding_client import do_vectorize
        from opencontext.models.context import Vectorize
        from opencontext.storage.global_storage import get_storage

        if not new_tasks:
            return []

        storage = get_storage()
        filtered_tasks = []
        filtered_count = 0

        for task in new_tasks:
            task_text = task.get("description", "")
            if not task_text.strip():
                continue

            # Generate embedding for the task
            try:
                todo_vectorize = Vectorize(text=task_text)
                do_vectorize(todo_vectorize)
                if not todo_vectorize.vector:
                    # If embedding generation fails, conservatively keep the task
                    logger.warning(f"Unable to generate embedding for todo: {task_text[:50]}...")
                    continue

                task_embedding = todo_vectorize.vector

            except Exception as e:
                continue

            # Search for similar historical todos
            similar_todos = storage.search_similar_todos(
                query_embedding=task_embedding,
                top_k=5,
                similarity_threshold=similarity_threshold,
            )

            if similar_todos:
                # Found similar historical todo, filter out
                most_similar = similar_todos[0]
                logger.info(
                    f"🚫 Todo filtered (duplicate with historical task): "
                    f"New='{task_text}' | "
                    f"Historical='{most_similar[1]}' | "
                    f"Similarity={most_similar[2]:.3f}"
                )
                filtered_count += 1
                continue

            # Compare with already approved todos in this batch
            is_duplicate_in_batch = False
            for existing_task in filtered_tasks:
                existing_text = existing_task.get("description", "")
                try:
                    # Reuse the embedding that was already computed and cached
                    existing_embedding = existing_task.get("_embedding")
                    if not existing_embedding:
                        continue
                    similarity = self._cosine_similarity(task_embedding, existing_embedding)

                    if similarity >= similarity_threshold:
                        logger.info(
                            f"🚫 Todo filtered (duplicate within batch): "
                            f"'{task_text}' vs '{existing_text}' | "
                            f"Similarity={similarity:.3f}"
                        )
                        is_duplicate_in_batch = True
                        filtered_count += 1
                        break
                except Exception as e:
                    continue

            if not is_duplicate_in_batch:
                task["_embedding"] = task_embedding
                filtered_tasks.append(task)
        return filtered_tasks

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            import numpy as np

            v1 = np.array(vec1)
            v2 = np.array(vec2)
            norm_product = np.linalg.norm(v1) * np.linalg.norm(v2)
            if norm_product == 0:
                return 0.0
            return float(np.dot(v1, v2) / norm_product)
        except Exception as e:
            logger.error(f"Failed to calculate cosine similarity: {e}")
            return 0.0

    def _process_task_people(self, task: Dict) -> Dict:
        """Process task personnel information."""
        try:
            # Clean and validate the assignee field
            if task.get("assignee"):
                assignee = str(task["assignee"]).strip()
                if assignee and assignee != "":
                    task["assignee"] = assignee
                else:
                    task["assignee"] = ""

            # Clean and validate the participants field
            if task.get("participants"):
                if isinstance(task["participants"], list):
                    # Filter out empty and duplicate values
                    participants = [
                        str(p).strip() for p in task["participants"] if p and str(p).strip()
                    ]
                    task["participants"] = list(set(participants))  # Remove duplicates
                elif isinstance(task["participants"], str):
                    # If it is a string, try to parse it (it may be comma-separated)
                    participants = [p.strip() for p in task["participants"].split(",") if p.strip()]
                    task["participants"] = participants
                else:
                    task["participants"] = []
            else:
                task["participants"] = []

            # Ensure the assignee is not duplicated in the participants
            if task["assignee"] and task["assignee"] in task["participants"]:
                task["participants"].remove(task["assignee"])

            return task

        except Exception as e:
            logger.debug(
                f"Failed to process personnel information for task {task.get('title', 'unknown')}: {e}"
            )
            return task
