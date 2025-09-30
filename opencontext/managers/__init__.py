#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0


"""
上下文管理器模块，包含系统各个组件的管理器类
"""

from opencontext.managers.capture_manager import ContextCaptureManager
from opencontext.managers.processor_manager import ContextProcessorManager
from opencontext.managers.consumption_manager import ConsumptionManager

__all__ = [
    'ContextCaptureManager',
    'ContextProcessorManager',
    'ConsumptionManager',
]