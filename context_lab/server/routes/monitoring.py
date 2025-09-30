# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Server component: monitoring routes - 监控相关API端点
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from datetime import datetime
from context_lab.server.utils import get_context_lab
from context_lab.server.context_lab import ContextLab
from context_lab.monitoring import get_monitor
from context_lab.server.middleware.auth import auth_dependency
from datetime import timedelta

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


@router.get("/overview")
async def get_system_overview(
    context_lab: ContextLab = Depends(get_context_lab),
    _auth: str = auth_dependency
):
    """
    获取系统监控概览
    """
    try:
        monitor = get_monitor()
        overview = monitor.get_system_overview()
        return {"success": True, "data": overview}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取系统概览失败: {str(e)}")


@router.get("/context-types")
async def get_context_type_stats(
    force_refresh: bool = Query(False, description="是否强制刷新缓存"),
    context_lab: ContextLab = Depends(get_context_lab),
    _auth: str = auth_dependency
):
    """
    获取各context_type的候选数量统计
    """
    try:
        monitor = get_monitor()
        stats = monitor.get_context_type_stats(force_refresh=force_refresh)
        return {"success": True, "data": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取上下文类型统计失败: {str(e)}")


@router.get("/token-usage")
async def get_token_usage_summary(
    hours: int = Query(24, ge=1, le=168, description="统计时间范围（小时）"),
    _auth: str = auth_dependency
):
    """
    获取模型token消耗详情
    """
    try:
        monitor = get_monitor()
        summary = monitor.get_token_usage_summary(hours=hours)
        return {"success": True, "data": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取token使用统计失败: {str(e)}")


@router.get("/processing")
async def get_processing_metrics(
    hours: int = Query(24, ge=1, le=168, description="统计时间范围（小时）"),
    _auth: str = auth_dependency
):
    """
    获取处理器性能指标
    """
    try:
        monitor = get_monitor()
        metrics = monitor.get_processing_summary(hours=hours)
        return {"success": True, "data": metrics}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取处理性能指标失败: {str(e)}")


@router.get("/todo-stats")
async def get_todo_stats(
    hours: int = Query(24, ge=1, le=168, description="统计时间范围（小时）"),
    context_lab: ContextLab = Depends(get_context_lab),
    _auth: str = auth_dependency
):
    """
    获取TODO任务统计
    """
    try:
        monitor = get_monitor()
        stats = monitor.get_todo_stats(hours=hours)
        return {"success": True, "data": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取TODO统计失败: {str(e)}")


@router.get("/tips-count")
async def get_tips_count(
    hours: int = Query(24, ge=1, le=168, description="统计时间范围（小时）"),
    context_lab: ContextLab = Depends(get_context_lab),
    _auth: str = auth_dependency
):
    """
    获取Tips提示数量
    """
    try:
        monitor = get_monitor()
        count = monitor.get_tips_count(hours=hours)
        return {"success": True, "data": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取Tips数量失败: {str(e)}")


@router.get("/activity-count")
async def get_activity_count(
    hours: int = Query(24, ge=1, le=168, description="统计时间范围（小时）"),
    context_lab: ContextLab = Depends(get_context_lab),
    _auth: str = auth_dependency
):
    """
    获取活动记录数量
    """
    try:
        monitor = get_monitor()
        count = monitor.get_activity_count(hours=hours)
        return {"success": True, "data": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取活动数量失败: {str(e)}")


@router.post("/refresh-context-stats")
async def refresh_context_type_stats(
    context_lab: ContextLab = Depends(get_context_lab),
    _auth: str = auth_dependency
):
    """
    刷新上下文类型统计缓存
    """
    try:
        monitor = get_monitor()
        stats = monitor.get_context_type_stats(force_refresh=True)
        return {"success": True, "data": stats, "message": "统计数据已刷新"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刷新统计数据失败: {str(e)}")


@router.get("/health")
async def monitoring_health(
    _auth: str = auth_dependency
):
    """
    监控系统健康检查
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