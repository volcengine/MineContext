# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Metrics endpoint exposing Prometheus metrics in text format.
"""

from fastapi import APIRouter, Depends, Request, Response

from opencontext.server.metrics import PROCESSOR_QUEUE_SIZE, render_latest_metrics
from opencontext.server.middleware.auth import auth_dependency

router = APIRouter(tags=["monitoring"])


@router.get("/metrics", summary="Prometheus metrics endpoint")
async def prometheus_metrics(request: Request, _auth: str = auth_dependency):
    # Best-effort queue size gauges (avoid importing heavy modules in hot path)
    try:
        ctx = getattr(request.app.state, "context_lab_instance", None)
        if ctx and ctx.processor_manager:
            for name, proc in ctx.processor_manager.get_all_processors().items():
                qsize = getattr(proc, "_input_queue", None)
                size = qsize.qsize() if qsize is not None else 0
                PROCESSOR_QUEUE_SIZE.labels(processor=name).set(size)
    except Exception:
        pass

    body, content_type = render_latest_metrics()
    return Response(content=body, media_type=content_type)
