# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
数据模型模块 - 定义系统中使用的数据结构
"""

from opencontext.models.enums import (
    ContextSource,
    ContentFormat,
)
from opencontext.models.context import (
    RawContextProperties,
    ProcessedContext,
    ExtractedData,
    ContextProperties,
)

__all__ = [
    "RawContextProperties",
    "ProcessedContext",
    "ExtractedData",
    "ContextProperties",
    "ContextSource",
    "ContentFormat",
]