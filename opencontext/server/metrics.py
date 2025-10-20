# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Prometheus metrics registry and metric definitions for OpenContext API and pipeline.
"""

import os
from typing import Optional

from prometheus_client import Counter, Gauge, Histogram
from prometheus_client import CollectorRegistry, CONTENT_TYPE_LATEST, generate_latest
from prometheus_client import multiprocess

# Registry helper


def get_prometheus_registry() -> CollectorRegistry:
    registry = CollectorRegistry()
    if os.environ.get("PROMETHEUS_MULTIPROC_DIR"):
        multiprocess.MultiProcessCollector(registry)
    return registry


# Metric definitions (module-level singletons)
HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests",
    labelnames=("method", "path", "status_code"),
)

HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    labelnames=("method", "path", "status_code"),
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10),
)

PIPELINE_STAGE_DURATION = Histogram(
    "pipeline_stage_duration_seconds",
    "Pipeline stage processing duration in seconds",
    labelnames=("processor", "operation", "context_type"),
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 30),
)

PIPELINE_PROCESSED_TOTAL = Counter(
    "pipeline_processed_total",
    "Total number of processed items by pipeline stage",
    labelnames=("processor", "operation"),
)

PROCESSOR_QUEUE_SIZE = Gauge(
    "processor_queue_size",
    "Size of processor internal work queues",
    labelnames=("processor",),
)


def render_latest_metrics() -> tuple[bytes, str]:
    registry = get_prometheus_registry()
    output = generate_latest(registry)
    return output, CONTENT_TYPE_LATEST
