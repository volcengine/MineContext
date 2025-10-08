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

# Global lock to ensure atomic configuration updates
_config_lock = threading.Lock()

class ModelSettingsVO(BaseModel):
    """
    Model settings data structure (keeps original field names for backward compatibility).
    Security adjustment: In the GET API, the apiKey field now returns a masked value instead of the plaintext.
    This allows old frontends to still display (masked) without a breaking change.
    """
    modelPlatform: str = Field(..., description="Model platform: doubao | openai")
    modelId: str = Field(..., description="VLM model ID")
    baseUrl: str = Field(..., description="API base URL")
    embeddingModelId: str = Field(..., description="Embedding model ID")
    apiKey: str = Field(..., description="API key (plaintext required in update request; masked in query response)")


class GetModelSettingsRequest(BaseModel):
    """Request body for fetching model settings (empty body)."""
    pass


class GetModelSettingsResponse(BaseModel):
    """Response body for fetching model settings (apiKey is masked)."""
    config: ModelSettingsVO


class UpdateModelSettingsRequest(BaseModel):
    """Request body for updating model settings (accepts plaintext apiKey)."""
    config: ModelSettingsVO


class UpdateModelSettingsResponse(BaseModel):
    """Response body for updating model settings."""
    success: bool
    message: str

@router.get("/api/model_settings/get")
async def get_model_settings(
    _auth: str = auth_dependency
):
    """
    Get current model configuration.
    """
    try:
        def _mask_api_key(raw: str) -> str:
            # Fixed rule: keep first 4 and last 2 characters, mask the middle with ***
            if not raw:
                return ""
            if len(raw) <= 6:  # 4 + 2
                return raw[0] + "***" if len(raw) > 1 else "***"
            return f"{raw[:4]}***{raw[-2:]}"
        # Retrieve current settings from global config
        global_config = GlobalConfig.get_instance()
        config = global_config.get_config()
        if not config:
            raise HTTPException(status_code=500, detail="配置未初始化")
        
        # Get VLM and embedding model configs
        vlm_config = config.get("vlm_model", {})
        embedding_config = config.get("embedding_model", {})
        
        # Infer platform type
        base_url = vlm_config.get("base_url", "")
        platform = vlm_config.get("provider", "")
        
        # Build response - using masked api key
        masked_key = _mask_api_key(vlm_config.get("api_key", ""))
        # Note: apiKey returns masked string for backward compatibility (field presence kept)
        model_settings = ModelSettingsVO(
            modelPlatform=platform,
            modelId=vlm_config.get("model", ""),
            baseUrl=base_url,
            embeddingModelId=embedding_config.get("model", ""),
            apiKey=masked_key
        )
        
        response = GetModelSettingsResponse(config=model_settings)
        return convert_resp(data=response.dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get model settings: {e}")
        return convert_resp(code=500, status=500, message=f"获取模型设置失败: {str(e)}")

@router.post("/api/model_settings/update")
async def update_model_settings(
    request: UpdateModelSettingsRequest,
    _auth: str = auth_dependency
):
    """
    Update model configuration and reinitialize LLM clients.
    """
    with _config_lock:
        try:
            def _is_masked_api_key(val: str) -> bool:
                # Heuristic: contains *** , does not end with *** , and length >= 6
                if not val:
                    return False
                return ("***" in val) and not val.endswith("***") and len(val) >= 6
            global_config = GlobalConfig.get_instance()
            current_cfg = global_config.get_config() or {}
            current_vlm_key = (current_cfg.get("vlm_model") or {}).get("api_key", "")
 
            incoming_key = request.config.apiKey
            keep_original = _is_masked_api_key(incoming_key)

            if not incoming_key and not current_vlm_key:
                # No valid key provided
                raise HTTPException(status_code=400, detail="api key cannot be empty")

            # If masked -> keep original; else use new key
            final_api_key = current_vlm_key if keep_original else incoming_key

            if not final_api_key:
                raise HTTPException(status_code=400, detail="api key cannot be empty")
            if not request.config.modelId:
                raise HTTPException(status_code=400, detail="vlm model cannot be empty")
            if not request.config.embeddingModelId:
                raise HTTPException(status_code=400, detail="embedding model cannot be empty")
            if not request.config.modelPlatform:
                raise HTTPException(status_code=400, detail="vlm model platform cannot be empty")
            if not request.config.baseUrl:
                raise HTTPException(status_code=400, detail="vlm model base url cannot be empty")
            
            # Construct new settings dict
            new_settings = {
                "vlm_model": {
                    "base_url": request.config.baseUrl,
                    "api_key": final_api_key,
                    "model": request.config.modelId,
                    "provider": request.config.modelPlatform,
                    "temperature": 0.7
                },
                "embedding_model": {
                    "base_url": request.config.baseUrl,
                    "api_key": final_api_key,
                    "model": request.config.embeddingModelId,
                    "provider": request.config.modelPlatform,
                    "output_dim": 2048
                }
            }
            
            # Get config manager
            config_manager = GlobalConfig.get_instance().get_config_manager()
            
            if not config_manager:
                raise HTTPException(status_code=500, detail="internal error: config not initialized")

            if not config_manager.save_user_settings(new_settings):
                raise HTTPException(status_code=500, detail="internal error: save user settings failed")

            current_config_path = config_manager.get_config_path()
            config_manager.load_config(current_config_path)

            try:
                # Reinitialize VLM client
                vlm_success = GlobalVLMClient.get_instance().reinitialize()
                logger.info("VLM client reinitialized successfully")
                embedding_success = GlobalEmbeddingClient.get_instance().reinitialize()
                logger.info("Embedding client reinitialized successfully")
                if not vlm_success or not embedding_success:
                    raise HTTPException(status_code=500, detail="internal error: reinitialize LLM clients failed")
                
            except Exception as e:
                logger.error(f"Failed to reinitialize LLM client: {e}")
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
            logger.error(f"Failed to update model settings: {e}")
            return convert_resp(
                code=500,
                status=500,
                message="internal error: update model settings failed"
            )