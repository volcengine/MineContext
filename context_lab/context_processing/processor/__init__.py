#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Processor module for context processing.
Contains processor-related functionality including base processor, document processor, 
screenshot processor, and processor factory.
"""

from .base_processor import BaseContextProcessor
from .document_processor import DocumentProcessor
from .screenshot_processor import ScreenshotProcessor
from .processor_factory import ProcessorFactory, processor_factory

__all__ = [
    'BaseContextProcessor',
    'DocumentProcessor',
    'ScreenshotProcessor',
    'ProcessorFactory',
    'processor_factory'
]