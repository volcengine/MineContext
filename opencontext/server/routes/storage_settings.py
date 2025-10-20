#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""Storage settings API routes"""

import threading

from fastapi import APIRouter
from pydantic import BaseModel, Field

from opencontext.config.global_config import GlobalConfig
from opencontext.server.middleware.auth import auth_dependency
from opencontext.server.utils import convert_resp
from opencontext.utils.logging_utils import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["storage-settings"])
_config_lock = threading.Lock()


# ==================== Data Models ====================


class StorageManagementConfig(BaseModel):
    """Storage management configuration"""

    retention_days: int = Field(
        default=15, ge=7, le=90, description="Screenshot retention period (days), range: 7-90"
    )
    max_storage_size_mb: int = Field(
        default=5000, ge=0, le=50000, description="Maximum storage size (MB), 0 means unlimited"
    )
    auto_cleanup_enabled: bool = Field(
        default=True, description="Enable automatic cleanup"
    )


class GetStorageSettingsResponse(BaseModel):
    """Get storage settings response"""

    config: StorageManagementConfig


class UpdateStorageSettingsRequest(BaseModel):
    """Update storage settings request"""

    config: StorageManagementConfig


class StorageStatsResponse(BaseModel):
    """Storage statistics response"""

    total_size_mb: float = Field(description="Total storage size in MB")
    file_count: int = Field(description="Total number of screenshot files")
    oldest_file_date: str = Field(description="Oldest file date (YYYYMMDD)")
    newest_file_date: str = Field(description="Newest file date (YYYYMMDD)")
    retention_days: int = Field(description="Current retention days setting")
    max_storage_size_mb: int = Field(description="Maximum storage size setting")


# ==================== API Endpoints ====================


@router.get("/api/storage_settings/get")
async def get_storage_settings(_auth: str = auth_dependency):
    """Get current storage management configuration"""
    try:
        config = GlobalConfig.get_instance().get_config()
        if not config:
            return convert_resp(code=500, status=500, message="配置未初始化")

        storage_config = config.get("storage", {})
        management_config = storage_config.get("management", {})

        settings = StorageManagementConfig(
            retention_days=management_config.get("retention_days", 15),
            max_storage_size_mb=management_config.get("max_storage_size_mb", 5000),
            auto_cleanup_enabled=management_config.get("auto_cleanup_enabled", True),
        )

        return convert_resp(data=GetStorageSettingsResponse(config=settings).model_dump())

    except Exception as e:
        logger.exception(f"Failed to get storage settings: {e}")
        return convert_resp(code=500, status=500, message=f"获取存储设置失败: {str(e)}")


@router.post("/api/storage_settings/update")
async def update_storage_settings(
    request: UpdateStorageSettingsRequest, _auth: str = auth_dependency
):
    """Update storage management configuration"""
    with _config_lock:
        try:
            cfg = request.config

            # Validation
            if cfg.retention_days < 7 or cfg.retention_days > 90:
                return convert_resp(
                    code=400, status=400, message="保留天数必须在7-90天之间"
                )

            if cfg.max_storage_size_mb < 0 or cfg.max_storage_size_mb > 50000:
                return convert_resp(
                    code=400, status=400, message="最大存储空间必须在0-50000 MB之间"
                )

            # Prepare storage configuration
            storage_settings = {
                "management": {
                    "retention_days": cfg.retention_days,
                    "max_storage_size_mb": cfg.max_storage_size_mb,
                    "auto_cleanup_enabled": cfg.auto_cleanup_enabled,
                }
            }

            # Save to user settings
            config_manager = GlobalConfig.get_instance().get_config_manager()
            if config_manager.save_user_settings({"storage": storage_settings}):
                logger.info(
                    f"Storage settings updated: retention_days={cfg.retention_days}, "
                    f"max_storage_size_mb={cfg.max_storage_size_mb}, "
                    f"auto_cleanup_enabled={cfg.auto_cleanup_enabled}"
                )
                return convert_resp(message="存储设置更新成功")
            else:
                return convert_resp(code=500, status=500, message="保存存储设置失败")

        except Exception as e:
            logger.exception(f"Failed to update storage settings: {e}")
            return convert_resp(code=500, status=500, message=f"更新存储设置失败: {str(e)}")


@router.get("/api/storage_settings/stats")
async def get_storage_stats(_auth: str = auth_dependency):
    """Get storage statistics (placeholder - will be implemented by frontend service)"""
    try:
        # This endpoint is a placeholder
        # Actual statistics will be calculated by the Electron main process
        # because it has direct access to the file system
        config = GlobalConfig.get_instance().get_config()
        if not config:
            return convert_resp(code=500, status=500, message="配置未初始化")

        storage_config = config.get("storage", {})
        management_config = storage_config.get("management", {})

        # Return current configuration
        # Frontend will call Electron IPC to get actual statistics
        return convert_resp(
            data={
                "retention_days": management_config.get("retention_days", 15),
                "max_storage_size_mb": management_config.get("max_storage_size_mb", 5000),
                "auto_cleanup_enabled": management_config.get("auto_cleanup_enabled", True),
                "message": "Use IPC to get actual storage statistics from main process",
            }
        )

    except Exception as e:
        logger.exception(f"Failed to get storage stats: {e}")
        return convert_resp(code=500, status=500, message=f"获取存储统计失败: {str(e)}")

