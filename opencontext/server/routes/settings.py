#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Model settings API routes
"""

import threading

from fastapi import APIRouter

from opencontext.config.global_config import GlobalConfig
from opencontext.llm.global_vlm_client import GlobalVLMClient
from opencontext.llm.global_embedding_client import GlobalEmbeddingClient
from opencontext.llm.llm_client import LLMClient, LLMType
from opencontext.server.utils import convert_resp
from opencontext.server.middleware.auth import auth_dependency
from opencontext.utils.logging_utils import get_logger
from pydantic import BaseModel, Field

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


class ValidateLLMRequest(BaseModel):
    """Request body for validating LLM configuration."""
    baseUrl: str = Field(..., description="API base URL")
    apiKey: str = Field(..., description="API key")
    modelId: str = Field(..., description="Model ID to test")
    embeddingModelId: str = Field(..., description="Embedding model ID to test")
    provider: str = Field(..., description="Model platform: doubao | openai")


class ValidateLLMResponse(BaseModel):
    """Response body for LLM validation."""
    vlm_valid: bool
    vlm_message: str
    embedding_valid: bool
    embedding_message: str
    overall_success: bool

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
            return convert_resp(code=500, status=500, message="配置未初始化")

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
        return convert_resp(data=response.model_dump())

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
                return convert_resp(code=400, status=400, message="api key cannot be empty")

            # If masked -> keep original; else use new key
            final_api_key = current_vlm_key if keep_original else incoming_key

            if not final_api_key:
                return convert_resp(code=400, status=400, message="api key cannot be empty")
            if not request.config.modelId:
                return convert_resp(code=400, status=400, message="vlm model cannot be empty")
            if not request.config.embeddingModelId:
                return convert_resp(code=400, status=400, message="embedding model cannot be empty")
            if not request.config.modelPlatform:
                return convert_resp(code=400, status=400, message="vlm model platform cannot be empty")
            if not request.config.baseUrl:
                return convert_resp(code=400, status=400, message="vlm model base url cannot be empty")

            # Validate the configuration before saving
            logger.info("Validating LLM configuration before saving...")
            try:
                # Validate VLM
                vlm_config = {
                    "base_url": request.config.baseUrl,
                    "api_key": final_api_key,
                    "model": request.config.modelId,
                    "provider": request.config.modelPlatform,
                    "temperature": 0.7
                }
                vlm_client = LLMClient(llm_type=LLMType.CHAT, config=vlm_config)
                vlm_valid, vlm_message = vlm_client.validate()

                if not vlm_valid:
                    logger.warning(f"VLM validation failed: {vlm_message}")
                    return convert_resp(
                        code=400,
                        status=400,
                        message=f"VLM validation failed: {vlm_message}"
                    )

                # Validate Embedding model
                embedding_config = {
                    "base_url": request.config.baseUrl,
                    "api_key": final_api_key,
                    "model": request.config.embeddingModelId,
                    "provider": request.config.modelPlatform,
                    "output_dim": 2048
                }
                embedding_client = LLMClient(llm_type=LLMType.EMBEDDING, config=embedding_config)
                embedding_valid, embedding_message = embedding_client.validate()

                if not embedding_valid:
                    logger.warning(f"Embedding model validation failed: {embedding_message}")
                    return convert_resp(
                        code=400,
                        status=400,
                        message=f"Embedding model validation failed: {embedding_message}"
                    )

                logger.info("LLM configuration validation successful")
            except Exception as e:
                logger.error(f"LLM configuration validation error: {e}")
                return convert_resp(
                    code=400,
                    status=400,
                    message=f"Validation error: {str(e)}"
                )

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
                return convert_resp(code=500, status=500, message="internal error: config not initialized")

            if not config_manager.save_user_settings(new_settings):
                return convert_resp(code=500, status=500, message="internal error: save user settings failed")

            current_config_path = config_manager.get_config_path()
            config_manager.load_config(current_config_path)

            try:
                # Reinitialize VLM client
                vlm_success = GlobalVLMClient.get_instance().reinitialize()
                logger.info("VLM client reinitialized successfully")
                embedding_success = GlobalEmbeddingClient.get_instance().reinitialize()
                logger.info("Embedding client reinitialized successfully")
                if not vlm_success or not embedding_success:
                    return convert_resp(
                        code=500,
                        status=500,
                        message="internal error: reinitialize LLM clients failed"
                    )

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
            return convert_resp(data=response.model_dump())

        except Exception as e:
            logger.error(f"Failed to update model settings: {e}")
            return convert_resp(
                code=500,
                status=500,
                message="internal error: update model settings failed"
            )


@router.post("/api/model_settings/validate")
async def validate_llm_config(
    request: ValidateLLMRequest,
    _auth: str = auth_dependency
):
    """
    Validate LLM configuration by testing the API connections.
    This endpoint creates temporary LLM clients to test the configuration without saving it.
    """
    try:
        # Validate VLM (chat model)
        vlm_valid = False
        vlm_message = ""
        try:
            vlm_config = {
                "base_url": request.baseUrl,
                "api_key": request.apiKey,
                "model": request.modelId,
                "provider": request.provider,
                "temperature": 0.7
            }
            vlm_client = LLMClient(llm_type=LLMType.CHAT, config=vlm_config)
            vlm_valid, vlm_message = vlm_client.validate()
        except Exception as e:
            vlm_message = f"VLM client creation failed: {str(e)}"
            logger.error(f"VLM validation error: {e}")

        # Validate Embedding model
        embedding_valid = False
        embedding_message = ""
        try:
            embedding_config = {
                "base_url": request.baseUrl,
                "api_key": request.apiKey,
                "model": request.embeddingModelId,
                "provider": request.provider,
                "output_dim": 2048
            }
            embedding_client = LLMClient(llm_type=LLMType.EMBEDDING, config=embedding_config)
            embedding_valid, embedding_message = embedding_client.validate()
        except Exception as e:
            embedding_message = f"Embedding client creation failed: {str(e)}"
            logger.error(f"Embedding validation error: {e}")

        # Overall success if both validations passed
        overall_success = vlm_valid and embedding_valid

        response = ValidateLLMResponse(
            vlm_valid=vlm_valid,
            vlm_message=vlm_message,
            embedding_valid=embedding_valid,
            embedding_message=embedding_message,
            overall_success=overall_success
        )

        return convert_resp(data=response.model_dump())

    except Exception as e:
        logger.exception(f"Failed to validate LLM configuration: {e}")
        return convert_resp(
            code=500,
            status=500,
            message=f"Validation failed: {str(e)}"
        )