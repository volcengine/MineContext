#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0


"""
Context consumption manager, responsible for managing and coordinating context consumption components
"""

import asyncio
import threading
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from opencontext.context_consumption.generation.generation_report import ReportGenerator
from opencontext.context_consumption.generation.realtime_activity_monitor import (
    RealtimeActivityMonitor,
)
from opencontext.context_consumption.generation.smart_tip_generator import SmartTipGenerator
from opencontext.context_consumption.generation.smart_todo_manager import SmartTodoManager
from opencontext.managers.event_manager import EventType, get_event_manager
from opencontext.models.enums import VaultType
from opencontext.storage.global_storage import get_storage
from opencontext.utils.logging_utils import get_logger

logger = get_logger(__name__)


class ConsumptionManager:
    """
    Context consumption manager

    Responsible for managing and coordinating context consumption components, providing a unified interface for context consumption
    """

    def __init__(self):
        """Initialize context consumption manager - parameters retained for backward compatibility but not used"""
        # Statistics
        self._statistics: Dict[str, Any] = {
            "total_queries": 0,
            "total_contexts_consumed": 0,
            "consumers": {},
            "errors": 0,
        }
        # ReportGenerator instance
        self._activity_generator: Optional[ReportGenerator] = None
        self._real_activity_monitor: Optional[RealtimeActivityMonitor] = None
        self._smart_tip_generator: Optional[SmartTipGenerator] = None
        self._smart_todo_manager: Optional[SmartTodoManager] = None

        # Load configuration from GlobalConfig
        from opencontext.config.global_config import GlobalConfig

        config = GlobalConfig.get_instance().get_config()
        content_gen_config = config.get("content_generation", {}) if config else {}

        # Scheduled task configuration (load from config)
        self._scheduled_tasks_enabled = False
        self._task_timers: Dict[str, threading.Timer] = {}
        self._task_intervals = {
            "activity": content_gen_config.get("activity", {}).get("interval", 900),
            "tips": content_gen_config.get("tips", {}).get("interval", 3600),
            "todos": content_gen_config.get("todos", {}).get("interval", 1800),
        }
        self._task_enabled = {
            "activity": content_gen_config.get("activity", {}).get("enabled", True),
            "tips": content_gen_config.get("tips", {}).get("enabled", True),
            "todos": content_gen_config.get("todos", {}).get("enabled", True),
            "report": content_gen_config.get("report", {}).get("enabled", True),
        }

        # Maintain local last successful generation time
        self._last_generation_times = {
            "activity": None,
            "tips": None,
            "todos": None,
        }

        self._daily_report_time = content_gen_config.get("report", {}).get("time", "08:00")
        self._config_lock = threading.Lock()
        self._activity_generator = ReportGenerator()
        self._real_activity_monitor = RealtimeActivityMonitor()
        self._smart_tip_generator = SmartTipGenerator()
        self._smart_todo_manager = SmartTodoManager()

    @property
    def storage(self):
        return get_storage()

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics

        Returns:
            Dict[str, Any]: Statistics
        """
        return self._statistics.copy()

    def shutdown(self) -> None:
        """
        Shutdown manager
        """
        logger.info("Shutting down context consumption manager...")

        # Stop all scheduled tasks
        self.stop_scheduled_tasks()

        logger.info("Context consumption manager shutdown complete")

    def _should_generate(self, task_type: str) -> bool:
        """Check if specified task type should be generated"""
        try:
            last_time = self._last_generation_times.get(task_type)
            if last_time is None:
                return True

            elapsed = (datetime.now() - last_time).total_seconds()
            interval = self._task_intervals.get(task_type, 0)
            should_generate = elapsed >= interval
            return should_generate

        except Exception as e:
            logger.debug(f"Check {task_type} generation time failed: {e}")
            return True

    def _last_generation_time(self, task_type: str) -> Optional[datetime]:
        """Get last generation time"""
        return self._last_generation_times.get(task_type)

    def start_scheduled_tasks(self, config: Dict[str, Any] = None):
        """Start scheduled tasks"""
        if self._scheduled_tasks_enabled:
            logger.warning("Scheduled tasks are already running")
            return

        if config:
            if "daily_report_time" in config:
                self._daily_report_time = config["daily_report_time"]
            if "activity_interval" in config:
                self._task_intervals["activity"] = config["activity_interval"]
            if "tips_interval" in config:
                self._task_intervals["tips"] = config["tips_interval"]
            if "todos_interval" in config:
                self._task_intervals["todos"] = config["todos_interval"]

        self._scheduled_tasks_enabled = True

        # Start various scheduled tasks
        self._start_report_timer()
        self._start_activity_timer()
        self._start_tips_timer()
        self._start_todos_timer()

    def stop_scheduled_tasks(self):
        """Stop scheduled tasks"""
        if not self._scheduled_tasks_enabled:
            return

        self._scheduled_tasks_enabled = False

        # Cancel all timers
        for timer in self._task_timers.values():
            if timer:
                timer.cancel()
        self._task_timers.clear()

        logger.info("Scheduled tasks stopped")

    def _calculate_seconds_until_daily_time(self, target_time_str: str) -> float:
        try:
            hour, minute = map(int, target_time_str.split(":"))
            now = datetime.now()
            target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

            if target <= now:
                target += timedelta(days=1)
            return (target - now).total_seconds()
        except Exception as e:
            logger.error(
                f"Failed to parse daily report time configuration: {e}, using default 24 hours"
            )
            return 24 * 60 * 60

    def _get_last_report_time(self) -> datetime:
        """Get last daily report generation time from database, return current time if none"""
        try:
            reports = get_storage().get_vaults(
                document_type=VaultType.DAILY_REPORT.value, limit=1, offset=0, is_deleted=False
            )
            if reports:
                created_at_str = reports[0]["created_at"]
                if created_at_str:
                    return datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
            return datetime.now()
        except Exception:
            return datetime.now()

    def _start_report_timer(self):
        """Start daily report timer"""
        if not self._task_enabled.get("report", True):
            logger.info("Report task is disabled, skipping timer start")
            return

        # Get last daily report time from database
        last_report_time = self._get_last_report_time()
        self._last_report_date = (
            last_report_time.date()
        )  # Record date of last daily report generation

        def check_and_generate_daily_report():
            if not self._activity_generator or not self._task_enabled.get("report", True):
                return
            try:
                now = datetime.now()
                today = now.date()

                hour, minute = map(int, self._daily_report_time.split(":"))
                target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

                if now >= target_time and self._last_report_date != today:
                    try:
                        end_time = int(now.timestamp())
                        start_time = int((now - timedelta(days=1)).timestamp())

                        asyncio.run(self._activity_generator.generate_report(start_time, end_time))
                        # Update last report date to prevent duplicate generation on the same day
                        self._last_report_date = today
                    except Exception as e:
                        logger.exception(f"Failed to generate daily report: {e}")
            except Exception as e:
                logger.error(f"Failed to check daily report generation time: {e}")

            if self._scheduled_tasks_enabled and self._task_enabled.get("report", True):
                self._task_timers["report"] = threading.Timer(
                    60 * 30, check_and_generate_daily_report
                )
                self._task_timers["report"].start()

        check_and_generate_daily_report()

    def _start_activity_timer(self):
        """Start activity recording timer"""
        if not self._task_enabled.get("activity", True):
            logger.info("Activity task is disabled, skipping timer start")
            return

        def generate_activity():
            if not (
                self._scheduled_tasks_enabled
                and self._real_activity_monitor
                and self._task_enabled.get("activity", True)
            ):
                return

            try:
                if self._should_generate("activity"):
                    end_time = int(datetime.now().timestamp())
                    last_generation_time = self._last_generation_time("activity")
                    start_time = (
                        int(last_generation_time.timestamp())
                        if last_generation_time
                        else end_time - self._task_intervals.get("activity", 15 * 60)
                    )
                    self._real_activity_monitor.generate_realtime_activity_summary(
                        start_time, end_time
                    )
                    self._last_generation_times["activity"] = datetime.now()
            except Exception as e:
                logger.exception(f"Failed to generate activity record: {e}")

            self._schedule_next_check("activity", generate_activity)

        check_interval = self._calculate_check_interval("activity")
        self._task_timers["activity"] = threading.Timer(check_interval, generate_activity)
        self._task_timers["activity"].start()
        logger.info(
            f"Activity timer started, check interval: {check_interval}s, generation interval: {self._task_intervals['activity']}s"
        )

    def _start_tips_timer(self):
        """Start smart tips timer"""
        if not self._task_enabled.get("tips", True):
            logger.info("Tips task is disabled, skipping timer start")
            return

        def generate_tips():
            if not (
                self._scheduled_tasks_enabled
                and self._smart_tip_generator
                and self._task_enabled.get("tips", True)
            ):
                return

            try:
                if self._should_generate("tips"):
                    end_time = int(datetime.now().timestamp())
                    last_generation_time = self._last_generation_time("tips")
                    start_time = (
                        int(last_generation_time.timestamp())
                        if last_generation_time
                        else end_time - self._task_intervals.get("tips", 60 * 60)
                    )
                    self._smart_tip_generator.generate_smart_tip(start_time, end_time)
                    self._last_generation_times["tips"] = datetime.now()
            except Exception as e:
                logger.exception(f"Failed to generate smart tip: {e}")

            self._schedule_next_check("tips", generate_tips)

        check_interval = self._calculate_check_interval("tips")
        self._task_timers["tips"] = threading.Timer(check_interval, generate_tips)
        self._task_timers["tips"].start()
        logger.info(
            f"Tips timer started, check interval: {check_interval}s, generation interval: {self._task_intervals['tips']}s"
        )

    def _start_todos_timer(self):
        """Start smart todo timer"""
        if not self._task_enabled.get("todos", True):
            logger.info("Todos task is disabled, skipping timer start")
            return

        def generate_todos():
            if not (
                self._scheduled_tasks_enabled
                and self._smart_todo_manager
                and self._task_enabled.get("todos", True)
            ):
                return

            try:
                if self._should_generate("todos"):
                    end_time = int(datetime.now().timestamp())
                    last_generation_time = self._last_generation_time("todos")
                    start_time = (
                        int(last_generation_time.timestamp())
                        if last_generation_time
                        else end_time - self._task_intervals.get("todos", 30 * 60)
                    )
                    self._smart_todo_manager.generate_todo_tasks(
                        start_time=start_time, end_time=end_time
                    )
                    self._last_generation_times["todos"] = datetime.now()
            except Exception as e:
                logger.exception(f"Failed to generate smart todo: {e}")

            self._schedule_next_check("todos", generate_todos)

        check_interval = self._calculate_check_interval("todos")
        self._task_timers["todos"] = threading.Timer(check_interval, generate_todos)
        self._task_timers["todos"].start()
        logger.info(
            f"Todos timer started, check interval: {check_interval}s, generation interval: {self._task_intervals['todos']}s"
        )

    def _calculate_check_interval(self, task_name: str) -> int:
        """Calculate check interval for a task (1/4 of generation interval with limits)"""
        interval = self._task_intervals.get(task_name, 900)
        limits = {"activity": 180, "tips": 200, "todos": 250}
        max_check = limits.get(task_name, 180)
        return min(max_check, interval // 4)

    def _schedule_next_check(self, task_name: str, callback) -> None:
        """Schedule next check for a task"""
        if self._scheduled_tasks_enabled and self._task_enabled.get(task_name, True):
            check_interval = self._calculate_check_interval(task_name)
            self._task_timers[task_name] = threading.Timer(check_interval, callback)
            self._task_timers[task_name].start()

    def get_scheduled_tasks_status(self) -> Dict[str, Any]:
        return {
            "enabled": self._scheduled_tasks_enabled,
            "daily_report_time": self._daily_report_time,
            "intervals": self._task_intervals.copy(),
            "active_timers": list(self._task_timers.keys()),
        }

    def get_task_config(self) -> Dict[str, Any]:
        """Get detailed task configuration"""
        with self._config_lock:
            return {
                "activity": {
                    "enabled": self._task_enabled.get("activity", True),
                    "interval": self._task_intervals.get("activity", 15 * 60),
                },
                "tips": {
                    "enabled": self._task_enabled.get("tips", True),
                    "interval": self._task_intervals.get("tips", 60 * 60),
                },
                "todos": {
                    "enabled": self._task_enabled.get("todos", True),
                    "interval": self._task_intervals.get("todos", 30 * 60),
                },
                "report": {
                    "enabled": self._task_enabled.get("report", True),
                    "time": self._daily_report_time,
                },
            }

    def update_task_config(self, config: Dict[str, Any]) -> bool:
        """
        Update task configuration dynamically
        """
        try:
            with self._config_lock:
                for task_name in ["activity", "tips", "todos"]:
                    if task_name in config:
                        self._update_interval_task(task_name, config[task_name])
                if "report" in config:
                    self._update_report_task(config["report"])

                return True
        except Exception as e:
            logger.exception(f"Failed to update task config: {e}")
            return False

    def _update_interval_task(self, task_name: str, task_cfg: Dict[str, Any]) -> None:
        """Update configuration for interval-based tasks (activity/tips/todos)"""
        need_restart = False

        if "enabled" in task_cfg:
            old_enabled = self._task_enabled.get(task_name, True)
            new_enabled = task_cfg["enabled"]
            self._task_enabled[task_name] = new_enabled

            if old_enabled != new_enabled:
                action = "Enabling" if new_enabled else "Disabling"
                logger.info(f"{action} {task_name} task")
                if new_enabled:
                    need_restart = True
                else:
                    self._stop_task_timer(task_name)
                    return

        # Update interval
        if "interval" in task_cfg:
            old_interval = self._task_intervals.get(task_name)
            new_interval = task_cfg["interval"]
            self._task_intervals[task_name] = new_interval

            if old_interval != new_interval and self._task_enabled.get(task_name, True):
                logger.info(f"Updating {task_name} interval to {new_interval}s")
                need_restart = True

        if need_restart:
            self._restart_task_timer(task_name)

    def _update_report_task(self, report_cfg: Dict[str, Any]) -> None:
        """Update configuration for report task"""
        need_restart = False

        # Update enabled status
        if "enabled" in report_cfg:
            old_enabled = self._task_enabled.get("report", True)
            new_enabled = report_cfg["enabled"]
            self._task_enabled["report"] = new_enabled

            if old_enabled != new_enabled:
                action = "Enabling" if new_enabled else "Disabling"
                logger.info(f"{action} report task")
                if new_enabled:
                    need_restart = True
                else:
                    self._stop_task_timer("report")
                    return  # Don't process time if disabling

        # Update time
        if "time" in report_cfg:
            old_time = self._daily_report_time
            new_time = report_cfg["time"]
            self._daily_report_time = new_time

            if old_time != new_time and self._task_enabled.get("report", True):
                logger.info(f"Updating report time to {new_time}")
                need_restart = True

        # Restart timer if needed
        if need_restart:
            self._restart_task_timer("report")

    def _stop_task_timer(self, task_name: str) -> None:
        """Stop a specific task timer"""
        if task_name in self._task_timers:
            timer = self._task_timers[task_name]
            if timer:
                timer.cancel()
            del self._task_timers[task_name]
            logger.info(f"Stopped {task_name} timer")

    def _restart_task_timer(self, task_name: str) -> None:
        """Restart a specific task timer"""
        if not self._scheduled_tasks_enabled:
            logger.warning(f"Cannot restart {task_name} timer: scheduled tasks not enabled")
            return

        # Stop existing timer
        self._stop_task_timer(task_name)

        # Start new timer based on task type
        if task_name == "activity":
            self._start_activity_timer()
        elif task_name == "tips":
            self._start_tips_timer()
        elif task_name == "todos":
            self._start_todos_timer()
        elif task_name == "report":
            self._start_report_timer()

        logger.info(f"Restarted {task_name} timer")

    def reset_statistics(self) -> None:
        """Reset statistics"""
        for consumer_name in self._statistics["consumers"]:
            self._statistics["consumers"][consumer_name] = {
                "queries": 0,
                "contexts_consumed": 0,
                "errors": 0,
            }

        self._statistics["total_queries"] = 0
        self._statistics["total_contexts_consumed"] = 0
        self._statistics["errors"] = 0