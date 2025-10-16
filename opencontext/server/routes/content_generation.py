# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Content generation routes (smart tips, todos, activities, reports)
"""

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from opencontext.server.middleware.auth import auth_dependency
from opencontext.server.opencontext import OpenContext
from opencontext.server.utils import convert_resp, get_context_lab
from opencontext.utils.logging_utils import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["content-generation"])

# ==================== Data Models ====================


class ActivityConfig(BaseModel):
    """Configuration for activity task"""

    enabled: Optional[bool] = None
    interval: Optional[int] = Field(
        None, ge=600, description="Interval in seconds, minimum 600 (10 minutes)"
    )


class TipsConfig(BaseModel):
    """Configuration for tips task"""

    enabled: Optional[bool] = None
    interval: Optional[int] = Field(
        None, ge=1800, description="Interval in seconds, minimum 1800 (30 minutes)"
    )


class TodosConfig(BaseModel):
    """Configuration for todos task"""

    enabled: Optional[bool] = None
    interval: Optional[int] = Field(
        None, ge=1800, description="Interval in seconds, minimum 1800 (30 minutes)"
    )


class ReportConfig(BaseModel):
    """Configuration for daily report"""

    enabled: Optional[bool] = None
    time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$", description="Time in HH:MM format")


class ContentGenerationConfig(BaseModel):
    """Complete content generation configuration"""

    activity: Optional[ActivityConfig] = None
    tips: Optional[TipsConfig] = None
    todos: Optional[TodosConfig] = None
    report: Optional[ReportConfig] = None


@router.get("/api/content_generation/config")
async def get_content_generation_config(
    opencontext: OpenContext = Depends(get_context_lab), _auth: str = auth_dependency
):
    """
    Get content generation configuration
    """
    try:
        if not hasattr(opencontext, "consumption_manager") or not opencontext.consumption_manager:
            return convert_resp(code=500, status=500, message="Consumption manager not initialized")

        config = opencontext.consumption_manager.get_task_config()
        return convert_resp(data=config)

    except Exception as e:
        logger.exception(f"Error getting content generation config: {e}")
        return convert_resp(code=500, status=500, message=f"Failed to get config: {str(e)}")


@router.post("/api/content_generation/config")
async def update_content_generation_config(
    config: ContentGenerationConfig,
    opencontext: OpenContext = Depends(get_context_lab),
    _auth: str = auth_dependency,
):
    """
    Update content generation configuration (supports partial updates)
    """
    try:
        if not hasattr(opencontext, "consumption_manager") or not opencontext.consumption_manager:
            return convert_resp(code=500, status=500, message="Consumption manager not initialized")
        config_dict = {}
        for task_name in ["activity", "tips", "todos"]:
            task_config = getattr(config, task_name, None)
            if task_config is not None:
                task_dict = {}
                if task_config.enabled is not None:
                    task_dict["enabled"] = task_config.enabled
                if task_config.interval is not None:
                    task_dict["interval"] = task_config.interval
                if task_dict:
                    config_dict[task_name] = task_dict
        if config.report is not None:
            report_dict = {}
            if config.report.enabled is not None:
                report_dict["enabled"] = config.report.enabled
            if config.report.time is not None:
                report_dict["time"] = config.report.time
            if report_dict:
                config_dict["report"] = report_dict

        if not config_dict:
            return convert_resp(code=400, status=400, message="No valid configuration provided")

        if opencontext.consumption_manager.update_task_config(config_dict):
            try:
                from opencontext.config.global_config import GlobalConfig

                config_manager = GlobalConfig.get_instance().get_config_manager()

                # Get current user settings and update content_generation section
                updated_config = opencontext.consumption_manager.get_task_config()
                config_manager.save_user_settings({"content_generation": updated_config})
                logger.info("Configuration saved to user_settings.yaml")
            except Exception as e:
                logger.error(f"Failed to save configuration to file: {e}")
                # Continue even if save fails - configuration is still applied in memory

            return convert_resp(message="Configuration updated successfully")
        else:
            return convert_resp(code=500, status=500, message="Failed to update configuration")

    except Exception as e:
        logger.exception(f"Error updating content generation config: {e}")
        return convert_resp(code=500, status=500, message=f"Failed to update config: {str(e)}")
