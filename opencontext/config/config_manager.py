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
from opencontext.utils.logging_utils import get_logger
import yaml

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

        with open(found_config_path, 'r', encoding='utf-8') as f:
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
            pattern = r'\$\{([^}:]+)(?::([^}]*))?\}'
            
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
    
    def save_config(self, config_path: Optional[str] = None) -> bool:
        """
        Save configuration
        
        Args:
            config_path (Optional[str], optional): Configuration file path. If None, the path used for loading will be used.
            
        Returns:
            bool: Whether the save was successful
        """
        if self._config is None:
            logger.error("Configuration not loaded, cannot save")
            return False
        
        if config_path is None:
            if self._config_path is None:
                logger.error("Configuration file path not specified, cannot save")
                return False
            
            config_path = self._config_path
        logger.info(f"Saving configuration to: {config_path}")
        try:
            # Create directory (if it doesn't exist)
            dir_name = os.path.dirname(config_path)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
            
            # Use the configuration dictionary directly
            config_dict = self._config
            
            # Save configuration
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
            
            logger.info(f"Configuration saved successfully: {config_path}")
            return True
        except Exception as e:
            logger.exception(f"Exception while saving configuration: {str(e)}")
            return False
    
    def get_default_config(self) -> Dict[str, Any]:
        """
        Get default configuration
        
        Returns:
            Dict[str, Any]: Default configuration dictionary
        """
        return {
            'capture': {
                'enabled': True,
                'screenshot': {
                    'enabled': True,
                    'interval': 5,
                },
                'file_monitor': {
                    'enabled': True,
                    'paths': ['~/Documents'],
                },
            },
            'processing': {
                'enabled': True,
            },
            'storage': {
                'enabled': True,
            },
            'consumption': {
                'enabled': True,
            },
            'web': {
                'enabled': True,
                'host': '127.0.0.1',
                'port': 8000,
            },
            'logging': {
                'level': 'INFO',
            },
        }
    
    def update_config(self, config: Dict[str, Any]) -> None:
        """
        Update configuration
        
        Args:
            config (Dict[str, Any]): New configuration dictionary
        """
        self._config = config
    
    def get_consumption_config(self) -> Optional[Dict[str, Any]]:
        """
        Get consumption configuration
        
        Returns:
            Optional[Dict[str, Any]]: Consumption configuration, or None if not loaded
        """
        if self._config is None:
            return None
        
        return self._config.get("consumption")
    
    def get_web_config(self) -> Optional[Dict[str, Any]]:
        """
        Get Web UI configuration
        
        Returns:
            Optional[Dict[str, Any]]: Web UI configuration, or None if not loaded
        """
        if self._config is None:
            return None
        
        return self._config.get("web")
    
    def get_logging_config(self) -> Optional[Dict[str, Any]]:
        """
        Get logging configuration
        
        Returns:
            Optional[Dict[str, Any]]: Logging configuration, or None if not loaded
        """
        if self._config is None:
            return None
        
        return self._config.get("logging")
    
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
            with open(user_setting_path, 'r', encoding='utf-8') as f:
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
  
            user_settings = {}
            if "vlm_model" in settings:
                user_settings["vlm_model"] = settings["vlm_model"]
            if "embedding_model" in settings:
                user_settings["embedding_model"] = settings["embedding_model"]
            with open(user_setting_path, 'w', encoding='utf-8') as f:
                yaml.dump(user_settings, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
            logger.info(f"User settings saved successfully: {user_setting_path}")
            self._config = self.deep_merge(self._config, user_settings)
            return True
        except Exception as e:
            logger.error(f"Failed to save user settings: {e}")
            return False