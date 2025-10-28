#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0


"""
Configuration manager, responsible for loading and managing system configurations
"""

import logging
import os
import re
from typing import Any, Dict, Optional

import yaml

from opencontext.utils.logging_utils import get_logger

logger = get_logger(__name__)


class ConfigManager:
    """
    Configuration Manager

    Responsible for loading and managing system configurations
    """

    def __init__(self):
        """Initialize the configuration manager"""
        self._config: Optional[Dict[str, Any]] = None
        self._config_path: Optional[str] = None
        self._env_vars: Dict[str, str] = {}

    def load_config(self, config_path: Optional[str] = None) -> bool:
        """
        Load configuration
        """
        found_config_path = None

        if not config_path:
            config_path = "config/config.yaml"
        if config_path and os.path.exists(config_path):
            found_config_path = config_path
        else:
            raise FileNotFoundError(f"Specified configuration file does not exist: {config_path}")

        with open(found_config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)

        self._load_env_vars()
        config_data = self._replace_env_vars(config_data)
        self._config = config_data
        self._config_path = found_config_path
        logger.info(f"Configuration loaded successfully: {self._config_path}")
        self.load_user_settings()

        return True

    def _load_env_vars(self) -> None:
        """Load environment variables"""
        for key, value in os.environ.items():
            self._env_vars[key] = value

    def _replace_env_vars(self, config_data: Any) -> Any:
        """
        Replace environment variable references in the configuration

        Supported formats:
        - ${VAR}: Simple variable substitution
        - ${VAR:default}: Use default value if the variable does not exist

        Args:
            config_data (Any): Configuration data

        Returns:
            Any: Configuration data after replacement
        """
        if isinstance(config_data, dict):
            return {k: self._replace_env_vars(v) for k, v in config_data.items()}
        elif isinstance(config_data, list):
            return [self._replace_env_vars(item) for item in config_data]
        elif isinstance(config_data, str):
            # Match environment variables in the format ${VAR} or ${VAR:default}
            pattern = r"\$\{([^}:]+)(?::([^}]*))?\}"

            def replace_match(match):
                var_name = match.group(1)
                default_value = match.group(2) if match.group(2) is not None else ""

                env_value = self._env_vars.get(var_name)

                # ${VAR:default}: Use default value if the variable does not exist
                return env_value if env_value is not None else default_value

            return re.sub(pattern, replace_match, config_data)
        else:
            return config_data

    def get_config(self) -> Optional[Dict[str, Any]]:
        """
        Get configuration

        Returns:
            Optional[Dict[str, Any]]: Configuration dictionary, or None if not loaded
        """
        return self._config

    def get_config_path(self) -> Optional[str]:
        """
        Get configuration file path

        Returns:
            Optional[str]: Configuration file path, or None if not loaded
        """
        return self._config_path

    def deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deep merge two dictionaries

        Args:
            base: Base configuration
            override: Configuration to override with

        Returns:
            Merged configuration
        """
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # Recursively merge dictionaries
                result[key] = self.deep_merge(result[key], value)
            else:
                # Directly override
                result[key] = value

        return result

    def load_user_settings(self) -> bool:
        """
        Load user settings and merge them into the main configuration
        """
        if not self._config:
            return False
        user_setting_path = self._config.get("user_setting_path")
        if not user_setting_path:
            return False
        if not os.path.exists(user_setting_path):
            logger.info(f"User settings file does not exist, skipping: {user_setting_path}")
            return False

        try:
            with open(user_setting_path, "r", encoding="utf-8") as f:
                user_settings = yaml.safe_load(f)
            if not user_settings:
                return False
            self._config = self.deep_merge(self._config, user_settings)
            # logger.info(f"User settings loaded successfully: {user_settings}")
            return True
        except Exception as e:
            logger.error(f"Failed to load user settings: {e}")
            return False

    def save_user_settings(self, settings: Dict[str, Any]) -> bool:
        """
        Save user settings to a separate file
        """
        if not self._config:
            logger.error("Main configuration not loaded")
            return False

        # Get user settings path
        user_setting_path = self._config.get("user_setting_path")
        if not user_setting_path:
            logger.error("user_setting_path not configured")
            return False
        try:
            dir_name = os.path.dirname(user_setting_path)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)

            # Load existing user settings
            user_settings = {}
            if os.path.exists(user_setting_path):
                with open(user_setting_path, "r", encoding="utf-8") as f:
                    existing_settings = yaml.safe_load(f)
                    if existing_settings:
                        user_settings = existing_settings

            # Update with new settings
            if "vlm_model" in settings:
                user_settings["vlm_model"] = settings["vlm_model"]
            if "embedding_model" in settings:
                user_settings["embedding_model"] = settings["embedding_model"]
            if "content_generation" in settings:
                user_settings["content_generation"] = settings["content_generation"]
            if "capture" in settings:
                user_settings["capture"] = settings["capture"]
            if "processing" in settings:
                user_settings["processing"] = settings["processing"]
            if "logging" in settings:
                user_settings["logging"] = settings["logging"]
            if "prompts" in settings:
                user_settings["prompts"] = settings["prompts"]

            # Save to file
            with open(user_setting_path, "w", encoding="utf-8") as f:
                yaml.dump(
                    user_settings, f, default_flow_style=False, sort_keys=False, allow_unicode=True
                )

            logger.info(f"User settings saved successfully: {user_setting_path}")

            # Merge into current config
            self._config = self.deep_merge(self._config, user_settings)
            return True
        except Exception as e:
            logger.error(f"Failed to save user settings: {e}")
            return False

    def reset_user_settings(self) -> bool:
        """
        Reset user settings by deleting the user_setting.yaml file
        """
        if not self._config:
            logger.error("Main configuration not loaded")
            return False

        user_setting_path = self._config.get("user_setting_path")
        if not user_setting_path:
            logger.error("user_setting_path not configured")
            return False

        try:
            if os.path.exists(user_setting_path):
                os.remove(user_setting_path)
                logger.info(f"User settings file deleted: {user_setting_path}")
            else:
                logger.info(f"User settings file does not exist: {user_setting_path}")

            # Reload config to apply defaults
            if self._config_path:
                self.load_config(self._config_path)

            return True
        except Exception as e:
            logger.error(f"Failed to reset user settings: {e}")
            return False
