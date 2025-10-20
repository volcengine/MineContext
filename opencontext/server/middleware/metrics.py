# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Request metrics middleware
Collects request counters and latency histograms for Prometheus.
"""

import time
from typing import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from opencontext.server.metrics import HTTP_REQUESTS_TOTAL, HTTP_REQUEST_DURATION


def _get_route_template(request: Request) -> str:
    try:
        route = request.scope.get("route")
        if route and getattr(route, "path", None):
            return route.path
    except Exception:
        pass
    # Fallback to raw path, but avoid cardinality explosion
    # by collapsing dynamic segments if any
    return request.url.path


class RequestMetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        start = time.perf_counter()
        method = request.method
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration = time.perf_counter() - start
            path = _get_route_template(request)
            # Limit label cardinality: only template path and coarse status code
            status_label = str(getattr(locals().get("response", None), "status_code", 500))
            HTTP_REQUESTS_TOTAL.labels(method=method, path=path, status_code=status_label).inc()
            HTTP_REQUEST_DURATION.labels(method=method, path=path, status_code=status_label).observe(duration)
