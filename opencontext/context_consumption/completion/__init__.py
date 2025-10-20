#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Context Consumption - Completion Module
智能补全模块
"""

from .completion_cache import CompletionCache, get_completion_cache
from .completion_service import CompletionService, get_completion_service

__all__ = ["CompletionService", "get_completion_service", "CompletionCache", "get_completion_cache"]
