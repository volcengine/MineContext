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
