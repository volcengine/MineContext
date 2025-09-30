# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Server component: api - Main router configuration
"""

from pathlib import Path

from fastapi import APIRouter

from opencontext.utils.logging_utils import get_logger

# Import route modules
from .routes import health, web, context, content_generation, screenshots, debug, monitoring, vaults, agent_chat, completions, events, settings

logger = get_logger(__name__)

router = APIRouter()

project_root = Path(__file__).parent.parent.parent.resolve()


# Include all route modules
router.include_router(health.router)
router.include_router(web.router)
router.include_router(context.router)
router.include_router(content_generation.router)
router.include_router(screenshots.router)
router.include_router(debug.router)
router.include_router(monitoring.router)
router.include_router(vaults.router)
router.include_router(agent_chat.router)
router.include_router(completions.router)
router.include_router(events.router)
router.include_router(settings.router)
