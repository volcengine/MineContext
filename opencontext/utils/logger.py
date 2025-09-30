#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0


"""
Log manager for configuring and managing logging
"""

import os
import sys
from typing import Any, Dict

from loguru import logger


class LogManager:
    """
    Log manager
    
    Configures and manages logging
    """
    
    def __init__(self):
        """Initialize log manager"""
        # Remove default handlers
        logger.remove()
    
    def configure(self, config: Dict[str, Any]) -> None:
        """
        Configure logging
        
        Args:
            config (Dict[str, Any]): Logging configuration
        """
        # Get log level
        level = config.get("level", "INFO")
        
        # Configure console logging
        console_config = config.get("console", {})
        if console_config.get("enabled", True):
            console_format = console_config.get(
                "format",
                "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <cyan>{message}</cyan>"
            )
            logger.add(sys.stderr, level=level, format=console_format)
        
        # Configure file logging
        file_config = config.get("file", {})
        if file_config.get("enabled", True):
            file_path = file_config.get("path", "logs/opencontext.log")
            
            # Create log directory if it doesn't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            file_format = file_config.get(
                "format",
                "{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
            )
            rotation = file_config.get("rotation", "500 MB")
            retention = file_config.get("retention", "10 days")
            
            logger.add(
                file_path,
                level=level,
                format=file_format,
                rotation=rotation,
                retention=retention,
                encoding="utf-8"
            )
        
    
    def get_logger(self):
        """
        Get logger instance
        
        Returns:
            Logger: Logger instance
        """
        return logger


# Create global log manager instance
log_manager = LogManager()

# Export logger for use by other modules
log = logger