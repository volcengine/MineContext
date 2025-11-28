#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Document upload API routes
Follows the architecture of screenshots.py, managed through OpenContext class
"""

from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from opencontext.server.middleware.auth import auth_dependency
from opencontext.server.opencontext import OpenContext
from opencontext.server.utils import convert_resp, get_context_lab
from opencontext.utils.logging_utils import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["documents"])


class UploadDocumentRequest(BaseModel):
    """Document upload request (local path)"""

    file_path: str


class UploadWebLinkRequest(BaseModel):
    """Web link upload request"""

    url: str
    filename_hint: Optional[str] = None


@router.post("/api/documents/upload", response_class=JSONResponse)
async def upload_document(
    request: UploadDocumentRequest,
    opencontext: OpenContext = Depends(get_context_lab),
    _auth: str = auth_dependency,
):
    """
    Upload a single document (local path)

    Add document to processing queue via OpenContext.add_document()
    """
    try:
        err_msg = opencontext.add_document(
            file_path=request.file_path,
        )
        if err_msg:
            return convert_resp(code=400, status=400, message=err_msg)
        return convert_resp(message="Document queued for processing successfully")
    except Exception as e:
        logger.exception(f"Error adding document: {e}")
        return convert_resp(code=500, status=500, message="Internal server error")


@router.post("/api/weblinks/upload", response_class=JSONResponse)
async def upload_weblink(
    request: UploadWebLinkRequest,
    opencontext: OpenContext = Depends(get_context_lab),
    _auth: str = auth_dependency,
):
    """
    Submit a web link to be converted to PDF and processed.
    If the capture component is not initialized via config, initialize it lazily with defaults.
    """
    try:
        capture_manager = opencontext.capture_manager
        component = capture_manager.get_component("web_link_capture")
        if component is None:
            from opencontext.context_capture.web_link_capture import WebLinkCapture

            component = WebLinkCapture()
            default_config = {
                "enabled": True,
                "auto_capture": True,
                "capture_interval": 1.0,
                "output_dir": "uploads/weblinks",
            }
            capture_manager.register_component("web_link_capture", component)
            capture_manager.initialize_component("web_link_capture", default_config)
            capture_manager.start_component("web_link_capture")

        ok = component.submit_url(request.url, request.filename_hint)
        if not ok:
            return convert_resp(code=400, status=400, message="Failed to queue URL")

        # Optionally trigger immediate capture once to speed up
        component.capture()

        return convert_resp(message="Web link queued for processing successfully")
    except Exception as e:
        logger.exception(f"Error queuing web link: {e}")
        return convert_resp(code=500, status=500, message="Internal server error")
