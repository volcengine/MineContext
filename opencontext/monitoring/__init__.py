# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
监控模块 - 提供系统性能和使用情况的监控功能
"""

from .metrics_collector import MetricsCollector
from .monitor import (
    Monitor,
    get_monitor,
    increment_context_count,
    increment_data_count,
    increment_screenshot_count,
    initialize_monitor,
    record_processing_error,
    record_processing_metrics,
    record_processing_stage,
    record_retrieval_metrics,
    record_token_usage,
)

__all__ = [
    "Monitor",
    "get_monitor",
    "initialize_monitor",
    "record_token_usage",
    "record_processing_metrics",
    "record_retrieval_metrics",
    "record_processing_error",
    "record_processing_stage",
    "increment_screenshot_count",
    "increment_context_count",
    "increment_data_count",
    "MetricsCollector",
]
