#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Debug Helper - Saves generation messages and responses for debugging prompts.
"""

import datetime
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from opencontext.config.global_config import get_config
from opencontext.utils.logging_utils import get_logger

logger = get_logger(__name__)


class DebugHelper:
    """
    Debug Helper for content generation modules.
    Saves messages and responses to local files when debug mode is enabled.
    """

    @staticmethod
    def is_debug_enabled() -> bool:
        """Check if debug mode is enabled."""
        try:
            config = get_config("content_generation.debug")
            if config and isinstance(config, dict):
                return config.get("enabled", False)
            return False
        except Exception:
            return False

    @staticmethod
    def get_debug_output_path() -> Optional[str]:
        """Get the debug output path from configuration."""
        try:
            config = get_config("content_generation.debug")
            if config and isinstance(config, dict):
                output_path = config.get("output_path", "${CONTEXT_PATH:.}/debug/generation")
                # Expand environment variables
                if "${CONTEXT_PATH" in output_path:
                    context_path = os.getenv("CONTEXT_PATH", ".")
                    output_path = output_path.replace("${CONTEXT_PATH:.}", context_path)
                    output_path = output_path.replace("${CONTEXT_PATH}", context_path)
                return output_path
            return None
        except Exception as e:
            logger.warning(f"Failed to get debug output path: {e}")
            return None

    @staticmethod
    def _serialize_messages(messages: List[Any]) -> List[Dict[str, Any]]:
        """
        Convert messages to JSON-serializable format.
        Handles both dict messages and ChatCompletionMessage objects.
        """
        serialized = []
        for msg in messages:
            if isinstance(msg, dict):
                serialized.append(msg)
            else:
                # Handle ChatCompletionMessage or similar objects
                try:
                    if hasattr(msg, "model_dump"):
                        # Pydantic v2
                        serialized.append(msg.model_dump())
                    elif hasattr(msg, "dict"):
                        # Pydantic v1
                        serialized.append(msg.dict())
                    elif hasattr(msg, "__dict__"):
                        # Generic object
                        serialized.append(msg.__dict__)
                    else:
                        serialized.append(str(msg))
                except Exception as e:
                    logger.debug(f"Failed to serialize message: {e}")
                    serialized.append(str(msg))
        return serialized

    @staticmethod
    def save_generation_debug(
        task_type: str,
        messages: List[Dict[str, Any]],
        response: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Save generation debug information to a file.

        Args:
            task_type: Type of generation task (todo, tips, activity, report)
            messages: Messages sent to the LLM
            response: Response from the LLM (optional, if None, file won't be saved)
            metadata: Additional metadata to save (optional)

        Returns:
            bool: True if saved successfully, False otherwise
        """
        # Check if debug mode is enabled
        if not DebugHelper.is_debug_enabled():
            return False

        # Don't save if there's no response
        if response is None:
            logger.debug(f"No response to save for {task_type}, skipping debug output")
            return False

        try:
            # Get output path
            base_path = DebugHelper.get_debug_output_path()
            if not base_path:
                logger.warning("Debug output path not configured")
                return False

            # Create directory structure: {base_path}/{task_type}/
            output_dir = Path(base_path) / task_type
            output_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename with timestamp
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"{timestamp}.json"
            filepath = output_dir / filename

            # Serialize messages to handle both dict and object types
            serialized_messages = DebugHelper._serialize_messages(messages)

            # Prepare debug data
            debug_data = {
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "task_type": task_type,
                "messages": serialized_messages,
                "response": response,
            }

            # Add metadata if provided
            if metadata:
                debug_data["metadata"] = metadata

            # Save to file
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(debug_data, f, ensure_ascii=False, indent=2)

            logger.info(f"Debug data saved to: {filepath}")
            return True

        except Exception as e:
            logger.exception(f"Failed to save debug data for {task_type}: {e}")
            return False
