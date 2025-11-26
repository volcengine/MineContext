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


# ==================== Helper Functions ====================

def _build_llm_config(
    base_url: str, api_key: str, model: str, provider: str, llm_type: LLMType, **kwargs
) -> dict:
    """Build LLM config dict"""
    config = {"base_url": base_url, "api_key": api_key, "model": model, "provider": provider}
    
    # Add optional parameters
    if "timeout" in kwargs:
        config["timeout"] = kwargs["timeout"]

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
            apiKey=vlm_cfg.get("api_key", ""),
            embeddingModelId=emb_cfg.get("model", ""),
            embeddingBaseUrl=emb_cfg.get("base_url", ""),
            embeddingApiKey=emb_cfg.get("api_key", ""),
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
            cfg = request.config

            # Use API keys directly from frontend
            vlm_key = cfg.apiKey
            emb_key = cfg.embeddingApiKey or vlm_key

            # Resolve embedding URL and provider
            emb_url = cfg.embeddingBaseUrl or cfg.baseUrl
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
                cfg.baseUrl, vlm_key, cfg.modelId, cfg.modelPlatform, LLMType.CHAT, timeout=15
            )
            vlm_valid, vlm_msg = LLMClient(llm_type=LLMType.CHAT, config=vlm_config).validate()
            if not vlm_valid:
                return convert_resp(
                    code=400, status=400, message=f"VLM validation failed: {vlm_msg}"
                )

            # Validate Embedding
            emb_config = _build_llm_config(
                emb_url, emb_key, cfg.embeddingModelId, emb_provider, LLMType.EMBEDDING, timeout=15
            )
            emb_valid, emb_msg = LLMClient(llm_type=LLMType.EMBEDDING, config=emb_config).validate()
            if not emb_valid:
                return convert_resp(
                    code=400, status=400, message=f"Embedding validation failed: {emb_msg}"
                )

            # Save configuration (without timeout limit)
            vlm_config_save = _build_llm_config(
                cfg.baseUrl, vlm_key, cfg.modelId, cfg.modelPlatform, LLMType.CHAT
            )
            emb_config_save = _build_llm_config(
                emb_url, emb_key, cfg.embeddingModelId, emb_provider, LLMType.EMBEDDING
            )
            
            new_settings = {"vlm_model": vlm_config_save, "embedding_model": emb_config_save}

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
            return convert_resp(code=500, status=500, message="Failed to update model settings")


@router.post("/api/model_settings/validate")
async def validate_llm_config(request: UpdateModelSettingsRequest, _auth: str = auth_dependency):
    """Validate LLM configuration from frontend (without saving)"""
    try:
        cfg = request.config

        # Use API keys directly from frontend
        vlm_key = cfg.apiKey
        emb_key = cfg.embeddingApiKey or vlm_key

        # Resolve embedding URL and provider
        emb_url = cfg.embeddingBaseUrl or cfg.baseUrl
        emb_provider = cfg.embeddingModelPlatform or cfg.modelPlatform

        # Validation
        if not vlm_key:
            return convert_resp(code=400, status=400, message="VLM API key cannot be empty")
        if not emb_key:
            return convert_resp(code=400, status=400, message="Embedding API key cannot be empty")
        if not cfg.modelId:
            return convert_resp(code=400, status=400, message="VLM model ID cannot be empty")
        if not cfg.embeddingModelId:
            return convert_resp(
                code=400, status=400, message="Embedding model ID cannot be empty"
            )

        # Build configs for validation (without saving)
        vlm_config = _build_llm_config(
            cfg.baseUrl, vlm_key, cfg.modelId, cfg.modelPlatform, LLMType.CHAT, timeout=15
        )
        emb_config = _build_llm_config(
            emb_url, emb_key, cfg.embeddingModelId, emb_provider, LLMType.EMBEDDING, timeout=15
        )

        # Validate VLM
        vlm_valid, vlm_msg = LLMClient(llm_type=LLMType.CHAT, config=vlm_config).validate()

        # Validate Embedding
        emb_valid, emb_msg = LLMClient(llm_type=LLMType.EMBEDDING, config=emb_config).validate()

        # Build error message
        if not vlm_valid or not emb_valid:
            errors = []
            if not vlm_valid:
                errors.append(f"VLM: {vlm_msg}")
            if not emb_valid:
                errors.append(f"Embedding: {emb_msg}")
            error_msg = "; ".join(errors)
            return convert_resp(code=400, status=400, message=error_msg)

        return convert_resp(code=0, status=200, message="连接测试成功！VLM和Embedding模型均正常")

    except Exception as e:
        logger.exception(f"Validation failed: {e}")
        return convert_resp(code=500, status=500, message=f"Validation failed: {str(e)}")


# ==================== General Settings ====================


class GeneralSettingsRequest(BaseModel):
    """General system settings request"""

    capture: dict | None = None
    processing: dict | None = None
    logging: dict | None = None
    content_generation: dict | None = None


@router.get("/api/settings/general")
async def get_general_settings(_auth: str = auth_dependency):
    """Get general system settings"""
    try:
        import os

        config = GlobalConfig.get_instance().get_config()
        if not config:
            return convert_resp(code=500, status=500, message="Configuration not initialized")

        settings = {
            "capture": config.get("capture", {}),
            "processing": config.get("processing", {}),
            "logging": config.get("logging", {}),
            "content_generation": config.get("content_generation", {}),
        }

        # Resolve environment variables in debug output path for display
        if "content_generation" in settings and "debug" in settings["content_generation"]:
            debug_config = settings["content_generation"]["debug"]
            if "output_path" in debug_config:
                output_path = debug_config["output_path"]
                # Resolve environment variables
                if "${CONTEXT_PATH" in output_path:
                    context_path = os.getenv("CONTEXT_PATH", ".")
                    resolved_path = output_path.replace("${CONTEXT_PATH:.}", context_path)
                    resolved_path = resolved_path.replace("${CONTEXT_PATH}", context_path)
                    # Add resolved path as a separate field for display
                    debug_config["output_path_resolved"] = resolved_path

        return convert_resp(data=settings)

    except Exception as e:
        logger.exception(f"Failed to get general settings: {e}")
        return convert_resp(
            code=500, status=500, message=f"Failed to get general settings: {str(e)}"
        )


@router.post("/api/settings/general")
async def update_general_settings(request: GeneralSettingsRequest, _auth: str = auth_dependency):
    """Update general system settings"""
    with _config_lock:
        try:
            config_mgr = GlobalConfig.get_instance().get_config_manager()
            if not config_mgr:
                return convert_resp(code=500, status=500, message="Config manager not initialized")

            # Build settings dict
            settings = {}
            if request.capture is not None:
                settings["capture"] = request.capture
            if request.processing is not None:
                settings["processing"] = request.processing
            if request.logging is not None:
                settings["logging"] = request.logging
            if request.content_generation is not None:
                settings["content_generation"] = request.content_generation

            if not settings:
                return convert_resp(code=400, status=400, message="No settings provided")

            # Save to user_setting.yaml
            if not config_mgr.save_user_settings(settings):
                return convert_resp(code=500, status=500, message="Failed to save settings")

            # Reload config
            config_mgr.load_config(config_mgr.get_config_path())

            logger.info("General settings updated successfully")
            return convert_resp(code=0, status=200, message="Settings updated successfully")

        except Exception as e:
            logger.exception(f"Failed to update general settings: {e}")
            return convert_resp(
                code=500, status=500, message=f"Failed to update settings: {str(e)}"
            )


# ==================== Prompts Settings ====================


class PromptsUpdateRequest(BaseModel):
    """Prompts update request"""

    prompts: dict


@router.get("/api/settings/prompts")
async def get_prompts(_auth: str = auth_dependency):
    """Get current prompts"""
    try:
        prompt_mgr = GlobalConfig.get_instance().get_prompt_manager()
        if not prompt_mgr:
            return convert_resp(code=500, status=500, message="Prompt manager not initialized")

        return convert_resp(data={"prompts": prompt_mgr.prompts})

    except Exception as e:
        logger.exception(f"Failed to get prompts: {e}")
        return convert_resp(code=500, status=500, message=f"Failed to get prompts: {str(e)}")


@router.post("/api/settings/prompts")
async def update_prompts(request: PromptsUpdateRequest, _auth: str = auth_dependency):
    """Update prompts"""
    try:
        prompt_mgr = GlobalConfig.get_instance().get_prompt_manager()
        if not prompt_mgr:
            return convert_resp(code=500, status=500, message="Prompt manager not initialized")

        if not prompt_mgr.save_prompts(request.prompts):
            return convert_resp(code=500, status=500, message="Failed to save prompts")

        logger.info("Prompts updated successfully")
        return convert_resp(code=0, status=200, message="Prompts updated successfully")

    except Exception as e:
        logger.exception(f"Failed to update prompts: {e}")
        return convert_resp(code=500, status=500, message=f"Failed to update prompts: {str(e)}")


@router.post("/api/settings/prompts/import")
async def import_prompts(file: UploadFile = File(...), _auth: str = auth_dependency):
    """Import prompts from YAML file"""
    try:
        prompt_mgr = GlobalConfig.get_instance().get_prompt_manager()
        if not prompt_mgr:
            return convert_resp(code=500, status=500, message="Prompt manager not initialized")

        # Read file content
        content = await file.read()
        yaml_content = content.decode("utf-8")

        if not prompt_mgr.import_prompts(yaml_content):
            return convert_resp(code=400, status=400, message="Failed to import prompts")

        logger.info("Prompts imported successfully")
        return convert_resp(code=0, status=200, message="Prompts imported successfully")

    except Exception as e:
        logger.exception(f"Failed to import prompts: {e}")
        return convert_resp(code=500, status=500, message=f"Failed to import prompts: {str(e)}")


@router.get("/api/settings/prompts/export")
async def export_prompts(_auth: str = auth_dependency):
    """Export prompts as YAML file"""
    try:
        prompt_mgr = GlobalConfig.get_instance().get_prompt_manager()
        if not prompt_mgr:
            return convert_resp(code=500, status=500, message="Prompt manager not initialized")

        yaml_content = prompt_mgr.export_prompts()
        if not yaml_content:
            return convert_resp(code=500, status=500, message="Failed to export prompts")

        # Return as downloadable file
        language = GlobalConfig.get_instance().get_language()
        filename = f"prompts_{language}.yaml"

        return StreamingResponse(
            io.BytesIO(yaml_content.encode("utf-8")),
            media_type="application/x-yaml",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    except Exception as e:
        logger.exception(f"Failed to export prompts: {e}")
        return convert_resp(code=500, status=500, message=f"Failed to export prompts: {str(e)}")


@router.get("/api/settings/prompts/language")
async def get_prompt_language(_auth: str = auth_dependency):
    """Get current prompt language"""
    try:
        language = GlobalConfig.get_instance().get_language()
        return convert_resp(data={"language": language})
    except Exception as e:
        logger.exception(f"Failed to get prompt language: {e}")
        return convert_resp(code=500, status=500, message=f"Failed to get language: {str(e)}")


class LanguageChangeRequest(BaseModel):
    """Language change request"""

    language: str = Field(..., pattern="^(zh|en)$")


@router.post("/api/settings/prompts/language")
async def change_prompt_language(request: LanguageChangeRequest, _auth: str = auth_dependency):
    """Change prompt language"""
    try:
        # Update language setting and reload prompts
        success = GlobalConfig.get_instance().set_language(request.language)

        if not success:
            return convert_resp(code=500, status=500, message="Failed to change language")

        logger.info(f"Prompt language changed to: {request.language}")
        return convert_resp(message=f"Language changed to {request.language}")
    except Exception as e:
        logger.exception(f"Failed to change prompt language: {e}")
        return convert_resp(code=500, status=500, message=f"Failed to change language: {str(e)}")


# ==================== Reset Settings ====================


@router.post("/api/settings/reset")
async def reset_settings(_auth: str = auth_dependency):
    """Reset all user settings to defaults"""
    with _config_lock:
        try:
            config_mgr = GlobalConfig.get_instance().get_config_manager()
            prompt_mgr = GlobalConfig.get_instance().get_prompt_manager()

            success = True

            # Reset user settings
            if config_mgr:
                if not config_mgr.reset_user_settings():
                    success = False
                    logger.error("Failed to reset user settings")

            # Reset user prompts
            if prompt_mgr:
                if not prompt_mgr.reset_user_prompts():
                    success = False
                    logger.error("Failed to reset user prompts")

            if not success:
                return convert_resp(code=500, status=500, message="Failed to reset some settings")

            logger.info("All settings reset successfully")
            return convert_resp(code=0, status=200, message="Settings reset successfully")

        except Exception as e:
            logger.exception(f"Failed to reset settings: {e}")
            return convert_resp(code=500, status=500, message=f"Failed to reset settings: {str(e)}")


# ==================== Prompts History & Debug ====================


@router.get("/api/settings/prompts/history/{category}")
async def get_prompts_history(category: str, _auth: str = auth_dependency):
    """
    Get debug history files for a prompt category

    Args:
        category: Prompt category (smart_tip_generation, todo_extraction, generation_report, realtime_activity_monitor)

    Returns:
        List of history files with metadata
    """
    try:
        import os
        from pathlib import Path

        # Map category names to directory names
        category_map = {
            "smart_tip_generation": "tips",
            "todo_extraction": "todo",
            "generation_report": "report",
            "realtime_activity_monitor": "activity",
        }

        if category not in category_map:
            return convert_resp(code=400, status=400, message=f"Invalid category: {category}")

        dir_name = category_map[category]

        # Get debug output path from config
        config = GlobalConfig.get_instance().get_config()
        if not config:
            return convert_resp(code=500, status=500, message="Configuration not initialized")

        debug_config = config.get("content_generation", {}).get("debug", {})
        if not debug_config.get("enabled", False):
            return convert_resp(code=400, status=400, message="Debug mode is not enabled")

        base_path = debug_config.get("output_path", "${CONTEXT_PATH:.}/debug/generation")

        # Resolve environment variables
        if "${CONTEXT_PATH" in base_path:
            context_path = os.getenv("CONTEXT_PATH", ".")
            base_path = base_path.replace("${CONTEXT_PATH:.}", context_path)
            base_path = base_path.replace("${CONTEXT_PATH}", context_path)

        # Get directory path
        history_dir = Path(base_path) / dir_name

        if not history_dir.exists():
            return convert_resp(data=[])

        # List all JSON files
        history_files = []
        for filepath in sorted(history_dir.glob("*.json"), reverse=True):  # Most recent first
            try:
                # Read file to check if it has response
                import json

                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)

                has_result = bool(data.get("response"))
                timestamp_str = data.get("timestamp", "")

                history_files.append(
                    {
                        "filename": filepath.name,
                        "timestamp": timestamp_str,
                        "has_result": has_result,
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to read history file {filepath}: {e}")
                continue

        return convert_resp(data=history_files)

    except Exception as e:
        logger.exception(f"Failed to get prompts history for {category}: {e}")
        return convert_resp(code=500, status=500, message=f"Failed to get history: {str(e)}")


@router.get("/api/settings/prompts/history/{category}/{filename}")
async def get_prompts_history_detail(category: str, filename: str, _auth: str = auth_dependency):
    """
    Get detailed content of a specific debug history file

    Args:
        category: Prompt category
        filename: History file name

    Returns:
        Debug file content with messages and response
    """
    try:
        import json
        import os
        from pathlib import Path

        # Map category names to directory names
        category_map = {
            "smart_tip_generation": "tips",
            "todo_extraction": "todo",
            "generation_report": "report",
            "realtime_activity_monitor": "activity",
        }

        if category not in category_map:
            return convert_resp(code=400, status=400, message=f"Invalid category: {category}")

        dir_name = category_map[category]

        # Get debug output path from config
        config = GlobalConfig.get_instance().get_config()
        if not config:
            return convert_resp(code=500, status=500, message="Configuration not initialized")

        debug_config = config.get("content_generation", {}).get("debug", {})
        base_path = debug_config.get("output_path", "${CONTEXT_PATH:.}/debug/generation")

        # Resolve environment variables
        if "${CONTEXT_PATH" in base_path:
            context_path = os.getenv("CONTEXT_PATH", ".")
            base_path = base_path.replace("${CONTEXT_PATH:.}", context_path)
            base_path = base_path.replace("${CONTEXT_PATH}", context_path)

        # Get file path (validate filename to prevent directory traversal)
        if ".." in filename or "/" in filename or "\\" in filename:
            return convert_resp(code=400, status=400, message="Invalid filename")

        filepath = Path(base_path) / dir_name / filename

        if not filepath.exists():
            return convert_resp(code=404, status=404, message="History file not found")

        # Read and return file content
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        return convert_resp(data=data)

    except Exception as e:
        logger.exception(f"Failed to get history detail for {category}/{filename}: {e}")
        return convert_resp(code=500, status=500, message=f"Failed to get history detail: {str(e)}")


class RegenerateRequest(BaseModel):
    """Regenerate request with custom prompts"""

    category: str
    history_file: str
    custom_prompts: dict = Field(
        default_factory=dict, description="Custom prompts with system and user keys"
    )


@router.post("/api/settings/prompts/regenerate")
async def regenerate_with_custom_prompts(request: RegenerateRequest, _auth: str = auth_dependency):
    """
    Regenerate content using custom prompts and compare with original result

    Args:
        request: Regenerate request with category, history_file, and custom_prompts

    Returns:
        Comparison data with original and new results
    """
    try:
        import json
        import os
        from pathlib import Path

        # Map category names to directory names
        category_map = {
            "smart_tip_generation": "tips",
            "todo_extraction": "todo",
            "generation_report": "report",
            "realtime_activity_monitor": "activity",
        }

        if request.category not in category_map:
            return convert_resp(
                code=400, status=400, message=f"Invalid category: {request.category}"
            )

        dir_name = category_map[request.category]

        # Get debug output path from config
        config = GlobalConfig.get_instance().get_config()
        if not config:
            return convert_resp(code=500, status=500, message="Configuration not initialized")

        debug_config = config.get("content_generation", {}).get("debug", {})
        base_path = debug_config.get("output_path", "${CONTEXT_PATH:.}/debug/generation")

        # Resolve environment variables
        if "${CONTEXT_PATH" in base_path:
            context_path = os.getenv("CONTEXT_PATH", ".")
            base_path = base_path.replace("${CONTEXT_PATH:.}", context_path)
            base_path = base_path.replace("${CONTEXT_PATH}", context_path)

        # Validate and read history file
        if (
            ".." in request.history_file
            or "/" in request.history_file
            or "\\" in request.history_file
        ):
            return convert_resp(code=400, status=400, message="Invalid filename")

        filepath = Path(base_path) / dir_name / request.history_file

        if not filepath.exists():
            return convert_resp(code=404, status=404, message="History file not found")

        # Read original debug data
        with open(filepath, "r", encoding="utf-8") as f:
            original_data = json.load(f)

        original_messages = original_data.get("messages", [])
        original_response = original_data.get("response", "")

        if not original_messages:
            return convert_resp(code=400, status=400, message="No messages found in history file")

        # Replace prompts with custom ones
        new_messages = []
        for msg in original_messages:
            if msg.get("role") == "system" and request.custom_prompts.get("system"):
                new_messages.append({"role": "system", "content": request.custom_prompts["system"]})
            elif msg.get("role") == "user" and request.custom_prompts.get("user"):
                # For user messages, we might want to keep the data but replace the template
                # This is tricky as user messages contain actual data, not just template
                # For now, we'll keep the original user message as it contains real data
                new_messages.append(msg)
            else:
                new_messages.append(msg)

        # Generate new response
        from opencontext.llm.global_vlm_client import generate_with_messages

        response = generate_with_messages(new_messages)
        # Return comparison data
        comparison_data = {
            "original_result": original_response,
            "new_result": response,
            "custom_prompts": request.custom_prompts,
            "timestamp": original_data.get("timestamp", ""),
            "category": request.category,
        }

        return convert_resp(data=comparison_data)

    except Exception as e:
        logger.exception(f"Failed to regenerate with custom prompts: {e}")
        return convert_resp(code=500, status=500, message=f"Failed to regenerate: {str(e)}")
