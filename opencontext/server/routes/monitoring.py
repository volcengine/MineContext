# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Server component: monitoring routes - Monitoring API endpoints
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from opencontext.monitoring import get_monitor
from opencontext.server.middleware.auth import auth_dependency
from opencontext.server.opencontext import OpenContext
from opencontext.server.utils import get_context_lab

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


@router.get("/overview")
async def get_system_overview(
    opencontext: OpenContext = Depends(get_context_lab), _auth: str = auth_dependency
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
    _auth: str = auth_dependency,
):
    """
    Get candidate count statistics for each context_type
    """
    try:
        monitor = get_monitor()
        stats = monitor.get_context_type_stats(force_refresh=force_refresh)
        return {"success": True, "data": stats}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get context type statistics: {str(e)}"
        )


@router.get("/token-usage")
async def get_token_usage_summary(
    hours: int = Query(24, ge=1, le=168, description="Statistics time range (hours)"),
    _auth: str = auth_dependency,
):
    """
    Get model token consumption details
    """
    try:
        monitor = get_monitor()
        summary = monitor.get_token_usage_summary(hours=hours)
        return {"success": True, "data": summary}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get token usage statistics: {str(e)}"
        )


@router.get("/processing")
async def get_processing_metrics(
    hours: int = Query(24, ge=1, le=168, description="Statistics time range (hours)"),
    _auth: str = auth_dependency,
):
    """
    Get processor performance metrics
    """
    try:
        monitor = get_monitor()
        metrics = monitor.get_processing_summary(hours=hours)
        return {"success": True, "data": metrics}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get processing performance metrics: {str(e)}"
        )


@router.get("/stage-timing")
async def get_stage_timing_metrics(
    hours: int = Query(24, ge=1, le=168, description="Statistics time range (hours)"),
    _auth: str = auth_dependency,
):
    """
    Get stage timing metrics (LLM API calls and processing stages)
    """
    try:
        monitor = get_monitor()
        metrics = monitor.get_stage_timing_summary(hours=hours)
        return {"success": True, "data": metrics}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stage timing metrics: {str(e)}")


@router.get("/data-stats")
async def get_data_stats(
    hours: int = Query(24, ge=1, le=168, description="Statistics time range (hours)"),
    _auth: str = auth_dependency,
):
    """
    Get data statistics (screenshots, documents, contexts)
    """
    try:
        monitor = get_monitor()
        stats = monitor.get_data_stats_summary(hours=hours)
        return {"success": True, "data": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get data statistics: {str(e)}")


@router.get("/data-stats-trend")
async def get_data_stats_trend(
    hours: int = Query(24, ge=1, le=168, description="Statistics time range (hours)"),
    _auth: str = auth_dependency,
):
    """
    Get data statistics trend with time series (screenshots, documents, contexts over time)
    """
    try:
        monitor = get_monitor()
        trend = monitor.get_data_stats_trend(hours=hours)
        return {"success": True, "data": trend}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get data statistics trend: {str(e)}"
        )


@router.get("/data-stats-range")
async def get_data_stats_by_range(
    start_time: datetime = Query(..., description="Start time of the query range (ISO format)"),
    end_time: datetime = Query(..., description="End time of the query range (ISO format)"),
    _auth: str = auth_dependency,
):
    """
    Get data statistics by custom time range (screenshots, documents, contexts)
    """
    try:
        # Validate time range
        if start_time >= end_time:
            raise HTTPException(
                status_code=400, detail="start_time must be earlier than end_time"
            )

        monitor = get_monitor()
        stats = monitor.get_data_stats_by_range(start_time=start_time, end_time=end_time)
        return {"success": True, "data": stats}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get data statistics by range: {str(e)}"
        )


@router.post("/refresh-context-stats")
async def refresh_context_type_stats(
    opencontext: OpenContext = Depends(get_context_lab), _auth: str = auth_dependency
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
async def monitoring_health(_auth: str = auth_dependency):
    """
    Monitoring system health check
    """
    try:
        monitor = get_monitor()
        uptime_seconds = (
            int((datetime.now() - monitor._start_time).total_seconds())
            if monitor._start_time
            else 0
        )
        return {"success": True, "data": {"monitor_active": True, "uptime_seconds": uptime_seconds}}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/processing-errors")
async def get_processing_errors(
    hours: int = Query(1, ge=1, le=24, description="Statistics time range (hours)"),
    top: int = Query(5, ge=1, le=20, description="Number of top errors to return"),
    _auth: str = auth_dependency,
):
    """
    Get processing errors Top N
    """
    try:
        monitor = get_monitor()
        errors = monitor.get_processing_errors(hours=hours, top_n=top)
        return {"success": True, "data": errors}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get processing errors: {str(e)}")


@router.get("/recording-stats")
async def get_recording_stats(_auth: str = auth_dependency):
    """
    Get current recording session statistics
    """
    try:
        monitor = get_monitor()
        stats = monitor.get_recording_stats()
        return {"success": True, "data": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get recording statistics: {str(e)}")


@router.post("/recording-stats/reset")
async def reset_recording_stats(_auth: str = auth_dependency):
    """
    Reset recording session statistics
    """
    try:
        monitor = get_monitor()
        monitor.reset_recording_stats()
        return {"success": True, "message": "Recording statistics reset successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to reset recording statistics: {str(e)}"
        )
