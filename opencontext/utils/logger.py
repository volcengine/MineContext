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
        level = config.get("level", "INFO")

        # Console logging
        console_format = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <cyan>{message}</cyan>"
        logger.add(sys.stderr, level=level, format=console_format)

        # File logging
        log_path = config.get("log_path")
        if log_path:
            log_dir = os.path.dirname(log_path)
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)

            # Add date to log filename: opentext_2025-10-13.log
            # When rotated, it becomes: opentext_2025-10-13.log.2025-10-13_14-30-00
            base_name = os.path.basename(log_path)
            name_without_ext = os.path.splitext(base_name)[0]
            ext = os.path.splitext(base_name)[1]
            dated_log_path = os.path.join(log_dir, f"{name_without_ext}_{{time:YYYY-MM-DD}}{ext}")

            file_format = "{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
            rotation = "100 MB"
            retention = 2  # Keep only the 2 most recent files

            logger.add(
                dated_log_path,
                level=level,
                format=file_format,
                rotation=rotation,
                retention=retention,
                encoding="utf-8",
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
