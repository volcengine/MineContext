# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Context capture module - responsible for capturing context information from various sources
"""

from opencontext.context_capture.base import BaseCaptureComponent
from opencontext.context_capture.screenshot import ScreenshotCapture
from opencontext.context_capture.vault_document_monitor import VaultDocumentMonitor


__all__ = [
    "BaseCaptureComponent",
    "ScreenshotCapture",
    "VaultDocumentMonitor",
]
