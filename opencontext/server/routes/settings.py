#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Model settings API routes
"""

import threading
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Depends

from opencontext.config.global_config import GlobalConfig
from opencontext.llm.global_vlm_client import GlobalVLMClient
from opencontext.llm.global_embedding_client import GlobalEmbeddingClient
from opencontext.server.utils import convert_resp
from opencontext.server.middleware.auth import auth_dependency
from opencontext.utils.logging_utils import get_logger
from pydantic import BaseModel, Field
from typing import Optional

logger = get_logger(__name__)
router = APIRouter(tags=["model-settings"])

# 全局锁，用于确保配置更新的原子性
_config_lock = threading.Lock()

class ModelSettingsVO(BaseModel):
    """模型设置数据结构"""
    modelPlatform: str = Field(..., description="模型平台: doubao | openai")
    modelId: str = Field(..., description="VLM模型ID")
    baseUrl: str = Field(..., description="API基础URL")
    embeddingModelId: str = Field(..., description="嵌入模型ID")
    apiKey: str = Field(..., description="API密钥")


class GetModelSettingsRequest(BaseModel):
    """获取模型设置请求（空请求）"""
    pass


class GetModelSettingsResponse(BaseModel):
    """获取模型设置响应"""
    config: ModelSettingsVO


class UpdateModelSettingsRequest(BaseModel):
    """更新模型设置请求"""
    config: ModelSettingsVO


class UpdateModelSettingsResponse(BaseModel):
    """更新模型设置响应"""
    success: bool
    message: str

@router.get("/api/model_settings/get")
async def get_model_settings(
    _auth: str = auth_dependency
):
    """
    获取当前模型配置
    """
    try:
        # 从全局配置获取当前设置
        global_config = GlobalConfig.get_instance()
        config = global_config.get_config()
        
        if not config:
            raise HTTPException(status_code=500, detail="配置未初始化")
        
        # 获取VLM和嵌入模型配置
        vlm_config = config.get("vlm_model", {})
        embedding_config = config.get("embedding_model", {})
        
        # 推断平台类型
        base_url = vlm_config.get("base_url", "")
        platform = vlm_config.get("provider", "")
        
        # 构造响应
        model_settings = ModelSettingsVO(
            modelPlatform=platform,
            modelId=vlm_config.get("model", ""),
            baseUrl=base_url,
            embeddingModelId=embedding_config.get("model", ""),
            apiKey=vlm_config.get("api_key", "")
        )
        
        response = GetModelSettingsResponse(config=model_settings)
        return convert_resp(data=response.dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"获取模型设置失败: {e}")
        return convert_resp(code=500, status=500, message=f"获取模型设置失败: {str(e)}")


@router.post("/api/model_settings/update")
async def update_model_settings(
    request: UpdateModelSettingsRequest,
    _auth: str = auth_dependency
):
    """
    更新模型配置并重新初始化LLM客户端
    """
    with _config_lock:
        try:
            # 验证请求
            if not request.config.apiKey:
                raise HTTPException(status_code=400, detail="api key cannot be empty")
            if not request.config.modelId:
                raise HTTPException(status_code=400, detail="vlm model cannot be empty")
            if not request.config.embeddingModelId:
                raise HTTPException(status_code=400, detail="embedding model cannot be empty")
            if not request.config.modelPlatform:
                raise HTTPException(status_code=400, detail="vlm model platform cannot be empty")
            if not request.config.baseUrl:
                raise HTTPException(status_code=400, detail="vlm model base url cannot be empty")
            
            # 构造新的配置
            new_settings = {
                "vlm_model": {
                    "base_url": request.config.baseUrl,
                    "api_key": request.config.apiKey,
                    "model": request.config.modelId,
                    "provider": request.config.modelPlatform,
                    "temperature": 0.7
                },
                "embedding_model": {
                    "base_url": request.config.baseUrl,
                    "api_key": request.config.apiKey,
                    "model": request.config.embeddingModelId,
                    "provider": request.config.modelPlatform,
                    "output_dim": 2048
                }
            }
            
            # 获取配置管理器
            config_manager = GlobalConfig.get_instance().get_config_manager()
            
            if not config_manager:
                raise HTTPException(status_code=500, detail="internal error: config not initialized")

            if not config_manager.save_user_settings(new_settings):
                raise HTTPException(status_code=500, detail="internal error: save user settings failed")

            current_config_path = config_manager.get_config_path()
            config_manager.load_config(current_config_path)

            try:
                # 重新初始化VLM客户端
                vlm_success = GlobalVLMClient.get_instance().reinitialize()
                logger.info("VLM客户端重新初始化成功")
                embedding_success = GlobalEmbeddingClient.get_instance().reinitialize()
                logger.info("嵌入客户端重新初始化成功")
                if not vlm_success or not embedding_success:
                    raise HTTPException(status_code=500, detail="internal error: reinitialize LLM clients failed")
                
            except Exception as e:
                logger.error(f"重新初始化LLM客户端失败: {e}")
                return convert_resp(
                    code=500,
                    status=500,
                    message="internal error: reinitialize LLM clients failed"
                )
            
            response = UpdateModelSettingsResponse(
                success=True,
                message="model settings updated successfully"
            )
            return convert_resp(data=response.dict())
            
        except HTTPException:
            raise
        except Exception as e:
            return convert_resp(
                code=500,
                status=500,
                message="internal error: update model settings failed"
            )