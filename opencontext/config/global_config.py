#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Global configuration manager, providing a unified interface for accessing configurations and prompts
"""

import os
import threading
from pathlib import Path
from typing import Any, Dict, Optional

from opencontext.config.config_manager import ConfigManager
from opencontext.config.prompt_manager import PromptManager
from opencontext.utils.logging_utils import get_logger

logger = get_logger(__name__)


class GlobalConfig:
    """
    Global Configuration Manager (Singleton Pattern)

    Provides a unified interface for accessing configurations and prompts, avoiding the need to pass configuration objects between components.
    All components can access the configuration via GlobalConfig.get_instance().
    """

    _instance = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls):
        """Ensure singleton pattern"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the global configuration manager"""
        if not self._initialized:
            with self._lock:
                if not self._initialized:
                    self._config_manager: Optional[ConfigManager] = None
                    self._prompt_manager: Optional[PromptManager] = None
                    self._config_path: Optional[str] = None
                    self._prompt_path: Optional[str] = None
                    self._auto_initialized = False
                    GlobalConfig._initialized = True

    @classmethod
    def get_instance(cls) -> "GlobalConfig":
        """
        Get the global configuration manager instance
        """
        instance = cls()
        # If not yet initialized, try to auto-initialize
        if not instance._auto_initialized and instance._config_manager is None:
            instance._auto_initialize()
        return instance

    @classmethod
    def reset(cls):
        """Reset the singleton instance (mainly for testing)"""
        with cls._lock:
            cls._instance = None
            cls._initialized = False

    def _auto_initialize(self):
        """Automatically initialize the configuration"""
        if self._auto_initialized:
            return

        try:
            # Try to load the configuration automatically
            self._initialized = self.initialize("config/config.yaml")
            if not self._initialized:
                logger.error(
                    "GlobalConfig auto-initialization: no config file found, using defaults"
                )
            self._auto_initialized = True
        except Exception as e:
            logger.error(f"GlobalConfig auto-initialization failed: {e}")
            self._auto_initialized = True  # Prevent repeated attempts

    def initialize(self, config_path: Optional[str] = None) -> bool:
        """
        Initialize the configuration and prompt managers
        """
        success = True

        # Initialize the configuration manager
        if self._config_manager is None:
            self._config_manager = ConfigManager()
            config_loaded = self._config_manager.load_config(config_path)
            if config_loaded:
                self._config_path = self._config_manager.get_config_path()
                logger.info(f"Config loaded from: {self._config_path}")
            else:
                logger.warning("Using default configuration")
                success = False

        # Initialize the prompt manager
        if self._prompt_manager is None:
            if not self._init_prompt_manager():
                success = False

        return success

    def _init_prompt_manager(self) -> bool:
        """
        Initialize the prompt manager
        """
        if not self._config_manager:
            logger.warning("Config manager not initialized, cannot load prompts")
            return False

        config = self._config_manager.get_config()
        if not config:
            logger.warning("No configuration available for prompts")
            return False

        # Get prompt configuration from the main configuration
        prompts_config = config.get("prompts", {})
        language = prompts_config.get("language", "zh")
        prompts_path = f"prompts_{language}.yaml"

        base_dir = os.path.dirname(self._config_path)
        absolute_prompts_path = os.path.join(base_dir, prompts_path)

        if not os.path.exists(absolute_prompts_path):
            logger.warning(f"Prompt file not found: {absolute_prompts_path}")
            return False

        try:
            self._prompt_manager = PromptManager(absolute_prompts_path)
            self._prompt_path = absolute_prompts_path
            self._language = language
            logger.info(f"Prompts loaded from: {self._prompt_path} (language: {language})")

            # Load user prompts if available
            self._prompt_manager.load_user_prompts()

            return True
        except Exception as e:
            logger.error(f"Failed to load prompts: {e}")
            return False

    def set_config_manager(self, config_manager: ConfigManager):
        """
        Set the configuration manager (for backward compatibility)
        """
        self._config_manager = config_manager
        if config_manager:
            self._config_path = config_manager.get_config_path()

    def set_prompt_manager(self, prompt_manager: PromptManager):
        """
        Set the prompt manager (for backward compatibility)
        """
        self._prompt_manager = prompt_manager

    def get_config_manager(self) -> Optional[ConfigManager]:
        """
        Get the configuration manager instance
        """
        return self._config_manager

    def get_prompt_manager(self) -> Optional[PromptManager]:
        """
        Get the prompt manager instance
        """
        return self._prompt_manager

    def get_language(self) -> str:
        """
        Get the current language setting
        """
        if hasattr(self, "_language"):
            return self._language
        return "zh"

    def set_language(self, language: str) -> bool:
        """
        Set the current language and reload prompts

        Args:
            language: Language code ('zh' or 'en')

        Returns:
            bool: True if successful, False otherwise
        """
        if language not in ["zh", "en"]:
            logger.error(f"Invalid language: {language}")
            return False

        try:
            # Update language in memory
            self._language = language

            # Save to user settings
            if self._config_manager:
                settings = {"prompts": {"language": language}}
                if not self._config_manager.save_user_settings(settings):
                    logger.error("Failed to save language setting")
                    return False

                # Reload config to pick up the new language setting
                self._config_manager.load_config(self._config_path)

            # Reload prompt manager with new language
            prompts_path = f"prompts_{language}.yaml"
            base_dir = os.path.dirname(self._config_path)
            absolute_prompts_path = os.path.join(base_dir, prompts_path)

            if not os.path.exists(absolute_prompts_path):
                logger.error(f"Prompt file not found: {absolute_prompts_path}")
                return False

            self._prompt_manager = PromptManager(absolute_prompts_path)
            self._prompt_path = absolute_prompts_path
            logger.info(f"Prompts reloaded from: {self._prompt_path} (language: {language})")

            # Load user prompts if available
            self._prompt_manager.load_user_prompts()

            return True
        except Exception as e:
            logger.error(f"Failed to set language: {e}")
            return False

    def get_config(self, path: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get configuration
        """
        if not self._config_manager:
            logger.warning("Config manager not initialized")
            return None

        config = self._config_manager.get_config()
        if not config:
            return None

        if not path:
            return config

        # Get configuration by path
        keys = path.split(".")
        value = config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                logger.debug(f"Config path '{path}' not found")
                return None

        return value

    def get_prompt(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get a prompt
        """
        if not self._prompt_manager:
            logger.warning("Prompt manager not initialized")
            return default

        return self._prompt_manager.get_prompt(name, default)

    def get_prompt_group(self, name: str) -> Dict[str, str]:
        """
        Get a prompt group
        """
        if not self._prompt_manager:
            logger.warning("Prompt manager not initialized")
            return {}

        return self._prompt_manager.get_prompt_group(name)

    def is_enabled(self, module: str) -> bool:
        """
        Check if a module is enabled
        """
        config = self.get_config(module)
        if isinstance(config, dict):
            return config.get("enabled", False)
        return False

    def is_initialized(self) -> bool:
        """Check if the global configuration is initialized"""
        return self._initialized


# Convenience functions
def get_global_config() -> GlobalConfig:
    """Convenience function to get the global config instance"""
    return GlobalConfig.get_instance()


def get_config(path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Convenience function to get a configuration value"""
    return GlobalConfig.get_instance().get_config(path)


def get_language() -> str:
    """Convenience function to get the current language setting"""
    return GlobalConfig.get_instance().get_language()


def get_prompt(name: str, default: Optional[str] = None) -> Optional[str]:
    """Convenience function to get a prompt"""
    return GlobalConfig.get_instance().get_prompt(name, default)


def get_prompt_group(name: str) -> Dict[str, str]:
    """Convenience function to get a prompt group"""
    return GlobalConfig.get_instance().get_prompt_group(name)


def get_prompt_manager() -> PromptManager:
    """Convenience function to get the prompt manager"""
    return GlobalConfig.get_instance()._prompt_manager


def is_initialized() -> bool:
    """Check if the global configuration is initialized"""
    return GlobalConfig.get_instance().is_initialized()
