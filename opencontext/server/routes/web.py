# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Web interface routes
"""

import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from opencontext.models.context import ProcessedContextModel
from opencontext.server.middleware.auth import auth_dependency
from opencontext.server.opencontext import OpenContext
from opencontext.server.utils import get_context_lab
from opencontext.storage.global_storage import get_storage

router = APIRouter(tags=["web"])

project_root = Path(__file__).parent.parent.parent.parent.resolve()
templates_path = Path(__file__).parent.parent.parent / "web" / "templates"
templates = Jinja2Templates(directory=templates_path)


@router.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/contexts")


@router.get("/contexts", response_class=HTMLResponse)
async def read_contexts(
    request: Request,
    page: int = 1,
    limit: int = 15,
    type: Optional[str] = None,
    opencontext: OpenContext = Depends(get_context_lab),
):
    offset = (page - 1) * limit
    types = []
    if type:
        types.append(type)
    contexts_dict = get_storage().get_all_processed_contexts(
        context_types=list(types), limit=limit + 1, offset=offset, need_vector=False
    )
    contexts = []
    for backend_contexts in contexts_dict.values():
        contexts.extend(backend_contexts)

    # Sort with timezone-aware datetime handling
    def get_sort_key(context):
        dt = context.properties.create_time
        # Convert naive datetime to aware (assume UTC if naive)
        if dt.tzinfo is None:
            import datetime as dt_module
            dt = dt.replace(tzinfo=dt_module.timezone.utc)
        return dt

    contexts.sort(key=get_sort_key, reverse=True)
    has_next = len(contexts) > limit
    contexts_to_display = contexts[:limit]

    context_types = get_storage().get_available_context_types()

    return templates.TemplateResponse(
        "contexts.html",
        {
            "request": request,
            "contexts": [
                ProcessedContextModel.from_processed_context(c, project_root)
                for c in contexts_to_display
            ],
            "page": page,
            "limit": limit,
            "type": type,
            "context_types": context_types,
            "has_next": has_next,
            "has_prev": page > 1,
        },
    )


@router.get("/vector_search", response_class=HTMLResponse)
async def vector_search_page(request: Request):
    return templates.TemplateResponse("vector_search.html", {"request": request})


@router.get("/debug", response_class=HTMLResponse)
async def debug_page(request: Request):
    return templates.TemplateResponse("debug.html", {"request": request})


@router.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    """AI chat interface - redirects to advanced chat"""
    return RedirectResponse(url="/advanced_chat")


@router.get("/advanced_chat", response_class=HTMLResponse)
async def advanced_chat_page(request: Request):
    """Advanced AI chat interface - redirects to AI document collaboration"""
    return RedirectResponse(url="/vaults")


@router.get("/files/{file_path:path}")
async def serve_file(file_path: str, _auth: str = auth_dependency):
    # Security check: block access to sensitive directories
    sensitive_paths = [
        "config/",
        ".env",
        ".git/",
        "opencontext/",
        "__pycache__/",
        ".pytest_cache/",
        "logs/",
        "private/",
        "secret",
        "password",
        "key",
    ]

    # Check if accessing sensitive paths
    file_path_lower = file_path.lower()
    for sensitive in sensitive_paths:
        if file_path_lower.startswith(sensitive.lower()) or sensitive.lower() in file_path_lower:
            raise HTTPException(status_code=403, detail="Access to sensitive files is forbidden")

    # Only allow access to specific safe directories
    allowed_prefixes = [
        "screenshots/",
        "static/",
        "uploads/",
        "public/",
        "docs/",
        "examples/",
        "templates/public/",
    ]

    if not any(file_path.startswith(prefix) for prefix in allowed_prefixes):
        raise HTTPException(
            status_code=403, detail="Access forbidden: file is outside allowed directories"
        )

    full_path = (project_root / file_path).resolve()
    if not str(full_path).startswith(str(project_root)):
        raise HTTPException(
            status_code=403, detail="Access forbidden: file is outside the project directory."
        )
    if not full_path.is_file():
        from opencontext.utils.logging_utils import get_logger

        logger = get_logger(__name__)
        logger.error(f"File not found at: {full_path}")
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(str(full_path))


@router.get("/monitoring", response_class=HTMLResponse)
async def monitoring_page(request: Request):
    """Monitoring page"""
    return templates.TemplateResponse("monitoring.html", {"request": request})


@router.get("/assistant", response_class=HTMLResponse)
async def assistant_page(request: Request):
    """Intelligent assistant page"""
    return templates.TemplateResponse(
        "assistant.html", {"request": request, "title": "Intelligent Assistant"}
    )


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """System settings page"""
    return templates.TemplateResponse("settings.html", {"request": request, "title": "系统设置"})
