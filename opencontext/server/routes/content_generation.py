# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Content generation routes (smart tips, todos, activities, reports)
"""

from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, Query

from opencontext.server.opencontext import OpenContext
from opencontext.utils.logging_utils import get_logger
from opencontext.server.utils import get_context_lab, convert_resp
from opencontext.server.middleware.auth import auth_dependency

logger = get_logger(__name__)
router = APIRouter(tags=["content-generation"])

@router.get("/api/content_generation/status")
async def get_content_generation_status(
    opencontext: OpenContext = Depends(get_context_lab),
    _auth: str = auth_dependency
):
    """Get content generation service status"""
    try:
        if not hasattr(opencontext, 'consumption_manager') or not opencontext.consumption_manager:
            return convert_resp(data={
                "enabled": False,
                "message": "Consumption manager not initialized"
            })
        
        status = opencontext.consumption_manager.get_scheduled_tasks_status()
        return convert_resp(data=status)
        
    except Exception as e:
        logger.exception(f"Error getting content generation status: {e}")
        return convert_resp(code=500, status=500, message=f"Failed to get status: {str(e)}")


@router.post("/api/content_generation/start")
async def start_content_generation(
    opencontext: OpenContext = Depends(get_context_lab),
    _auth: str = auth_dependency
):
    """Start content generation scheduled tasks"""
    try:
        if not hasattr(opencontext, 'consumption_manager') or not opencontext.consumption_manager:
            return convert_resp(code=500, status=500, message="Consumption manager not initialized")
        
        content_generation_config = opencontext.config.get("content_generation", {})
        opencontext.consumption_manager.start_scheduled_tasks(content_generation_config)
        
        return convert_resp(data={"message": "Content generation tasks started"})
        
    except Exception as e:
        logger.exception(f"Error starting content generation: {e}")
        return convert_resp(code=500, status=500, message=f"Failed to start: {str(e)}")


@router.post("/api/content_generation/stop")
async def stop_content_generation(
    opencontext: OpenContext = Depends(get_context_lab),
    _auth: str = auth_dependency
):
    """Stop content generation scheduled tasks"""
    try:
        if hasattr(opencontext, 'consumption_manager') and opencontext.consumption_manager:
            opencontext.consumption_manager.stop_scheduled_tasks()
        
        return convert_resp(data={"message": "Content generation tasks stopped"})
        
    except Exception as e:
        logger.exception(f"Error stopping content generation: {e}")
        return convert_resp(code=500, status=500, message=f"Failed to stop: {str(e)}")