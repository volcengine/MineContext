# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Screenshot management routes
"""

from typing import List
from pydantic import BaseModel
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from opencontext.server.opencontext import OpenContext
from opencontext.utils.logging_utils import get_logger
from opencontext.server.utils import get_context_lab, convert_resp
from opencontext.server.middleware.auth import auth_dependency

logger = get_logger(__name__)
router = APIRouter(tags=["screenshots"])


class AddScreenshotRequest(BaseModel):
    path: str
    window: str
    create_time: str
    source: str = "unknown"


class AddScreenshotsRequest(BaseModel):
    screenshots: List[AddScreenshotRequest]


@router.post("/api/add_screenshot", response_class=JSONResponse)
async def add_screenshot(
    request: AddScreenshotRequest,
    opencontext: OpenContext = Depends(get_context_lab),
    _auth: str = auth_dependency
):
    try:
        err_msg = opencontext.add_screenshot(request.path, request.window, request.create_time, request.source)
        if err_msg:
            return convert_resp(code=400, status=400, message=err_msg)
        return convert_resp(message="Screenshot added successfully")
    except Exception as e:
        logger.exception(f"Error adding screenshot: {e}")
    return convert_resp(code=500, status=500, message="Internal server error")


@router.post("/api/add_screenshots", response_class=JSONResponse)
async def add_screenshots(
    request: AddScreenshotsRequest,
    opencontext: OpenContext = Depends(get_context_lab),
    _auth: str = auth_dependency
):
    try:
        for screenshot in request.screenshots:
            err_msg = opencontext.add_screenshot(screenshot.path, screenshot.window, screenshot.create_time, screenshot.source)
            if err_msg:
                return convert_resp(code=400, status=400, message=err_msg)
        return convert_resp(message="Screenshots added successfully")
    except Exception as e:
        logger.exception(f"Error adding screenshots: {e}")
    return convert_resp(code=500, status=500, message="Internal server error")