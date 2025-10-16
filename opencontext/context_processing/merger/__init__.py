#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Merger module for context processing.
Contains merge-related functionality including context merging, strategies, and cross-type relationships.
"""

from .context_merger import ContextMerger
from .cross_type_relationships import CrossTypeRelationshipManager
from .merge_strategies import (
    ActivityContextStrategy,
    ContextTypeAwareStrategy,
    IntentContextStrategy,
    ProceduralContextStrategy,
    ProfileContextStrategy,
    SemanticContextStrategy,
    StateContextStrategy,
    StrategyFactory,
)

__all__ = [
    "ContextMerger",
    "ContextTypeAwareStrategy",
    "ProfileContextStrategy",
    "ActivityContextStrategy",
    "StateContextStrategy",
    "IntentContextStrategy",
    "SemanticContextStrategy",
    "ProceduralContextStrategy",
    "StrategyFactory",
    "CrossTypeRelationshipManager",
]
