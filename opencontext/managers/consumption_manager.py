#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0


"""
Context consumption manager, responsible for managing and coordinating context consumption components
"""

from typing import Any, Dict, List, Optional
import asyncio
import threading
from datetime import datetime, timedelta
from opencontext.context_consumption.generation.generation_report import ReportGenerator
from opencontext.context_consumption.generation.realtime_activity_monitor import RealtimeActivityMonitor
from opencontext.context_consumption.generation.smart_tip_generator import SmartTipGenerator
from opencontext.context_consumption.generation.smart_todo_manager import SmartTodoManager
from opencontext.storage.global_storage import get_storage
from opencontext.managers.event_manager import get_event_manager, EventType
from opencontext.models.enums import VaultType
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
        
        # Scheduled task configuration
        self._scheduled_tasks_enabled = False
        self._task_timers: Dict[str, threading.Timer] = {}
        self._task_intervals = {
            'activity': 15 * 60,
            'tips': 60 * 60,
            'todos': 30 * 60,
        }
        
        # Maintain local last successful generation time
        self._last_generation_times = {
            'activity': None,
            'tips': None,
            'todos': None,
        }
        
        self._daily_report_time = "08:00"
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
        """Check if specified task type should be generated
        """
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
            if 'daily_report_time' in config:
                self._daily_report_time = config['daily_report_time']
            if 'activity_interval' in config:
                self._task_intervals['activity'] = config['activity_interval'] 
            if 'tips_interval' in config:
                self._task_intervals['tips'] = config['tips_interval']
            if 'todos_interval' in config:
                self._task_intervals['todos'] = config['todos_interval']
        
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
            hour, minute = map(int, target_time_str.split(':'))
            now = datetime.now().astimezone()
            target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            if target <= now:
                target += timedelta(days=1)
            return (target - now).total_seconds()
        except Exception as e:
            logger.error(f"Failed to parse daily report time configuration: {e}, using default 24 hours")
            return 24 * 60 * 60
    
    def _get_last_report_time(self) -> datetime:
        """Get last daily report generation time from database, return current time if none"""
        try:
            reports = get_storage().get_vaults(
                document_type=VaultType.DAILY_REPORT.value, 
                limit=1, 
                offset=0,
                is_deleted=False
            )
            if reports:
                created_at_str = reports[0]['created_at']
                if created_at_str:
                    return datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
            return datetime.now()
        except Exception as e:
            return datetime.now()
    
    def _start_report_timer(self):
        # Get last daily report time from database
        last_report_time = self._get_last_report_time()
        self._last_report_date = last_report_time.date()  # Record date of last daily report generation
        
        def check_and_generate_daily_report():
            if not self._activity_generator:
                return
            try:
                now = datetime.now()
                today = now.date()

                hour, minute = map(int, self._daily_report_time.split(':'))
                target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

                if now >= target_time and self._last_report_date != today:
                    try:
                        end_time = int(now.timestamp())
                        start_time = int((now - timedelta(days=1)).timestamp())

                        report_content = asyncio.run(self._activity_generator.generate_report(start_time, end_time))
                        # Update last report date to prevent duplicate generation on the same day
                        self._last_report_date = today
                    except Exception as e:
                        logger.exception(f"Failed to generate daily report: {e}")
            except Exception as e:
                logger.error(f"Failed to check daily report generation time: {e}")
            
            if self._scheduled_tasks_enabled:
                self._task_timers['report'] = threading.Timer(60*30, check_and_generate_daily_report)
                self._task_timers['report'].start()
        
        check_and_generate_daily_report()
    
    def _start_activity_timer(self):
        """Start activity recording timer"""
        def generate_activity():
            if self._scheduled_tasks_enabled and self._real_activity_monitor:
                try:
                    # Check if generation time has arrived
                    if self._should_generate('activity'):
                        end_time = int(datetime.now().timestamp())
                        last_generation_time = self._last_generation_time('activity')
                        start_time = last_generation_time.timestamp() if last_generation_time else end_time - self._task_intervals.get('activity', 15*60)
                        result = self._real_activity_monitor.generate_realtime_activity_summary(start_time, end_time)
                        if result:
                            logger.info(f"Activity record generated, ID: {result.get('doc_id')}")
                            # Update last successful generation time
                            self._last_generation_times['activity'] = datetime.now()
                except Exception as e:
                    logger.exception(f"Failed to generate activity record: {e}")
                
                if self._scheduled_tasks_enabled:
                    check_interval = min(180, self._task_intervals['activity'] // 4)  # 3 minutes or 1/4 of interval
                    self._task_timers['activity'] = threading.Timer(
                        check_interval, generate_activity
                    )
                    self._task_timers['activity'].start()

        check_interval = min(180, self._task_intervals['activity'] // 4)
        self._task_timers['activity'] = threading.Timer(
            check_interval, generate_activity
        )
        self._task_timers['activity'].start()
        logger.info(f"Activity recording timer started, check interval: {check_interval} seconds, generation interval: {self._task_intervals['activity']} seconds")
    
    def _start_tips_timer(self):
        """Start smart tips timer"""
        def generate_tips():
            if self._scheduled_tasks_enabled and self._smart_tip_generator:
                try:
                    if self._should_generate('tips'):
                        end_time = int(datetime.now().timestamp())
                        last_generation_time = self._last_generation_time('tips')
                        start_time = last_generation_time.timestamp() if last_generation_time else end_time - self._task_intervals.get('tips', 60*60)
                        result = self._smart_tip_generator.generate_smart_tip(start_time, end_time)
                        if result:
                            logger.info(f"Smart tip generated, ID: {result.get('doc_id')}")
                            # Update last successful generation time
                            self._last_generation_times['tips'] = datetime.now()
                    else:
                        logger.debug("Not time for smart tip generation, skipping")
                except Exception as e:
                    logger.exception(f"Failed to generate smart tip: {e}")
                
                if self._scheduled_tasks_enabled:
                    # Use shorter check interval instead of generation interval
                    check_interval = min(200, self._task_intervals['tips'] // 4)  # 3.3 minutes or 1/4 of interval
                    self._task_timers['tips'] = threading.Timer(
                        check_interval, generate_tips
                    )
                    self._task_timers['tips'].start()
        
        # Initial startup also uses check interval
        check_interval = min(200, self._task_intervals['tips'] // 4)
        self._task_timers['tips'] = threading.Timer(
            check_interval, generate_tips
        )
        self._task_timers['tips'].start()
        logger.info(f"Smart tip timer started, check interval: {check_interval} seconds, generation interval: {self._task_intervals['tips']} seconds")
    
    def _start_todos_timer(self):
        """Start smart todo timer"""
        def generate_todos():
            if self._scheduled_tasks_enabled and self._smart_todo_manager:
                try:
                    # Check if generation time has arrived
                    if self._should_generate('todos'):
                        end_time = int(datetime.now().timestamp())
                        last_generation_time = self._last_generation_time('todos')
                        start_time = last_generation_time.timestamp() if last_generation_time else end_time - self._task_intervals.get('todos', 30*60)
                        result = self._smart_todo_manager.generate_todo_tasks(
                            start_time=start_time, end_time=end_time
                        )
                        if result:
                            logger.info(f"Smart todo generated, ID: {result.get('doc_id')}")
                            # Update last successful generation time
                            self._last_generation_times['todos'] = datetime.now()
                    else:
                        logger.debug("Not time for smart todo generation, skipping")
                except Exception as e:
                    logger.exception(f"Failed to generate smart todo: {e}")
                
                if self._scheduled_tasks_enabled:
                    # Use shorter check interval instead of generation interval
                    check_interval = min(250, self._task_intervals['todos'] // 4)  # 4.2 minutes or 1/4 of interval
                    self._task_timers['todos'] = threading.Timer(
                        check_interval, generate_todos
                    )
                    self._task_timers['todos'].start()
        
        # Initial startup also uses check interval
        check_interval = min(250, self._task_intervals['todos'] // 4)
        self._task_timers['todos'] = threading.Timer(
            check_interval, generate_todos
        )
        self._task_timers['todos'].start()
        logger.info(f"Smart todo timer started, check interval: {check_interval} seconds, generation interval: {self._task_intervals['todos']} seconds")

    def get_scheduled_tasks_status(self) -> Dict[str, Any]:
        return {
            "enabled": self._scheduled_tasks_enabled,
            "daily_report_time": self._daily_report_time,
            "intervals": self._task_intervals.copy(),
            "active_timers": list(self._task_timers.keys())
        }
    
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
    
    def generate_report(self, start_time: int, end_time: int) -> str:
        """Generate activity report
        
        Args:
            start_time: Start timestamp
            end_time: End timestamp
            
        Returns:
            str: Generated report content
        """
        if self._activity_generator is None:
            logger.error("ActivityGenerator not initialized, unable to generate activity report")
            return ""
        
        try:
            report = self._activity_generator.generate_report(start_time, end_time)
            
            # Update statistics
            self._statistics["total_queries"] += 1
            return report
            
        except Exception as e:
            self._statistics["errors"] += 1
            logger.exception(f"Error occurred while generating activity report: {e}")
            return ""