# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Web interface routes
"""

from pathlib import Path
from typing import Optional
import datetime

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates

from context_lab.server.context_lab import ContextLab
from context_lab.models.context import ProcessedContextModel
from context_lab.server.utils import get_context_lab
from context_lab.storage.global_storage import get_storage
from context_lab.server.middleware.auth import auth_dependency


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
    context_lab: ContextLab = Depends(get_context_lab)
):
    offset = (page - 1) * limit
    types = []
    if type:
        types.append(type)
    contexts_dict = get_storage().get_all_processed_contexts(context_types=list(types), limit=limit+1, offset=offset, need_vector=False)
    contexts = []
    for backend_contexts in contexts_dict.values():
        contexts.extend(backend_contexts)
    contexts.sort(key=lambda x: x.properties.create_time, reverse=True)
    has_next = len(contexts) > limit
    contexts_to_display = contexts[:limit]
    
    context_types = get_storage().get_available_context_types()
    
    return templates.TemplateResponse("contexts.html", {
        "request": request,
        "contexts": [ProcessedContextModel.from_processed_context(c, project_root) for c in contexts_to_display],
        "page": page,
        "limit": limit,
        "type": type,
        "context_types": context_types,
        "has_next": has_next,
        "has_prev": page > 1,
    })


@router.get("/vector_search", response_class=HTMLResponse)
async def vector_search_page(request: Request):
    return templates.TemplateResponse("vector_search.html", {"request": request})


@router.get("/debug", response_class=HTMLResponse)
async def debug_page(request: Request):
    return templates.TemplateResponse("debug.html", {"request": request})


@router.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    """AI 聊天界面 - 重定向到高级聊天"""
    return RedirectResponse(url="/advanced_chat")


@router.get("/advanced_chat", response_class=HTMLResponse)
async def advanced_chat_page(request: Request):
    """高级AI聊天界面 - 重定向到AI文档协作"""
    return RedirectResponse(url="/vaults")


@router.get("/files/{file_path:path}")
async def serve_file(file_path: str, _auth: str = auth_dependency):
    # 安全检查：阻止访问敏感目录
    sensitive_paths = [
        'config/', '.env', '.git/', 'context_lab/', 
        '__pycache__/', '.pytest_cache/', 'logs/',
        'private/', 'secret', 'password', 'key'
    ]
    
    # 检查是否访问敏感路径
    file_path_lower = file_path.lower()
    for sensitive in sensitive_paths:
        if file_path_lower.startswith(sensitive.lower()) or sensitive.lower() in file_path_lower:
            raise HTTPException(status_code=403, detail="Access to sensitive files is forbidden")
    
    # 仅允许访问特定的安全目录
    allowed_prefixes = [
        'screenshots/', 'static/', 'uploads/', 'public/',
        'docs/', 'examples/', 'templates/public/'
    ]
    
    if not any(file_path.startswith(prefix) for prefix in allowed_prefixes):
        raise HTTPException(status_code=403, detail="Access forbidden: file is outside allowed directories")
    
    full_path = (project_root / file_path).resolve()
    if not str(full_path).startswith(str(project_root)):
        raise HTTPException(status_code=403, detail="Access forbidden: file is outside the project directory.")
    if not full_path.is_file():
        from context_lab.utils.logging_utils import get_logger
        logger = get_logger(__name__)
        logger.error(f"File not found at: {full_path}")
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(str(full_path))


@router.get("/monitoring", response_class=HTMLResponse)
async def monitoring_page(request: Request):
    """监控页面"""
    return templates.TemplateResponse("monitoring.html", {"request": request})


@router.get("/assistant", response_class=HTMLResponse)
async def assistant_page(request: Request):
    """智能助手页面"""
    return templates.TemplateResponse("assistant.html", {
        "request": request,
        "title": "智能助手"
    })


