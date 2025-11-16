#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""Model settings API routes"""

import io
import threading

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from opencontext.config.global_config import GlobalConfig
from opencontext.llm.global_embedding_client import GlobalEmbeddingClient
from opencontext.llm.global_vlm_client import GlobalVLMClient
from opencontext.llm.llm_client import LLMClient, LLMType
from opencontext.server.middleware.auth import auth_dependency
from opencontext.server.utils import convert_resp
from opencontext.utils.logging_utils import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["model-settings"])
_config_lock = threading.Lock()


# ==================== Data Models ====================


class ModelSettingsVO(BaseModel):
    """Model settings with optional separate embedding configuration"""

    modelPlatform: str
    modelId: str
    baseUrl: str
    apiKey: str
    embeddingModelId: str
    embeddingBaseUrl: str | None = None
    embeddingApiKey: str | None = None
    embeddingModelPlatform: str | None = None


class GetModelSettingsResponse(BaseModel):
    config: ModelSettingsVO


class UpdateModelSettingsRequest(BaseModel):
    config: ModelSettingsVO


class UpdateModelSettingsResponse(BaseModel):
    success: bool
    message: str


class ValidateLLMRequest(BaseModel):
    baseUrl: str
    apiKey: str
    modelId: str
    provider: str
    embeddingModelId: str
    embeddingBaseUrl: str | None = None
    embeddingApiKey: str | None = None
    embeddingProvider: str | None = None


# ==================== Helper Functions ====================


def _mask_api_key(raw: str) -> str:
    """Mask API key: keep first 4 and last 2 chars"""
    if not raw:
        return ""
    if len(raw) <= 6:
        return raw[0] + "***" if len(raw) > 1 else "***"
    return f"{raw[:4]}***{raw[-2:]}"


def _is_masked_api_key(val: str) -> bool:
    """Check if API key is already masked"""
    if not val:
        return False
    return ("***" in val) and not val.endswith("***") and len(val) >= 6


def _build_llm_config(
    base_url: str, api_key: str, model: str, provider: str, llm_type: LLMType, **kwargs
) -> dict:
    """Build LLM config dict"""
    config = {"base_url": base_url, "api_key": api_key, "model": model, "provider": provider}
    if llm_type == LLMType.EMBEDDING:
        config["output_dim"] = kwargs.get("output_dim", 2048)
    return config


# ==================== API Endpoints ====================


@router.get("/api/model_settings/get")
async def get_model_settings(_auth: str = auth_dependency):
    """Get current model configuration"""
    try:
        config = GlobalConfig.get_instance().get_config()
        if not config:
            return convert_resp(code=500, status=500, message="配置未初始化")

        vlm_cfg = config.get("vlm_model", {})
        emb_cfg = config.get("embedding_model", {})

        settings = ModelSettingsVO(
            modelPlatform=vlm_cfg.get("provider", ""),
            modelId=vlm_cfg.get("model", ""),
            baseUrl=vlm_cfg.get("base_url", ""),
            apiKey=_mask_api_key(vlm_cfg.get("api_key", "")),
            embeddingModelId=emb_cfg.get("model", ""),
            embeddingBaseUrl=emb_cfg.get("base_url", ""),
            embeddingApiKey=_mask_api_key(emb_cfg.get("api_key", "")),
            embeddingModelPlatform=emb_cfg.get("provider", ""),
        )

        return convert_resp(data=GetModelSettingsResponse(config=settings).model_dump())

    except Exception as e:
        logger.exception(f"Failed to get model settings: {e}")
        return convert_resp(code=500, status=500, message=f"获取模型设置失败: {str(e)}")


@router.post("/api/model_settings/update")
async def update_model_settings(request: UpdateModelSettingsRequest, _auth: str = auth_dependency):
    """Update model configuration and reinitialize LLM clients"""
    with _config_lock:
        try:
            import os
            cfg = request.config
            current_cfg = GlobalConfig.get_instance().get_config() or {}
            current_vlm_key = (current_cfg.get("vlm_model") or {}).get("api_key", "")
            current_emb_key = (current_cfg.get("embedding_model") or {}).get("api_key", "")

            # Resolve VLM API key
            vlm_key = current_vlm_key if _is_masked_api_key(cfg.apiKey) else cfg.apiKey
            if not vlm_key:
                # Prefer provider-specific environment variable for Zhipu
                if (cfg.modelPlatform or "").lower() == "openai" and "bigmodel.cn" in (cfg.baseUrl or ""):
                    vlm_key = os.getenv("ZHIPUAI_API_KEY", "") or os.getenv("LLM_API_KEY", "")
                else:
                    vlm_key = os.getenv("LLM_API_KEY", "") or vlm_key

            # Resolve Embedding API key
            if cfg.embeddingApiKey:
                emb_key = (
                    current_emb_key
                    if _is_masked_api_key(cfg.embeddingApiKey)
                    else cfg.embeddingApiKey
                )
            else:
                # Prefer provider-specific environment variable for Doubao
                emb_key = vlm_key
                target_provider = (cfg.embeddingModelPlatform or cfg.modelPlatform or "").lower()
                target_url = (cfg.embeddingBaseUrl or cfg.baseUrl or "")
                if target_provider == "doubao" or "volces.com" in target_url:
                    emb_key = os.getenv("DOUBAO_API_KEY", "") or os.getenv("EMBEDDING_API_KEY", "") or emb_key

            # Resolve embedding URL and provider
            emb_url = cfg.embeddingBaseUrl or cfg.baseUrl
            # Normalize possible incorrect Zhipu path ending
            if emb_url and emb_url.rstrip("/").endswith("/chat/completions"):
                emb_url = emb_url.rstrip("/")
                emb_url = emb_url[: emb_url.rfind("/chat/completions")]
            base_url = cfg.baseUrl
            if base_url and base_url.rstrip("/").endswith("/chat/completions"):
                base_url = base_url.rstrip("/")
                base_url = base_url[: base_url.rfind("/chat/completions")]
            emb_provider = cfg.embeddingModelPlatform or cfg.modelPlatform

            # Validation
            if not vlm_key:
                return convert_resp(code=400, status=400, message="VLM API key cannot be empty")
            if not emb_key:
                return convert_resp(
                    code=400, status=400, message="Embedding API key cannot be empty"
                )
            if not cfg.modelId:
                return convert_resp(code=400, status=400, message="VLM model ID cannot be empty")
            if not cfg.embeddingModelId:
                return convert_resp(
                    code=400, status=400, message="Embedding model ID cannot be empty"
                )

            # Validate VLM
            vlm_config = _build_llm_config(
                base_url, vlm_key, cfg.modelId, cfg.modelPlatform, LLMType.CHAT
            )
            vlm_valid, vlm_msg = LLMClient(llm_type=LLMType.CHAT, config=vlm_config).validate()
            if not vlm_valid:
                return convert_resp(
                    code=400, status=400, message=f"视觉模型校验失败：{vlm_msg}"
                )

            # Normalize Doubao embedding model alias
            emb_model_id = cfg.embeddingModelId
            if (emb_provider or "").lower() == "doubao" or "volces.com" in (emb_url or "").lower():
                nm = (emb_model_id or "").strip().lower()
                if nm == "doubao-embedding-large" or (
                    "豆包" in emb_model_id and "嵌入" in emb_model_id and "大模型" in emb_model_id
                ):
                    emb_model_id = "doubao-embedding-large-text-240915"

            # Validate Embedding
            emb_config = _build_llm_config(
                emb_url, emb_key, emb_model_id, emb_provider, LLMType.EMBEDDING
            )
            emb_valid, emb_msg = LLMClient(llm_type=LLMType.EMBEDDING, config=emb_config).validate()
            if not emb_valid:
                return convert_resp(
                    code=400, status=400, message=f"向量模型校验失败：{emb_msg}"
                )

            # Save configuration
            new_settings = {"vlm_model": vlm_config, "embedding_model": emb_config}

            config_mgr = GlobalConfig.get_instance().get_config_manager()
            if not config_mgr:
                return convert_resp(code=500, status=500, message="Config manager not initialized")

            if not config_mgr.save_user_settings(new_settings):
                return convert_resp(code=500, status=500, message="Failed to save settings")

            config_mgr.load_config(config_mgr.get_config_path())

            # Reinitialize clients
            if not GlobalVLMClient.get_instance().reinitialize():
                return convert_resp(
                    code=500, status=500, message="Failed to reinitialize VLM client"
                )
            if not GlobalEmbeddingClient.get_instance().reinitialize():
                return convert_resp(
                    code=500, status=500, message="Failed to reinitialize embedding client"
                )

            logger.info("Model settings updated successfully")
            return convert_resp(
                data=UpdateModelSettingsResponse(
                    success=True, message="Model settings updated successfully"
                ).model_dump()
            )

        except Exception as e:
            logger.exception(f"Failed to update model settings: {e}")
