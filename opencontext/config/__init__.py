# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
配置模块 - 负责加载和管理配置
"""

from opencontext.config.config_manager import ConfigManager
from opencontext.config.global_config import GlobalConfig, get_config, get_global_config, get_prompt
from opencontext.config.prompt_manager import PromptManager

__all__ = [
    "ConfigManager",
    "PromptManager",
    "GlobalConfig",
    "get_global_config",
    "get_config",
    "get_prompt",
]
