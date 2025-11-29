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


@dataclass
class RecordingSessionStats:
    """Recording session statistics"""

    processed_screenshots: int = 0
    failed_screenshots: int = 0
    generated_activities: int = 0
    last_activity_time: Optional[datetime] = None
    session_start_time: datetime = field(default_factory=datetime.now)
    recent_screenshot_paths: deque = field(default_factory=lambda: deque(maxlen=5))


class Monitor:
    """System Monitor"""

    def __init__(self):
        self._lock = threading.RLock()

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

        # Recording session statistics
        self._recording_stats = RecordingSessionStats()

        # Start time
        self._start_time = datetime.now()

        # Auto cleanup old monitoring data on startup
        self._cleanup_old_data()

        logger.info("System monitor initialized")

    def _cleanup_old_data(self):
        """Clean up monitoring data older than 7 days"""

        try:
            get_storage().cleanup_old_monitoring_data(days=7)
        except Exception as e:
            logger.error(f"Failed to cleanup old monitoring data: {e}")

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

            # Persist to database
            self._persist_token_usage(model, prompt_tokens, completion_tokens, total_tokens)

    def _persist_token_usage(
        self, model: str, prompt_tokens: int, completion_tokens: int, total_tokens: int
    ):
        """Persist token usage to database"""
        try:
            get_storage().save_monitoring_token_usage(
                model, prompt_tokens, completion_tokens, total_tokens
            )
        except Exception as e:
            logger.error(f"Failed to persist token usage: {e}")

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
        try:
            with self._lock:
                stats = get_storage().get_all_processed_context_counts()
                stats = {}
                for context_type in ContextType:
                    count = get_storage().get_processed_context_count(context_type.value)
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
        """Get token usage summary from database"""
        summary = {
            "total_records": 0,
            "by_model": {},
            "total_tokens": 0,
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
        }

        try:
            rows = get_storage().query_monitoring_token_usage(hours)

            model_stats = defaultdict(
                lambda: {"count": 0, "total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0}
            )

            for row in rows:
                model = row["model"]
                prompt_tokens = row["prompt_tokens"]
                completion_tokens = row["completion_tokens"]
                total_tokens = row["total_tokens"]

                model_stats[model]["count"] += 1
                model_stats[model]["total_tokens"] += total_tokens
                model_stats[model]["prompt_tokens"] += prompt_tokens
                model_stats[model]["completion_tokens"] += completion_tokens

                summary["total_tokens"] += total_tokens
                summary["total_prompt_tokens"] += prompt_tokens
                summary["total_completion_tokens"] += completion_tokens

            summary["by_model"] = dict(model_stats)
            summary["total_records"] = len(rows)

        except Exception as e:
            logger.error(f"Failed to get token usage summary: {e}")

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

    def record_processing_stage(
        self,
        stage_name: str,
        duration_ms: int,
        status: str = "success",
        metadata: Optional[str] = None,
    ):
        """Record processing stage timing"""
        try:
            get_storage().save_monitoring_stage_timing(stage_name, duration_ms, status, metadata)
        except Exception as e:
            logger.error(f"Failed to record processing stage: {e}")

    def increment_data_count(
        self,
        data_type: str,
        count: int = 1,
        context_type: Optional[str] = None,
        metadata: Optional[str] = None,
    ):
        """Increment data count"""
        try:
            get_storage().save_monitoring_data_stats(data_type, count, context_type, metadata)
        except Exception as e:
            logger.error(f"Failed to increment data count: {e}")

    def get_stage_timing_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get stage timing summary from database"""
        summary = {
            "total_operations": 0,
            "by_stage": {},
            "avg_duration_ms": 0,
        }

        try:
            rows = get_storage().query_monitoring_stage_timing(hours)

            stage_stats = defaultdict(
                lambda: {
                    "count": 0,
                    "total_duration": 0,
                    "avg_duration": 0,
                    "success_count": 0,
                    "error_count": 0,
                }
            )

            total_duration = 0

            for row in rows:
                stage_name = row["stage_name"]
                duration_ms = row["duration_ms"]
                status = row["status"]

                stage_stats[stage_name]["count"] += 1
                stage_stats[stage_name]["total_duration"] += duration_ms

                if status == "success":
                    stage_stats[stage_name]["success_count"] += 1
                else:
                    stage_stats[stage_name]["error_count"] += 1

                total_duration += duration_ms

            # Calculate averages
            for stats in stage_stats.values():
                if stats["count"] > 0:
                    stats["avg_duration"] = int(stats["total_duration"] / stats["count"])

            summary["by_stage"] = dict(stage_stats)
            summary["total_operations"] = len(rows)
            summary["avg_duration_ms"] = int(total_duration / len(rows)) if rows else 0

        except Exception as e:
            logger.error(f"Failed to get stage timing summary: {e}")

        return summary

    def get_data_stats_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get data statistics summary from database"""
        summary = {
            "by_data_type": {},
            "total_data_processed": 0,
            "by_context_type": {},
        }

        try:
            rows = get_storage().query_monitoring_data_stats(hours)

            # Process the grouped data
            for row in rows:
                data_type = row["data_type"]
                count = row["count"]
                context_type = row["context_type"]

                # Aggregate by data type
                if data_type not in summary["by_data_type"]:
                    summary["by_data_type"][data_type] = 0
                summary["by_data_type"][data_type] += count
                summary["total_data_processed"] += count

                # Aggregate context stats (only for 'context' data_type with non-null context_type)
                if data_type == "context" and context_type is not None:
                    if context_type not in summary["by_context_type"]:
                        summary["by_context_type"][context_type] = 0
                    summary["by_context_type"][context_type] += count

        except Exception as e:
            logger.error(f"Failed to get data stats summary: {e}")

        return summary

    def get_data_stats_by_range(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Get data statistics by custom time range"""
        summary = {
            "by_data_type": {},
            "total_data_processed": 0,
            "by_context_type": {},
            "time_range": {
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
            },
        }

        try:
            rows = get_storage().query_monitoring_data_stats_by_range(start_time, end_time)

            # Process the grouped data
            for row in rows:
                data_type = row["data_type"]
                count = row["count"]
                context_type = row["context_type"]

                # Aggregate by data type
                if data_type not in summary["by_data_type"]:
                    summary["by_data_type"][data_type] = 0
                summary["by_data_type"][data_type] += count
                summary["total_data_processed"] += count

                # Aggregate context stats (only for 'context' data_type with non-null context_type)
                if data_type == "context" and context_type is not None:
                    if context_type not in summary["by_context_type"]:
                        summary["by_context_type"][context_type] = 0
                    summary["by_context_type"][context_type] += count

        except Exception as e:
            logger.error(f"Failed to get data stats by range: {e}")

        return summary

    def get_data_stats_trend(self, hours: int = 24) -> Dict[str, Any]:
        """Get data statistics trend with time series data"""
        try:
            rows = get_storage().query_monitoring_data_stats_trend(hours)

            # Organize data by data_type for easy frontend consumption
            # Structure: { 'screenshot': [{timestamp, count}, ...], 'document': [...], 'context': [...] }
            trend_data = {
                "screenshot": [],
                "document": [],
                "context": [],
            }

            # Group by timestamp and data_type
            time_buckets = {}
            for row in rows:
                timestamp = row["timestamp"]
                data_type = row["data_type"]
                count = row["count"]

                if timestamp not in time_buckets:
                    time_buckets[timestamp] = {"screenshot": 0, "document": 0, "context": 0}

                if data_type in time_buckets[timestamp]:
                    time_buckets[timestamp][data_type] += count

            # Convert to sorted time series
            sorted_timestamps = sorted(time_buckets.keys())
            for ts in sorted_timestamps:
                for data_type in ["screenshot", "document", "context"]:
                    trend_data[data_type].append(
                        {"timestamp": ts, "count": time_buckets[ts][data_type]}
                    )

            return {
                "trend": trend_data,
                "timestamps": sorted_timestamps,
            }

        except Exception as e:
            logger.error(f"Failed to get data stats trend: {e}")
            return {"trend": {"screenshot": [], "document": [], "context": []}, "timestamps": []}

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

    def increment_recording_stat(self, stat_type: str, count: int = 1):
        """Increment recording session statistics"""
        with self._lock:
            if stat_type == "processed":
                self._recording_stats.processed_screenshots += count
            elif stat_type == "failed":
                self._recording_stats.failed_screenshots += count
            elif stat_type == "activity":
                self._recording_stats.generated_activities += count
                self._recording_stats.last_activity_time = datetime.now()

    def record_screenshot_path(self, screenshot_path: str):
        """Record a screenshot path to recent screenshots list"""
        with self._lock:
            self._recording_stats.recent_screenshot_paths.append(screenshot_path)

    def get_recording_stats(self) -> Dict[str, Any]:
        """Get current recording session statistics"""
        with self._lock:
            stats = {
                "processed_screenshots": self._recording_stats.processed_screenshots,
                "failed_screenshots": self._recording_stats.failed_screenshots,
                "generated_activities": self._recording_stats.generated_activities,
                "last_activity_time": (
                    self._recording_stats.last_activity_time.isoformat()
                    if self._recording_stats.last_activity_time
                    else None
                ),
                "session_start_time": self._recording_stats.session_start_time.isoformat(),
            }

            # Calculate next activity ETA
            # Get activity generation interval from config (default 900 seconds = 15 minutes)
            try:
                from opencontext.config.global_config import GlobalConfig

                config = GlobalConfig.get_instance().get_config()
                activity_interval = (
                    config.get("content_generation", {}).get("activity", {}).get("interval", 900)
                )
            except Exception:
                activity_interval = 900

            if self._recording_stats.last_activity_time:
                elapsed = (
                    datetime.now() - self._recording_stats.last_activity_time
                ).total_seconds()
                remaining = max(0, activity_interval - elapsed)
                stats["next_activity_eta_seconds"] = int(remaining)
            else:
                elapsed = (
                    datetime.now() - self._recording_stats.session_start_time
                ).total_seconds()
                remaining = max(0, activity_interval - elapsed)
                stats["next_activity_eta_seconds"] = int(remaining)

            # Get recent errors from this session
            session_start = self._recording_stats.session_start_time
            recent_errors = [
                {
                    "error_message": e.error_message,
                    "processor_name": e.processor_name,
                    "timestamp": e.timestamp.isoformat(),
                }
                for e in self._processing_errors
                if e.timestamp >= session_start and e.processor_name == "screenshot_processor"
            ]
            stats["recent_errors"] = recent_errors[-5:]  # Last 5 errors

            # Get recent screenshots (最多5张)
            stats["recent_screenshots"] = list(self._recording_stats.recent_screenshot_paths)

            return stats

    def reset_recording_stats(self):
        """Reset recording session statistics"""
        with self._lock:
            logger.info("Resetting recording session statistics")
            self._recording_stats = RecordingSessionStats()

    def get_system_overview(self) -> Dict[str, Any]:
        """Get system overview"""
        uptime = datetime.now() - self._start_time

        return {
            "uptime_seconds": int(uptime.total_seconds()),
            "uptime_formatted": str(uptime).split(".")[0],
            "context_types": self.get_context_type_stats(),
            "token_usage_24h": self.get_token_usage_summary(hours=24),
            "token_usage_7d": self.get_token_usage_summary(hours=168),  # 7 days
            "processing": self.get_processing_summary(hours=24),
            "stage_timing": self.get_stage_timing_summary(hours=24),
            "data_stats_24h": self.get_data_stats_summary(hours=24),
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


def record_processing_stage(
    stage_name: str, duration_ms: int, status: str = "success", metadata: Optional[str] = None
):
    """Global function: Record processing stage timing"""
    get_monitor().record_processing_stage(stage_name, duration_ms, status, metadata)


def increment_screenshot_count():
    """Global function: Increment screenshot count"""
    get_monitor().increment_data_count("screenshot")


def increment_context_count(context_type: str):
    """Global function: Increment context count by type"""
    get_monitor().increment_data_count("context", context_type=context_type)


def increment_data_count(
    data_type: str,
    count: int = 1,
    context_type: Optional[str] = None,
    metadata: Optional[str] = None,
):
    """Global function: Increment data count"""
    get_monitor().increment_data_count(data_type, count, context_type, metadata)


def increment_recording_stat(stat_type: str, count: int = 1):
    """Global function: Increment recording session statistics"""
    get_monitor().increment_recording_stat(stat_type, count)


def get_recording_stats() -> Dict[str, Any]:
    """Global function: Get current recording session statistics"""
    return get_monitor().get_recording_stats()


def reset_recording_stats():
    """Global function: Reset recording session statistics"""
    get_monitor().reset_recording_stats()


def record_screenshot_path(screenshot_path: str):
    """Global function: Record a screenshot path"""
    get_monitor().record_screenshot_path(screenshot_path)
