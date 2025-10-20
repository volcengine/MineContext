# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Health check routes
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy import text

from opencontext import __version__ as oc_version
from opencontext.db import get_engine
from opencontext.server.middleware.auth import auth_dependency, is_auth_enabled
from opencontext.server.opencontext import OpenContext
from opencontext.server.utils import convert_resp, get_context_lab
from opencontext.storage.global_storage import get_storage

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return convert_resp(data={"status": "healthy", "service": "opencontext"})


@router.get("/api/health")
async def api_health_check(opencontext: OpenContext = Depends(get_context_lab)):
    """Detailed health check with service status"""
    try:
        health_data = {
            "status": "healthy",
            "service": "opencontext",
            "components": opencontext.check_components_health(),
        }
        return convert_resp(data=health_data)
    except Exception as e:
        from opencontext.utils.logging_utils import get_logger

        logger = get_logger(__name__)
        logger.exception(f"Health check failed: {e}")
        return convert_resp(code=503, status=503, message="Service unhealthy")


@router.get("/api/auth/status")
async def auth_status():
    """Check if API authentication is enabled"""
    return convert_resp(data={"auth_enabled": is_auth_enabled()})


@router.get("/healthz", summary="Operational health endpoint")
async def healthz(request: Request, _auth: str = auth_dependency):
    overall_ok = True
    components = {}

    # Build/version info
    build = {
        "version": oc_version,
    }
    try:
        import os

        if os.environ.get("GIT_SHA"):
            build["git_sha"] = os.environ.get("GIT_SHA")
        if os.environ.get("BUILD_TIMESTAMP"):
            build["build_time"] = os.environ.get("BUILD_TIMESTAMP")
    except Exception:
        pass

    # Database connectivity
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        components["database"] = {"status": "ok"}
    except Exception as e:
        overall_ok = False
        components["database"] = {"status": "error", "error": str(e)}

    # Vector store (Chroma) reachability
    try:
        storage = get_storage()
        if storage is None:
            components["vector_store"] = {"status": "unconfigured"}
        else:
            counts = storage.get_all_processed_context_counts()
            # If the call succeeded, backend is reachable
            total = sum(counts.values()) if counts else 0
            components["vector_store"] = {"status": "ok", "total_contexts": total}
    except Exception as e:
        overall_ok = False
        components["vector_store"] = {"status": "error", "error": str(e)}

    # Background workers liveness (best-effort)
    try:
        ctx = getattr(request.app.state, "context_lab_instance", None)
        workers_ok = True
        details = {}
        if ctx and getattr(ctx, "processor_manager", None):
            for name, proc in ctx.processor_manager.get_all_processors().items():
                alive = getattr(proc, "_processing_task", None)
                if alive is not None:
                    running = bool(getattr(alive, "is_alive", lambda: False)())
                    details[name] = {"thread_alive": running}
                    workers_ok = workers_ok and running
        if ctx and getattr(ctx, "consumption_manager", None):
            status = ctx.consumption_manager.get_scheduled_tasks_status()
            details["scheduled_tasks"] = status
        components["workers"] = {"status": "ok" if workers_ok else "degraded", "details": details}
        if not workers_ok:
            overall_ok = False
    except Exception as e:
        components["workers"] = {"status": "unknown", "error": str(e)}

    status = "ok" if overall_ok else "error"
    return convert_resp(
        data={
            "status": status,
            "service": "opencontext",
            "build": build,
            "components": components,
        },
        status=200 if overall_ok else 503,
        code=0 if overall_ok else 1,
        message="healthy" if overall_ok else "unhealthy",
    )
