# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Logging utilities - Provides logging related functionality
"""

from typing import Any, Dict

from opencontext.utils.logger import log, log_manager


def setup_logging(config: Dict[str, Any]):
    """
    Setup logging

    Args:
        config (Dict[str, Any]): Logging configuration
    """
    log_manager.configure(config)
    log.info("Logging setup completed")


def get_logger(name: str):
    """
    Get logger instance
    """
    return log.bind(name=name)
