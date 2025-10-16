#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0


"""
Context interface module containing interface definitions for system components
"""

from opencontext.interfaces.capture_interface import ICaptureComponent
from opencontext.interfaces.processor_interface import IContextProcessor
from opencontext.interfaces.storage_interface import IContextStorage

__all__ = [
    "ICaptureComponent",
    "IContextProcessor",
    "IContextStorage",
]
