# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
System Monitor - Collects and manages various system metrics
"""

import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from opencontext.models.enums import ContextType
from opencontext.storage.global_storage import get_storage
from opencontext.utils.logging_utils import get_logger

logger = get_logger(__name__)


@dataclass
class TokenUsage:
    """Token usage statistics"""

    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ProcessingMetrics:
    """Processing performance metrics"""

    processor_name: str
    operation: str
    duration_ms: int
    context_type: Optional[str] = None
    context_count: int = 1
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class RetrievalMetrics:
    """Retrieval performance metrics"""

    operation: str
    duration_ms: int
    snippets_count: int = 0
    query: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ContextTypeStats:
    """Context type statistics"""

    context_type: str
    count: int
    last_update: datetime = field(default_factory=datetime.now)


@dataclass
class ProcessingError:
    """Processing error record"""

    error_message: str
    processor_name: str = ""
    context_count: int = 0
    timestamp: datetime = field(default_factory=datetime.now)


class Monitor:
    """System Monitor"""

    def __init__(self):
        self._lock = threading.RLock()
        self._storage = None

        # Token usage history (keep last 1000 records)
        self._token_usage_history: deque = deque(maxlen=1000)
        self._token_usage_by_model: Dict[str, List[TokenUsage]] = defaultdict(list)

        # Processing performance history (keep last 1000 records)
        self._processing_history: deque = deque(maxlen=1000)
        self._processing_by_type: Dict[str, List[ProcessingMetrics]] = defaultdict(list)

        # Retrieval performance history (keep last 1000 records)
        self._retrieval_history: deque = deque(maxlen=1000)

        # Context type statistics cache
        self._context_type_stats: Dict[str, ContextTypeStats] = {}
        self._stats_cache_ttl = 60  # Cache for 60 seconds
        self._last_stats_update = datetime.min

        # Processing error records (keep last 50 records)
        self._processing_errors: deque = deque(maxlen=50)

        # Start time
        self._start_time = datetime.now()
        self._storage = get_storage()
        logger.info("System monitor initialized")

    def record_token_usage(
        self, model: str, prompt_tokens: int = 0, completion_tokens: int = 0, total_tokens: int = 0
    ):
        """Record token usage"""
        with self._lock:
            usage = TokenUsage(
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
            )
            self._token_usage_history.append(usage)
            self._token_usage_by_model[model].append(usage)

            # Limit history size per model
            if len(self._token_usage_by_model[model]) > 100:
                self._token_usage_by_model[model] = self._token_usage_by_model[model][-100:]

    def record_processing_metrics(
        self,
        processor_name: str,
        operation: str,
        duration_ms: int,
        context_type: Optional[str] = None,
        context_count: int = 1,
    ):
        """Record processing performance metrics"""
        with self._lock:
            metrics = ProcessingMetrics(
                processor_name=processor_name,
                operation=operation,
                duration_ms=duration_ms,
                context_type=context_type,
                context_count=context_count,
            )
            self._processing_history.append(metrics)
            key = f"{processor_name}:{operation}"
            self._processing_by_type[key].append(metrics)

            # Limit history size
            if len(self._processing_by_type[key]) > 100:
                self._processing_by_type[key] = self._processing_by_type[key][-100:]

    def record_retrieval_metrics(
        self, operation: str, duration_ms: int, snippets_count: int = 0, query: Optional[str] = None
    ):
        """Record retrieval performance metrics"""
        with self._lock:
            metrics = RetrievalMetrics(
                operation=operation,
                duration_ms=duration_ms,
                snippets_count=snippets_count,
                query=query,
            )
            self._retrieval_history.append(metrics)

    def get_context_type_stats(self, force_refresh: bool = False) -> Dict[str, int]:
        """Get record count for each context_type"""
        now = datetime.now()

        # Check if cache is expired
        if not force_refresh and now - self._last_stats_update < timedelta(
            seconds=self._stats_cache_ttl
        ):
            return {k: v.count for k, v in self._context_type_stats.items()}

        # Fetch latest statistics from storage
        if self._storage:
            try:
                with self._lock:
                    # Use dedicated count method for better efficiency
                    if hasattr(self._storage, "get_all_processed_context_counts"):
                        stats = self._storage.get_all_processed_context_counts()
                    else:
                        # Fallback to old method
                        stats = {}
                        for context_type in ContextType:
                            if hasattr(self._storage, "get_processed_context_count"):
                                count = self._storage.get_processed_context_count(
                                    context_type.value
                                )
                            else:
                                # Final fallback: fetch actual records and count
                                contexts = self._storage.get_all_processed_contexts(
                                    context_types=[context_type.value], limit=10000
                                )
                                count = 0
                                if isinstance(contexts, dict):
                                    count = sum(
                                        len(backend_contexts) if backend_contexts else 0
                                        for backend_contexts in contexts.values()
                                    )
                                elif isinstance(contexts, list):
                                    count = len(contexts)

                            stats[context_type.value] = count

                    # Update cache
                    for context_type_value, count in stats.items():
                        self._context_type_stats[context_type_value] = ContextTypeStats(
                            context_type=context_type_value, count=count
                        )

                    self._last_stats_update = now
                    logger.debug(f"Refreshed context_type statistics: {stats}")
                    return stats
            except Exception as e:
                logger.error(f"Failed to get context_type statistics: {e}")

        # Return cached data or empty dict
        return {k: v.count for k, v in self._context_type_stats.items()}

    def get_token_usage_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get token usage summary"""
        cutoff_time = datetime.now() - timedelta(hours=hours)

        with self._lock:
            recent_usage = [u for u in self._token_usage_history if u.timestamp >= cutoff_time]

            summary = {
                "total_records": len(recent_usage),
                "by_model": {},
                "total_tokens": 0,
                "total_prompt_tokens": 0,
                "total_completion_tokens": 0,
            }

            model_stats = defaultdict(
                lambda: {"count": 0, "total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0}
            )

            for usage in recent_usage:
                model_stats[usage.model]["count"] += 1
                model_stats[usage.model]["total_tokens"] += usage.total_tokens
                model_stats[usage.model]["prompt_tokens"] += usage.prompt_tokens
                model_stats[usage.model]["completion_tokens"] += usage.completion_tokens

                summary["total_tokens"] += usage.total_tokens
                summary["total_prompt_tokens"] += usage.prompt_tokens
                summary["total_completion_tokens"] += usage.completion_tokens

            summary["by_model"] = dict(model_stats)
            return summary

    def get_processing_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get processing performance summary"""
        cutoff_time = datetime.now() - timedelta(hours=hours)

        with self._lock:
            recent_metrics = [m for m in self._processing_history if m.timestamp >= cutoff_time]

            summary = {
                "total_operations": len(recent_metrics),
                "by_processor": {},
                "by_context_type": {},
                "avg_duration_ms": 0,
                "total_contexts_processed": 0,
            }

            if not recent_metrics:
                return summary

            processor_stats = defaultdict(
                lambda: {"count": 0, "total_duration": 0, "avg_duration": 0, "contexts": 0}
            )
            context_stats = defaultdict(
                lambda: {"count": 0, "total_duration": 0, "avg_duration": 0}
            )

            total_duration = 0
            total_contexts = 0

            for metrics in recent_metrics:
                # Stats by processor
                key = f"{metrics.processor_name}:{metrics.operation}"
                processor_stats[key]["count"] += 1
                processor_stats[key]["total_duration"] += metrics.duration_ms
                processor_stats[key]["contexts"] += metrics.context_count

                # Stats by context type
                if metrics.context_type:
                    context_stats[metrics.context_type]["count"] += 1
                    context_stats[metrics.context_type]["total_duration"] += metrics.duration_ms

                total_duration += metrics.duration_ms
                total_contexts += metrics.context_count

            # Calculate averages
            for stats in processor_stats.values():
                if stats["count"] > 0:
                    stats["avg_duration"] = stats["total_duration"] / stats["count"]

            for stats in context_stats.values():
                if stats["count"] > 0:
                    stats["avg_duration"] = stats["total_duration"] / stats["count"]

            summary["by_processor"] = dict(processor_stats)
            summary["by_context_type"] = dict(context_stats)
            summary["avg_duration_ms"] = (
                total_duration / len(recent_metrics) if recent_metrics else 0
            )
            summary["total_contexts_processed"] = total_contexts

            return summary

    def get_todo_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Get TODO task statistics"""
        try:
            if self._storage:
                end_time = datetime.now()
                start_time = end_time - timedelta(hours=hours)

                # Get all TODOs
                todos = self._storage.get_todos(start_time=start_time, end_time=end_time)

                completed = 0
                pending = 0

                for todo in todos:
                    if todo.get("status", 0) == 1:  # 1 means completed
                        completed += 1
                    else:
                        pending += 1

                return {
                    "total": len(todos),
                    "completed": completed,
                    "pending": pending,
                    "time_range_hours": hours,
                }
        except Exception as e:
            logger.error(f"Failed to get TODO statistics: {e}")

        return {"total": 0, "completed": 0, "pending": 0, "time_range_hours": hours}

    def get_tips_count(self, hours: int = 24) -> Dict[str, Any]:
        """Get Tips count"""
        try:
            if self._storage:
                end_time = datetime.now()
                start_time = end_time - timedelta(hours=hours)

                tips = self._storage.get_tips(start_time=start_time, end_time=end_time)

                return {"total": len(tips), "time_range_hours": hours}
        except Exception as e:
            logger.error(f"Failed to get Tips count: {e}")

        return {"total": 0, "time_range_hours": hours}

    def get_activity_count(self, hours: int = 24) -> Dict[str, Any]:
        """Get activity record count"""
        try:
            if self._storage:
                end_time = datetime.now()
                start_time = end_time - timedelta(hours=hours)
                activities = self._storage.get_activities(start_time=start_time, end_time=end_time)
                return {"total": len(activities), "time_range_hours": hours}
        except Exception as e:
            logger.error(f"Failed to get activity count: {e}")
        return {"total": 0, "time_range_hours": hours}

    def record_processing_error(
        self,
        error_message: str,
        processor_name: str = "",
        context_count: int = 0,
        timestamp: datetime = None,
    ):
        """Record processing error"""
        if timestamp is None:
            timestamp = datetime.now()
        with self._lock:
            error = ProcessingError(
                error_message=error_message,
                processor_name=processor_name,
                context_count=context_count,
                timestamp=timestamp,
            )
            self._processing_errors.append(error)

    def get_processing_errors(self, hours: int = 1, top_n: int = 5) -> Dict[str, Any]:
        """Get top N processing errors"""
        cutoff_time = datetime.now() - timedelta(hours=hours)

        with self._lock:
            recent_errors = [e for e in self._processing_errors if e.timestamp >= cutoff_time]

            # Sort by timestamp in descending order and get top N
            recent_errors.sort(key=lambda x: x.timestamp, reverse=True)
            top_errors = recent_errors[:top_n]

            errors_list = [
                {
                    "error_message": e.error_message,
                    "processor_name": e.processor_name,
                    "context_count": e.context_count,
                    "timestamp": e.timestamp.isoformat(),
                }
                for e in top_errors
            ]

            return {
                "errors": errors_list,
                "total_errors": len(recent_errors),
                "time_range_hours": hours,
            }

    def get_retrieval_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get retrieval performance summary"""
        cutoff_time = datetime.now() - timedelta(hours=hours)

        with self._lock:
            recent_metrics = [m for m in self._retrieval_history if m.timestamp >= cutoff_time]

            summary = {
                "total_operations": len(recent_metrics),
                "by_operation": {},
                "avg_duration_ms": 0,
                "total_snippets": 0,
                "avg_snippets_per_query": 0,
            }

            if not recent_metrics:
                return summary

            operation_stats = defaultdict(
                lambda: {"count": 0, "total_duration": 0, "avg_duration": 0, "snippets": 0}
            )

            total_duration = 0
            total_snippets = 0

            for metrics in recent_metrics:
                operation_stats[metrics.operation]["count"] += 1
                operation_stats[metrics.operation]["total_duration"] += metrics.duration_ms
                operation_stats[metrics.operation]["snippets"] += metrics.snippets_count

                total_duration += metrics.duration_ms
                total_snippets += metrics.snippets_count

            # Calculate averages
            for stats in operation_stats.values():
                if stats["count"] > 0:
                    stats["avg_duration"] = stats["total_duration"] / stats["count"]

            summary["by_operation"] = dict(operation_stats)
            summary["avg_duration_ms"] = (
                total_duration / len(recent_metrics) if recent_metrics else 0
            )
            summary["total_snippets"] = total_snippets
            summary["avg_snippets_per_query"] = (
                total_snippets / len(recent_metrics) if recent_metrics else 0
            )

            return summary

    def get_system_overview(self) -> Dict[str, Any]:
        """Get system overview"""
        uptime = datetime.now() - self._start_time

        return {
            "uptime_seconds": int(uptime.total_seconds()),
            "uptime_formatted": str(uptime).split(".")[0],
            "context_types": self.get_context_type_stats(),
            "token_usage": self.get_token_usage_summary(hours=24),
            "processing": self.get_processing_summary(hours=24),
            "todo_stats": self.get_todo_stats(hours=24),
            "tips_count": self.get_tips_count(hours=24),
            "activity_count": self.get_activity_count(hours=24),
            "last_updated": datetime.now().isoformat(),
        }


# Global monitor instance
_monitor: Optional[Monitor] = None
_monitor_lock = threading.Lock()


def get_monitor() -> Monitor:
    """Get global monitor instance"""
    global _monitor
    if _monitor is None:
        with _monitor_lock:
            if _monitor is None:
                _monitor = Monitor()
    return _monitor


def initialize_monitor() -> Monitor:
    """Initialize monitor"""
    monitor = get_monitor()
    return monitor


# Convenient global functions for reporting metrics
def record_token_usage(
    model: str, prompt_tokens: int = 0, completion_tokens: int = 0, total_tokens: int = 0
):
    """Global function: Record token usage"""
    get_monitor().record_token_usage(model, prompt_tokens, completion_tokens, total_tokens)


def record_processing_metrics(
    processor_name: str,
    operation: str,
    duration_ms: int,
    context_type: Optional[str] = None,
    context_count: int = 1,
):
    """Global function: Record processing performance metrics"""
    get_monitor().record_processing_metrics(
        processor_name, operation, duration_ms, context_type, context_count
    )


def record_retrieval_metrics(
    operation: str, duration_ms: int, snippets_count: int = 0, query: Optional[str] = None
):
    """Global function: Record retrieval performance metrics"""
    get_monitor().record_retrieval_metrics(operation, duration_ms, snippets_count, query)


def record_processing_error(
    error_message: str, processor_name: str = "", context_count: int = 0, timestamp: datetime = None
):
    """Global function: Record processing error"""
    get_monitor().record_processing_error(error_message, processor_name, context_count, timestamp)
