# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
事件推送路由 - 缓存版本，支持获取并清空机制
"""

from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, Query

from context_lab.managers.event_manager import get_event_manager, EventType
from context_lab.server.context_lab import ContextLab
from context_lab.utils.logging_utils import get_logger
from context_lab.server.utils import get_context_lab, convert_resp
from context_lab.server.middleware.auth import auth_dependency

logger = get_logger(__name__)
router = APIRouter(tags=["events"])


class PublishEventRequest(BaseModel):
    event_type: str
    data: dict


@router.get("/api/events/fetch")
async def fetch_and_clear_events(
    _auth: str = auth_dependency
):
    """
    获取并清空缓存事件 - 核心API
    
    返回缓存中的所有事件并清空缓存。
    前端应定期调用此接口获取新事件。
    """
    try:
        event_manager = get_event_manager()
        events = event_manager.fetch_and_clear_events()
        
        return convert_resp(data={
            "events": events,
            "count": len(events),
            "message": "success"
        })
        
    except Exception as e:
        logger.exception(f"获取事件失败: {e}")
        return convert_resp(code=500, status=500, message=f"获取事件失败: {str(e)}")


@router.get("/api/events/status")
async def get_event_status(
    context_lab: ContextLab = Depends(get_context_lab),
    _auth: str = auth_dependency
):
    """获取事件缓存状态"""
    try:
        event_manager = get_event_manager()
        status = event_manager.get_cache_status()
        
        return convert_resp(data={
            "event_system_status": "active",
            **status
        })
        
    except Exception as e:
        logger.exception(f"获取事件状态失败: {e}")
        return convert_resp(code=500, status=500, message=f"获取事件状态失败: {str(e)}")


@router.post("/api/events/publish")
async def publish_event(
    request: PublishEventRequest,
    context_lab: ContextLab = Depends(get_context_lab),
    _auth: str = auth_dependency
):
    """
    发布事件（主要用于测试）
    """
    try:
        event_manager = get_event_manager()
        
        # 验证事件类型
        try:
            event_type = EventType(request.event_type)
        except ValueError:
            return convert_resp(code=400, status=400, message=f"无效的事件类型: {request.event_type}")
        
        # 发布事件
        event_id = event_manager.publish_event(
            event_type=event_type,
            data=request.data
        )
        
        return convert_resp(data={
            "event_id": event_id,
            "event_type": request.event_type,
            "message": "事件发布成功"
        })
        
    except Exception as e:
        logger.exception(f"发布事件失败: {e}")
        return convert_resp(code=500, status=500, message=f"发布事件失败: {str(e)}")