# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Content generation routes (smart tips, todos, activities, reports)
"""

from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, Query

from context_lab.server.context_lab import ContextLab
from context_lab.utils.logging_utils import get_logger
from context_lab.server.utils import get_context_lab, convert_resp
from context_lab.server.middleware.auth import auth_dependency

logger = get_logger(__name__)
router = APIRouter(tags=["content-generation"])

@router.get("/api/content_generation/status")
async def get_content_generation_status(
    context_lab: ContextLab = Depends(get_context_lab),
    _auth: str = auth_dependency
):
    """获取内容生成服务状态"""
    try:
        if not hasattr(context_lab, 'consumption_manager') or not context_lab.consumption_manager:
            return convert_resp(data={
                "enabled": False,
                "message": "Consumption manager not initialized"
            })
        
        status = context_lab.consumption_manager.get_scheduled_tasks_status()
        return convert_resp(data=status)
        
    except Exception as e:
        logger.exception(f"Error getting content generation status: {e}")
        return convert_resp(code=500, status=500, message=f"Failed to get status: {str(e)}")


@router.post("/api/content_generation/start")
async def start_content_generation(
    context_lab: ContextLab = Depends(get_context_lab),
    _auth: str = auth_dependency
):
    """启动内容生成定时任务"""
    try:
        if not hasattr(context_lab, 'consumption_manager') or not context_lab.consumption_manager:
            return convert_resp(code=500, status=500, message="Consumption manager not initialized")
        
        content_generation_config = context_lab.config.get("content_generation", {})
        context_lab.consumption_manager.start_scheduled_tasks(content_generation_config)
        
        return convert_resp(data={"message": "Content generation tasks started"})
        
    except Exception as e:
        logger.exception(f"Error starting content generation: {e}")
        return convert_resp(code=500, status=500, message=f"Failed to start: {str(e)}")


@router.post("/api/content_generation/stop")
async def stop_content_generation(
    context_lab: ContextLab = Depends(get_context_lab),
    _auth: str = auth_dependency
):
    """停止内容生成定时任务"""
    try:
        if hasattr(context_lab, 'consumption_manager') and context_lab.consumption_manager:
            context_lab.consumption_manager.stop_scheduled_tasks()
        
        return convert_resp(data={"message": "Content generation tasks stopped"})
        
    except Exception as e:
        logger.exception(f"Error stopping content generation: {e}")
        return convert_resp(code=500, status=500, message=f"Failed to stop: {str(e)}")