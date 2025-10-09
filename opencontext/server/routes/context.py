# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Context management routes
"""

import json
from pathlib import Path
from typing import Any, List, Optional, Dict

from fastapi import APIRouter, Depends, Request, Query, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from opencontext.server.opencontext import OpenContext
from opencontext.models.context import ProcessedContextModel
from opencontext.models.enums import ContextSource, ContentFormat
from opencontext.utils.json_encoder import CustomJSONEncoder
from opencontext.utils.logging_utils import get_logger
from opencontext.server.utils import get_context_lab, convert_resp
from opencontext.server.middleware.auth import auth_dependency

logger = get_logger(__name__)
router = APIRouter(tags=["context"])

project_root = Path(__file__).parent.parent.parent.parent.resolve()
templates_path = Path(__file__).parent.parent.parent / "web" / "templates"
templates = Jinja2Templates(directory=templates_path)


class ContextIn(BaseModel):
    source: ContextSource
    content_format: ContentFormat
    data: Any
    metadata: Optional[dict] = {}
    tags: Optional[List[str]] = []


class UpdateContextIn(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    keywords: Optional[List[str]] = None
    tags: Optional[List[str]] = None


class QueryIn(BaseModel):
    query: str


class ConsumeIn(BaseModel):
    query: str
    context_ids: List[str]


class ContextDetailRequest(BaseModel):
    id: str
    context_type: str


class VectorSearchRequest(BaseModel):
    query: str
    top_k: int = 10
    context_types: Optional[List[str]] = None
    filters: Optional[Dict[str, Any]] = None


@router.post("/contexts/delete")
def delete_context(
    detail_request: ContextDetailRequest,
    opencontext: OpenContext = Depends(get_context_lab),
    _auth: str = auth_dependency
):
    """Delete a processed context by its ID and context_type."""
    success = opencontext.delete_context(detail_request.id, detail_request.context_type)
    if not success:
        raise HTTPException(status_code=404, detail="Context not found or failed to delete")
    return {"message": "Context deleted successfully"}


@router.post("/contexts/detail", response_class=HTMLResponse)
async def read_context_detail(
    detail_request: ContextDetailRequest,
    request: Request,
    opencontext: OpenContext = Depends(get_context_lab),
    _auth: str = auth_dependency
):
    context = opencontext.get_context(detail_request.id, detail_request.context_type)
    if context is None:
        return templates.TemplateResponse("error.html", {"request": request, "message": "Context not found"}, status_code=404)
    
    return templates.TemplateResponse("context_detail.html", {
        "request": request,
        "context": ProcessedContextModel.from_processed_context(context, project_root)
    })


@router.get("/api/context_types")
async def get_context_types(
    opencontext: OpenContext = Depends(get_context_lab),
    _auth: str = auth_dependency
):
    """Get all available context types."""
    try:
        context_types = opencontext.get_context_types()
        return context_types
    except Exception as e:
        logger.exception(f"Error getting context types: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get context types: {str(e)}")


@router.post("/api/vector_search")
async def vector_search(
    request: VectorSearchRequest,
    opencontext: OpenContext = Depends(get_context_lab),
    _auth: str = auth_dependency
):
    """Directly search vector database without using LLM."""
    try:
        results = opencontext.search(
            query=request.query,
            top_k=request.top_k,
            context_types=request.context_types,
            filters=request.filters
        )
        
        return convert_resp(data={
            "results": results,
            "total": len(results),
            "query": request.query,
            "top_k": request.top_k,
            "context_types": request.context_types,
            "filters": request.filters
        })
        
    except Exception as e:
        logger.exception(f"Error in vector search: {e}")
        return convert_resp(code=500, status=500, message=f"Vector search failed: {str(e)}")