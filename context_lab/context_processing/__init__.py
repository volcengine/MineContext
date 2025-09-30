# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Context processing module - Handles processing and transformation of captured context information
"""

from context_lab.context_processing.processor.screenshot_processor import ScreenshotProcessor
from context_lab.context_processing.processor.base_processor import BaseContextProcessor
from context_lab.context_processing.processor.document_processor import DocumentProcessor
from context_lab.context_processing.processor.processor_factory import processor_factory
from context_lab.context_processing.merger.context_merger import ContextMerger


__all__ = [
    "BaseContextProcessor",
    "DocumentProcessor",
    "processor_factory",
    "ScreenshotProcessor",
    "ContextMerger",
]
