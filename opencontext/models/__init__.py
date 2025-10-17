# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
数据模型模块 - 定义系统中使用的数据结构
"""

from opencontext.models.context import (
    ContextProperties,
    ExtractedData,
    ProcessedContext,
    RawContextProperties,
)
from opencontext.models.enums import ContentFormat, ContextSource

__all__ = [
    "RawContextProperties",
    "ProcessedContext",
    "ExtractedData",
    "ContextProperties",
    "ContextSource",
    "ContentFormat",
]
