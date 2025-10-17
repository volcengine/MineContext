# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Common utilities for API routes
"""

import json
from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from opencontext.server.opencontext import OpenContext
from opencontext.utils.json_encoder import CustomJSONEncoder


def get_context_lab(request: Request) -> OpenContext:
    """Dependency to get OpenContext instance"""
    context_lab_instance = getattr(request.app.state, "context_lab_instance", None)
    if not context_lab_instance:
        raise HTTPException(status_code=500, detail="OpenContext instance not initialized")
    return context_lab_instance


def convert_resp(data: Any = None, code: int = 0, status: int = 200, message: str = "success"):
    """Convert response to standard JSON format"""
    content = {
        "code": code,
        "status": status,
        "message": message,
    }
    if data is not None:
        content["data"] = data

    # Use CustomJSONEncoder to handle datetime and other special types
    json_content = json.dumps(content, cls=CustomJSONEncoder)
    return JSONResponse(status_code=status, content=json.loads(json_content))
