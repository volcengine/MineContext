# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Server component: monitoring routes - Monitoring API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from datetime import datetime
from opencontext.server.utils import get_context_lab
from opencontext.server.opencontext import OpenContext
from opencontext.monitoring import get_monitor
from opencontext.server.middleware.auth import auth_dependency
from datetime import timedelta

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


@router.get("/overview")
async def get_system_overview(
    opencontext: OpenContext = Depends(get_context_lab),
    _auth: str = auth_dependency
):
    """
    Get system monitoring overview
    """
    try:
        monitor = get_monitor()
        overview = monitor.get_system_overview()
        return {"success": True, "data": overview}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get system overview: {str(e)}")


@router.get("/context-types")
async def get_context_type_stats(
    force_refresh: bool = Query(False, description="Whether to force refresh cache"),
    opencontext: OpenContext = Depends(get_context_lab),
    _auth: str = auth_dependency
):
    """
    Get candidate count statistics for each context_type
    """
    try:
        monitor = get_monitor()
        stats = monitor.get_context_type_stats(force_refresh=force_refresh)
        return {"success": True, "data": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get context type statistics: {str(e)}")


@router.get("/token-usage")
async def get_token_usage_summary(
    hours: int = Query(24, ge=1, le=168, description="Statistics time range (hours)"),
    _auth: str = auth_dependency
):
    """
    Get model token consumption details
    """
    try:
        monitor = get_monitor()
        summary = monitor.get_token_usage_summary(hours=hours)
        return {"success": True, "data": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get token usage statistics: {str(e)}")


@router.get("/processing")
async def get_processing_metrics(
    hours: int = Query(24, ge=1, le=168, description="Statistics time range (hours)"),
    _auth: str = auth_dependency
):
    """
    Get processor performance metrics
    """
    try:
        monitor = get_monitor()
        metrics = monitor.get_processing_summary(hours=hours)
        return {"success": True, "data": metrics}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get processing performance metrics: {str(e)}")


@router.get("/todo-stats")
async def get_todo_stats(
    hours: int = Query(24, ge=1, le=168, description="Statistics time range (hours)"),
    opencontext: OpenContext = Depends(get_context_lab),
    _auth: str = auth_dependency
):
    """
    Get TODO task statistics
    """
    try:
        monitor = get_monitor()
        stats = monitor.get_todo_stats(hours=hours)
        return {"success": True, "data": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get TODO statistics: {str(e)}")


@router.get("/tips-count")
async def get_tips_count(
    hours: int = Query(24, ge=1, le=168, description="Statistics time range (hours)"),
    opencontext: OpenContext = Depends(get_context_lab),
    _auth: str = auth_dependency
):
    """
    Get Tips count
    """
    try:
        monitor = get_monitor()
        count = monitor.get_tips_count(hours=hours)
        return {"success": True, "data": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get Tips count: {str(e)}")


@router.get("/activity-count")
async def get_activity_count(
    hours: int = Query(24, ge=1, le=168, description="Statistics time range (hours)"),
    opencontext: OpenContext = Depends(get_context_lab),
    _auth: str = auth_dependency
):
    """
    Get activity record count
    """
    try:
        monitor = get_monitor()
        count = monitor.get_activity_count(hours=hours)
        return {"success": True, "data": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get activity count: {str(e)}")


@router.post("/refresh-context-stats")
async def refresh_context_type_stats(
    opencontext: OpenContext = Depends(get_context_lab),
    _auth: str = auth_dependency
):
    """
    Refresh context type statistics cache
    """
    try:
        monitor = get_monitor()
        stats = monitor.get_context_type_stats(force_refresh=True)
        return {"success": True, "data": stats, "message": "Statistics data refreshed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to refresh statistics data: {str(e)}")


@router.get("/health")
async def monitoring_health(
    _auth: str = auth_dependency
):
    """
    Monitoring system health check
    """
    try:
        monitor = get_monitor()
        uptime_seconds = int((datetime.now() - monitor._start_time).total_seconds()) if monitor._start_time else 0
        return {
            "success": True,
            "data": {
                "monitor_active": True,
                "uptime_seconds": uptime_seconds
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}