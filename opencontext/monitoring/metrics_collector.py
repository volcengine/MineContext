# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
指标收集器 - 提供装饰器和工具来自动收集性能指标
"""

import functools
import time
from typing import Any, Callable, Optional

from opencontext.utils.logging_utils import get_logger

from .monitor import get_monitor

logger = get_logger(__name__)


class MetricsCollector:
    """指标收集器工具类"""

    @staticmethod
    def timing_decorator(processor_name: str, operation: str, context_type: Optional[str] = None):
        """
        时间测量装饰器

        Args:
            processor_name: 处理器名称
            operation: 操作名称
            context_type: 上下文类型
        """

        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    duration_ms = int((time.time() - start_time) * 1000)
                    monitor = get_monitor()

                    # 尝试从结果中获取上下文数量
                    context_count = 1
                    if hasattr(result, "__len__") and not isinstance(result, str):
                        try:
                            context_count = len(result)
                        except:
                            context_count = 1

                    monitor.record_processing_metrics(
                        processor_name=processor_name,
                        operation=operation,
                        duration_ms=duration_ms,
                        context_type=context_type,
                        context_count=context_count,
                    )

                    logger.debug(f"{processor_name}:{operation} completed in {duration_ms}ms")

            return wrapper

        return decorator

    @staticmethod
    def retrieval_timing_decorator(operation: str):
        """
        检索时间测量装饰器

        Args:
            operation: 检索操作名称
        """

        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    duration_ms = int((time.time() - start_time) * 1000)
                    monitor = get_monitor()

                    # 尝试从结果中获取snippets数量
                    snippets_count = 0
                    query = None

                    if hasattr(result, "top_snippets"):
                        snippets_count = len(result.top_snippets)
                    elif hasattr(result, "__len__") and not isinstance(result, str):
                        try:
                            snippets_count = len(result)
                        except:
                            snippets_count = 0

                    # 尝试从参数中获取query
                    if "query" in kwargs:
                        query = kwargs["query"]
                    elif args and isinstance(args[0], str):
                        query = args[0]

                    monitor.record_retrieval_metrics(
                        operation=operation,
                        duration_ms=duration_ms,
                        snippets_count=snippets_count,
                        query=query,
                    )

                    logger.debug(
                        f"Retrieval {operation} completed in {duration_ms}ms, {snippets_count} snippets"
                    )

            return wrapper

        return decorator

    @staticmethod
    def manual_timing_context(
        processor_name: str, operation: str, context_type: Optional[str] = None
    ):
        """
        手动时间测量上下文管理器

        Args:
            processor_name: 处理器名称
            operation: 操作名称
            context_type: 上下文类型
        """
        return TimingContext(processor_name, operation, context_type)

    @staticmethod
    def manual_retrieval_timing_context(operation: str):
        """
        手动检索时间测量上下文管理器

        Args:
            operation: 检索操作名称
        """
        return RetrievalTimingContext(operation)


class TimingContext:
    """处理时间测量上下文管理器"""

    def __init__(self, processor_name: str, operation: str, context_type: Optional[str] = None):
        self.processor_name = processor_name
        self.operation = operation
        self.context_type = context_type
        self.start_time = None
        self.context_count = 1

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration_ms = int((time.time() - self.start_time) * 1000)
            monitor = get_monitor()
            monitor.record_processing_metrics(
                processor_name=self.processor_name,
                operation=self.operation,
                duration_ms=duration_ms,
                context_type=self.context_type,
                context_count=self.context_count,
            )

    def set_context_count(self, count: int):
        """设置处理的上下文数量"""
        self.context_count = count


class RetrievalTimingContext:
    """检索时间测量上下文管理器"""

    def __init__(self, operation: str):
        self.operation = operation
        self.start_time = None
        self.snippets_count = 0
        self.query = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration_ms = int((time.time() - self.start_time) * 1000)
            monitor = get_monitor()
            monitor.record_retrieval_metrics(
                operation=self.operation,
                duration_ms=duration_ms,
                snippets_count=self.snippets_count,
                query=self.query,
            )

    def set_snippets_count(self, count: int):
        """设置检索到的snippets数量"""
        self.snippets_count = count

    def set_query(self, query: str):
        """设置查询字符串"""
        self.query = query
