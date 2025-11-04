# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
OpenContext module: prompt_manager
"""

import os
from typing import Dict

import yaml
from loguru import logger


class PromptManager:
    def __init__(self, prompt_config_path: str = None):
        self.prompts = {}
        self.prompt_config_path = prompt_config_path
        if prompt_config_path and os.path.exists(prompt_config_path):
            with open(prompt_config_path, "r", encoding="utf-8") as f:
                self.prompts = yaml.safe_load(f)
        else:
            logger.warning("Prompt config file not found, using default prompts.")
            raise FileNotFoundError("Prompt config file not found.")

    def get_prompt(self, name: str, default: str = None) -> str:
        keys = name.split(".")
        value = self.prompts
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                logger.warning(f"Prompt '{name}' not found.")
                return default
        return value if isinstance(value, str) else default

    def get_prompt_group(self, name: str) -> Dict[str, str]:
        keys = name.split(".")
        value = self.prompts
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                logger.warning(f"Prompt group '{name}' not found.")
                return {}
        return value if isinstance(value, dict) else {}

    def get_context_type_descriptions(self) -> str:
        """
        Get descriptions of all context types, formatted as a YAML-style string.
        """
        # Use the method in enums to get the descriptions
        from opencontext.models.enums import get_context_type_descriptions_for_prompts

        return get_context_type_descriptions_for_prompts()

    def get_user_prompts_path(self) -> str | None:
        """
        Get the path for user prompts file based on current prompts file
        Returns path like 'config/user_prompts_zh.yaml'
        """
        if not self.prompt_config_path:
            return None

        # Extract language from path (e.g., prompts_zh.yaml -> zh)
        base_name = os.path.basename(self.prompt_config_path)
        if "_" in base_name:
            lang = base_name.split("_")[1].split(".")[0]
            dir_name = os.path.dirname(self.prompt_config_path)
            return os.path.join(dir_name, f"user_prompts_{lang}.yaml")
        return None

    def load_user_prompts(self) -> bool:
        """
        Load user custom prompts and merge them into the prompts dictionary
        """
        user_prompts_path = self.get_user_prompts_path()
        if not user_prompts_path or not os.path.exists(user_prompts_path):
            logger.debug(f"User prompts file does not exist: {user_prompts_path}")
            return False

        try:
            with open(user_prompts_path, "r", encoding="utf-8") as f:
                user_prompts = yaml.safe_load(f)

            if not user_prompts:
                return False

            # Deep merge user prompts into current prompts
            self.prompts = self._deep_merge(self.prompts, user_prompts)
            logger.info(f"User prompts loaded from: {user_prompts_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load user prompts: {e}")
            return False

    def save_prompts(self, prompts_data: dict) -> bool:
        """
        Save prompts to user_prompts file with proper multi-line formatting
        """
        user_prompts_path = self.get_user_prompts_path()
        if not user_prompts_path:
            logger.error("Cannot determine user prompts path")
            return False

        try:
            # Create directory if it doesn't exist
            dir_name = os.path.dirname(user_prompts_path)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)

            # Create a custom dumper class with proper string representation
            class LiteralDumper(yaml.SafeDumper):
                pass

            def str_representer(dumper, data):
                # Check if string has newlines or is long (>80 chars)
                if "\n" in data or len(data) > 80:
                    # Use literal style (|) for multi-line strings
                    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
                # Use plain style for short single-line strings
                return dumper.represent_scalar("tag:yaml.org,2002:str", data)

            # Add the representer to our custom dumper
            LiteralDumper.add_representer(str, str_representer)

            # Save prompts to file using custom dumper
            with open(user_prompts_path, "w", encoding="utf-8") as f:
                yaml.dump(
                    prompts_data,
                    f,
                    Dumper=LiteralDumper,
                    default_flow_style=False,
                    sort_keys=False,
                    allow_unicode=True,
                    width=float("inf"),  # Prevent line wrapping
                )

            logger.info(f"Prompts saved to: {user_prompts_path}")

            # Update current prompts
            self.prompts = self._deep_merge(self.prompts, prompts_data)
            return True
        except Exception as e:
            logger.error(f"Failed to save prompts: {e}")
            return False

    def export_prompts(self) -> str:
        """
        Export current prompts as YAML string
        """
        try:
            return yaml.dump(
                self.prompts, default_flow_style=False, sort_keys=False, allow_unicode=True
            )
        except Exception as e:
            logger.error(f"Failed to export prompts: {e}")
            return ""

    def import_prompts(self, yaml_content: str) -> bool:
        """
        Import prompts from YAML string and save to user_prompts file
        """
        try:
            imported_prompts = yaml.safe_load(yaml_content)
            if not isinstance(imported_prompts, dict):
                logger.error("Imported content is not a valid YAML dictionary")
                return False

            return self.save_prompts(imported_prompts)
        except Exception as e:
            logger.error(f"Failed to import prompts: {e}")
            return False

    def reset_user_prompts(self) -> bool:
        """
        Delete user prompts file to reset to defaults
        """
        user_prompts_path = self.get_user_prompts_path()
        if not user_prompts_path:
            logger.error("Cannot determine user prompts path")
            return False

        try:
            if os.path.exists(user_prompts_path):
                os.remove(user_prompts_path)
                logger.info(f"User prompts file deleted: {user_prompts_path}")

            # Reload prompts from base file
            if self.prompt_config_path and os.path.exists(self.prompt_config_path):
                with open(self.prompt_config_path, "r", encoding="utf-8") as f:
                    self.prompts = yaml.safe_load(f)

            return True
        except Exception as e:
            logger.error(f"Failed to reset user prompts: {e}")
            return False

    def _deep_merge(self, base: dict, override: dict) -> dict:
        """
        Deep merge two dictionaries
        """
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def get_context_type_descriptions_for_retrieval(self) -> str:
        """
        Get context type descriptions for retrieval scenarios
        """
        from opencontext.models.enums import get_context_type_descriptions_for_retrieval

        return get_context_type_descriptions_for_retrieval()
