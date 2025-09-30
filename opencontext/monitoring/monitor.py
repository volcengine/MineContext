# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
系统监控器 - 收集和管理系统各种指标数据
"""

import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from opencontext.utils.logging_utils import get_logger
from opencontext.storage.global_storage import get_storage
from opencontext.models.enums import ContextType
from datetime import datetime, timedelta

logger = get_logger(__name__)


@dataclass
class TokenUsage:
    """Token使用统计"""
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ProcessingMetrics:
    """处理性能指标"""
    processor_name: str
    operation: str
    duration_ms: int
    context_type: Optional[str] = None
    context_count: int = 1
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class RetrievalMetrics:
    """检索性能指标"""
    operation: str
    duration_ms: int
    snippets_count: int = 0
    query: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ContextTypeStats:
    """上下文类型统计"""
    context_type: str
    count: int
    last_update: datetime = field(default_factory=datetime.now)


class Monitor:
    """系统监控器"""
    
    def __init__(self):
        self._lock = threading.RLock()
        self._storage = None
        
        # Token使用记录 (保留最近1000条)
        self._token_usage_history: deque = deque(maxlen=1000)
        self._token_usage_by_model: Dict[str, List[TokenUsage]] = defaultdict(list)
        
        # 处理性能记录 (保留最近1000条)
        self._processing_history: deque = deque(maxlen=1000)
        self._processing_by_type: Dict[str, List[ProcessingMetrics]] = defaultdict(list)
        
        # 检索性能记录 (保留最近1000条)
        self._retrieval_history: deque = deque(maxlen=1000)
        
        # 上下文类型统计缓存
        self._context_type_stats: Dict[str, ContextTypeStats] = {}
        self._stats_cache_ttl = 60  # 缓存60秒
        self._last_stats_update = datetime.min
        
        # 启动时间
        self._start_time = datetime.now()
        self._storage = get_storage()
        logger.info("System monitor initialized")
    
    def record_token_usage(self, model: str, prompt_tokens: int = 0, 
                          completion_tokens: int = 0, total_tokens: int = 0):
        """记录token使用"""
        with self._lock:
            usage = TokenUsage(
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens
            )
            self._token_usage_history.append(usage)
            self._token_usage_by_model[model].append(usage)
            
            # 限制每个模型的历史记录数量
            if len(self._token_usage_by_model[model]) > 100:
                self._token_usage_by_model[model] = self._token_usage_by_model[model][-100:]
    
    def record_processing_metrics(self, processor_name: str, operation: str, 
                                duration_ms: int, context_type: Optional[str] = None,
                                context_count: int = 1):
        """记录处理性能指标"""
        with self._lock:
            metrics = ProcessingMetrics(
                processor_name=processor_name,
                operation=operation,
                duration_ms=duration_ms,
                context_type=context_type,
                context_count=context_count
            )
            self._processing_history.append(metrics)
            key = f"{processor_name}:{operation}"
            self._processing_by_type[key].append(metrics)
            
            # 限制历史记录数量
            if len(self._processing_by_type[key]) > 100:
                self._processing_by_type[key] = self._processing_by_type[key][-100:]
    
    def record_retrieval_metrics(self, operation: str, duration_ms: int,
                               snippets_count: int = 0, query: Optional[str] = None):
        """记录检索性能指标"""
        with self._lock:
            metrics = RetrievalMetrics(
                operation=operation,
                duration_ms=duration_ms,
                snippets_count=snippets_count,
                query=query
            )
            self._retrieval_history.append(metrics)
    
    def get_context_type_stats(self, force_refresh: bool = False) -> Dict[str, int]:
        """获取各context_type的记录数量"""
        now = datetime.now()
        
        # 检查缓存是否过期
        if (not force_refresh and 
            now - self._last_stats_update < timedelta(seconds=self._stats_cache_ttl)):
            return {k: v.count for k, v in self._context_type_stats.items()}
        
        # 从存储获取最新统计
        if self._storage:
            try:
                with self._lock:
                    # 使用专门的计数方法，更高效
                    if hasattr(self._storage, 'get_all_processed_context_counts'):
                        stats = self._storage.get_all_processed_context_counts()
                    else:
                        # 降级到旧方法
                        stats = {}
                        for context_type in ContextType:
                            if hasattr(self._storage, 'get_processed_context_count'):
                                count = self._storage.get_processed_context_count(context_type.value)
                            else:
                                # 最后的降级：获取实际记录并计数
                                contexts = self._storage.get_all_processed_contexts(
                                    context_types=[context_type.value],
                                    limit=10000
                                )
                                count = 0
                                if isinstance(contexts, dict):
                                    count = sum(len(backend_contexts) if backend_contexts else 0 
                                              for backend_contexts in contexts.values())
                                elif isinstance(contexts, list):
                                    count = len(contexts)
                            
                            stats[context_type.value] = count
                    
                    # 更新缓存
                    for context_type_value, count in stats.items():
                        self._context_type_stats[context_type_value] = ContextTypeStats(
                            context_type=context_type_value,
                            count=count
                        )
                    
                    self._last_stats_update = now
                    logger.debug(f"刷新context_type统计: {stats}")
                    return stats
            except Exception as e:
                logger.error(f"获取context_type统计失败: {e}")
        
        # 返回缓存数据或空字典
        return {k: v.count for k, v in self._context_type_stats.items()}
    
    def get_token_usage_summary(self, hours: int = 24) -> Dict[str, Any]:
        """获取token使用摘要"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self._lock:
            recent_usage = [u for u in self._token_usage_history if u.timestamp >= cutoff_time]
            
            summary = {
                "total_records": len(recent_usage),
                "by_model": {},
                "total_tokens": 0,
                "total_prompt_tokens": 0,
                "total_completion_tokens": 0
            }
            
            model_stats = defaultdict(lambda: {"count": 0, "total_tokens": 0, 
                                             "prompt_tokens": 0, "completion_tokens": 0})
            
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
        """获取处理性能摘要"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self._lock:
            recent_metrics = [m for m in self._processing_history if m.timestamp >= cutoff_time]
            
            summary = {
                "total_operations": len(recent_metrics),
                "by_processor": {},
                "by_context_type": {},
                "avg_duration_ms": 0,
                "total_contexts_processed": 0
            }
            
            if not recent_metrics:
                return summary
            
            processor_stats = defaultdict(lambda: {"count": 0, "total_duration": 0, 
                                                 "avg_duration": 0, "contexts": 0})
            context_stats = defaultdict(lambda: {"count": 0, "total_duration": 0, 
                                               "avg_duration": 0})
            
            total_duration = 0
            total_contexts = 0
            
            for metrics in recent_metrics:
                # 按处理器统计
                key = f"{metrics.processor_name}:{metrics.operation}"
                processor_stats[key]["count"] += 1
                processor_stats[key]["total_duration"] += metrics.duration_ms
                processor_stats[key]["contexts"] += metrics.context_count
                
                # 按上下文类型统计
                if metrics.context_type:
                    context_stats[metrics.context_type]["count"] += 1
                    context_stats[metrics.context_type]["total_duration"] += metrics.duration_ms
                
                total_duration += metrics.duration_ms
                total_contexts += metrics.context_count
            
            # 计算平均值
            for stats in processor_stats.values():
                if stats["count"] > 0:
                    stats["avg_duration"] = stats["total_duration"] / stats["count"]
            
            for stats in context_stats.values():
                if stats["count"] > 0:
                    stats["avg_duration"] = stats["total_duration"] / stats["count"]
            
            summary["by_processor"] = dict(processor_stats)
            summary["by_context_type"] = dict(context_stats)
            summary["avg_duration_ms"] = total_duration / len(recent_metrics) if recent_metrics else 0
            summary["total_contexts_processed"] = total_contexts
            
            return summary
    
    def get_todo_stats(self, hours: int = 24) -> Dict[str, Any]:
        """获取TODO任务统计"""
        try:
            if self._storage:
                end_time = datetime.now()
                start_time = end_time - timedelta(hours=hours)
                
                # 获取所有TODO
                todos = self._storage.get_todos(start_time=start_time, end_time=end_time)
                
                completed = 0
                pending = 0
                
                for todo in todos:
                    if todo.get('status', 0) == 1:  # 1表示已完成
                        completed += 1
                    else:
                        pending += 1
                
                return {
                    "total": len(todos),
                    "completed": completed,
                    "pending": pending,
                    "time_range_hours": hours
                }
        except Exception as e:
            logger.error(f"获取TODO统计失败: {e}")
        
        return {"total": 0, "completed": 0, "pending": 0, "time_range_hours": hours}
    
    def get_tips_count(self, hours: int = 24) -> Dict[str, Any]:
        """获取Tips提示数量"""
        try:
            if self._storage:
                end_time = datetime.now()
                start_time = end_time - timedelta(hours=hours)
                
                tips = self._storage.get_tips(start_time=start_time, end_time=end_time)
                
                return {
                    "total": len(tips),
                    "time_range_hours": hours
                }
        except Exception as e:
            logger.error(f"获取Tips数量失败: {e}")
        
        return {"total": 0, "time_range_hours": hours}
    
    def get_activity_count(self, hours: int = 24) -> Dict[str, Any]:
        """获取活动记录数量"""
        try:
            if self._storage:
                end_time = datetime.now()
                start_time = end_time - timedelta(hours=hours)
                
                activities = self._storage.get_activities(start_time=start_time, end_time=end_time)
                
                return {
                    "total": len(activities),
                    "time_range_hours": hours
                }
        except Exception as e:
            logger.error(f"获取活动数量失败: {e}")
        
        return {"total": 0, "time_range_hours": hours}
    
    def get_retrieval_summary(self, hours: int = 24) -> Dict[str, Any]:
        """获取检索性能摘要"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self._lock:
            recent_metrics = [m for m in self._retrieval_history if m.timestamp >= cutoff_time]
            
            summary = {
                "total_operations": len(recent_metrics),
                "by_operation": {},
                "avg_duration_ms": 0,
                "total_snippets": 0,
                "avg_snippets_per_query": 0
            }
            
            if not recent_metrics:
                return summary
            
            operation_stats = defaultdict(lambda: {"count": 0, "total_duration": 0, 
                                                 "avg_duration": 0, "snippets": 0})
            
            total_duration = 0
            total_snippets = 0
            
            for metrics in recent_metrics:
                operation_stats[metrics.operation]["count"] += 1
                operation_stats[metrics.operation]["total_duration"] += metrics.duration_ms
                operation_stats[metrics.operation]["snippets"] += metrics.snippets_count
                
                total_duration += metrics.duration_ms
                total_snippets += metrics.snippets_count
            
            # 计算平均值
            for stats in operation_stats.values():
                if stats["count"] > 0:
                    stats["avg_duration"] = stats["total_duration"] / stats["count"]
            
            summary["by_operation"] = dict(operation_stats)
            summary["avg_duration_ms"] = total_duration / len(recent_metrics) if recent_metrics else 0
            summary["total_snippets"] = total_snippets
            summary["avg_snippets_per_query"] = total_snippets / len(recent_metrics) if recent_metrics else 0
            
            return summary
    
    def get_system_overview(self) -> Dict[str, Any]:
        """获取系统概览"""
        uptime = datetime.now() - self._start_time
        
        return {
            "uptime_seconds": int(uptime.total_seconds()),
            "uptime_formatted": str(uptime).split('.')[0],
            "context_types": self.get_context_type_stats(),
            "token_usage": self.get_token_usage_summary(hours=24),
            "processing": self.get_processing_summary(hours=24),
            "todo_stats": self.get_todo_stats(hours=24),
            "tips_count": self.get_tips_count(hours=24),
            "activity_count": self.get_activity_count(hours=24),
            "last_updated": datetime.now().isoformat()
        }


# 全局监控器实例
_monitor: Optional[Monitor] = None
_monitor_lock = threading.Lock()


def get_monitor() -> Monitor:
    """获取全局监控器实例"""
    global _monitor
    if _monitor is None:
        with _monitor_lock:
            if _monitor is None:
                _monitor = Monitor()
    return _monitor


def initialize_monitor() -> Monitor:
    """初始化监控器"""
    monitor = get_monitor()
    return monitor


# 便捷的全局函数，直接上报指标
def record_token_usage(model: str, prompt_tokens: int = 0, 
                      completion_tokens: int = 0, total_tokens: int = 0):
    """全局函数：记录token使用"""
    get_monitor().record_token_usage(model, prompt_tokens, completion_tokens, total_tokens)


def record_processing_metrics(processor_name: str, operation: str, 
                            duration_ms: int, context_type: Optional[str] = None,
                            context_count: int = 1):
    """全局函数：记录处理性能指标"""
    get_monitor().record_processing_metrics(processor_name, operation, duration_ms, context_type, context_count)


def record_retrieval_metrics(operation: str, duration_ms: int,
                           snippets_count: int = 0, query: Optional[str] = None):
    """全局函数：记录检索性能指标"""
    get_monitor().record_retrieval_metrics(operation, duration_ms, snippets_count, query)