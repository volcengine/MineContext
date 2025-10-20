#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Intelligent Completion API Routes
Provides GitHub Copilot-like note content completion functionality
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from opencontext.context_consumption.completion import get_completion_service
from opencontext.models.enums import CompletionType
from opencontext.server.middleware.auth import auth_dependency
from opencontext.utils.logging_utils import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["completions"])


# API model definitions
class CompletionRequest(BaseModel):
    """Completion request model"""

    text: str = Field(..., description="Current document content")
    cursor_position: int = Field(..., description="Cursor position")
    document_id: Optional[int] = Field(None, description="Document ID")
    completion_types: Optional[list] = Field(
        default=None,
        description="Specify completion types, e.g., ['semantic_continuation', 'template_completion']",
    )
    max_suggestions: Optional[int] = Field(default=3, description="Maximum number of suggestions")
    context: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional context information"
    )


class CompletionResponse(BaseModel):
    """Completion response model"""

    success: bool
    suggestions: list
    processing_time_ms: float
    cache_hit: bool = False
    error: Optional[str] = None


@router.post("/api/completions/suggest")
async def get_completion_suggestions(request: CompletionRequest, _auth: str = auth_dependency):
    """
    Get intelligent completion suggestions

    Supports multiple completion strategies:
    - Semantic continuation: Context-based intelligent continuation
    - Template completion: Structured completion for headings, lists, etc.
    - Reference suggestions: Recall relevant content from vector database
    """
    start_time = datetime.now()

    try:
        # Parameter validation
        if not request.text.strip():
            raise HTTPException(status_code=400, detail="Text content cannot be empty")

        if request.cursor_position < 0 or request.cursor_position > len(request.text):
            raise HTTPException(status_code=400, detail="Invalid cursor position")

        # Get completion service
        completion_service = get_completion_service()

        # Get completion suggestions
        suggestions = completion_service.get_completions(
            current_text=request.text,
            cursor_position=request.cursor_position,
            document_id=request.document_id,
            user_context=request.context or {},
        )

        # Filter specified completion types (if specified)
        if request.completion_types:
            valid_types = {ct.value for ct in CompletionType}
            filter_types = set(request.completion_types) & valid_types
            if filter_types:
                suggestions = [s for s in suggestions if s.completion_type.value in filter_types]

        # Limit number of suggestions
        if request.max_suggestions:
            suggestions = suggestions[: request.max_suggestions]

        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds() * 1000

        # Convert to response format
        suggestion_dicts = [s.to_dict() for s in suggestions]

        logger.info(
            f"Returned {len(suggestion_dicts)} completion suggestions, processing time: {processing_time:.2f}ms"
        )

        return JSONResponse(
            {
                "success": True,
                "suggestions": suggestion_dicts,
                "processing_time_ms": processing_time,
                "cache_hit": False,  # TODO: Implement cache hit detection
                "timestamp": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        logger.error(f"Completion request failed: {e}")

        return JSONResponse(
            {
                "success": False,
                "suggestions": [],
                "processing_time_ms": processing_time,
                "error": str(e),
            },
            status_code=500,
        )


@router.post("/api/completions/suggest/stream")
async def get_completion_suggestions_stream(
    request: CompletionRequest, _auth: str = auth_dependency
):
    """
    Stream completion suggestions
    Suitable for scenarios requiring real-time completion progress display
    """

    async def generate_completions():
        try:
            # Send start event
            yield f"data: {json.dumps({'type': 'start', 'timestamp': datetime.now().isoformat()})}\n\n"

            # Get completion service
            completion_service = get_completion_service()

            # Simulate streaming different types of completions
            completion_types = [
                CompletionType.TEMPLATE_COMPLETION,
                CompletionType.SEMANTIC_CONTINUATION,
                CompletionType.REFERENCE_SUGGESTION,
            ]

            all_suggestions = []

            for comp_type in completion_types:
                # Send processing status
                yield f"data: {json.dumps({'type': 'processing', 'completion_type': comp_type.value})}\n\n"

                # Get completions for this type
                suggestions = completion_service.get_completions(
                    current_text=request.text,
                    cursor_position=request.cursor_position,
                    document_id=request.document_id,
                    user_context=request.context or {},
                )

                # Filter suggestions for current type
                type_suggestions = [s for s in suggestions if s.completion_type == comp_type]

                if type_suggestions:
                    all_suggestions.extend(type_suggestions)

                    # Send suggestions for this type
                    for suggestion in type_suggestions:
                        yield f"data: {json.dumps({'type': 'suggestion', 'data': suggestion.to_dict()})}\n\n"

                # Small delay to simulate processing time
                await asyncio.sleep(0.1)

            # Send completion event
            yield f"data: {json.dumps({'type': 'complete', 'total_suggestions': len(all_suggestions)})}\n\n"
            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error(f"Stream completion failed: {e}")
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(
        generate_completions(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control",
        },
    )


@router.post("/api/completions/feedback")
async def submit_completion_feedback(
    suggestion_text: str,
    document_id: Optional[int] = None,
    accepted: bool = False,
    completion_type: Optional[str] = None,
    _auth: str = auth_dependency,
):
    """
    Submit completion feedback to improve completion quality

    Args:
        suggestion_text: Suggested text
        document_id: Document ID
        accepted: Whether the user accepted the suggestion
        completion_type: Completion type
    """
    try:
        # Record feedback (can be stored to database for future optimization)
        feedback_data = {
            "suggestion_text": suggestion_text,
            "document_id": document_id,
            "accepted": accepted,
            "completion_type": completion_type,
            "timestamp": datetime.now().isoformat(),
        }

        # TODO: Store feedback data to database
        logger.info(f"Received completion feedback: {feedback_data}")

        return JSONResponse({"success": True, "message": "Feedback recorded"})

    except Exception as e:
        logger.error(f"Failed to submit completion feedback: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@router.get("/api/completions/stats")
async def get_completion_stats(_auth: str = auth_dependency):
    """Get completion service statistics"""
    try:
        completion_service = get_completion_service()

        # Get cache statistics
        cache_stats = completion_service.get_cache_stats()

        # TODO: Add more statistics
        stats = {
            "service_status": "active",
            "cache_stats": cache_stats,
            "supported_types": [ct.value for ct in CompletionType],
            "timestamp": datetime.now().isoformat(),
        }

        return JSONResponse({"success": True, "data": stats})

    except Exception as e:
        logger.error(f"Failed to get completion statistics: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@router.get("/api/completions/cache/stats")
async def get_cache_stats(_auth: str = auth_dependency):
    """Get completion cache statistics"""
    try:
        completion_service = get_completion_service()
        stats = completion_service.get_cache_stats()

        return JSONResponse(
            {"success": True, "data": stats, "timestamp": datetime.now().isoformat()}
        )

    except Exception as e:
        logger.error(f"Failed to get cache statistics: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@router.post("/api/completions/cache/optimize")
async def optimize_cache(_auth: str = auth_dependency):
    """Optimize completion cache"""
    try:
        completion_service = get_completion_service()
        completion_service.optimize_cache()

        # Get statistics after optimization
        stats = completion_service.get_cache_stats()

        return JSONResponse(
            {"success": True, "message": "Cache optimization completed", "stats": stats}
        )

    except Exception as e:
        logger.error(f"Cache optimization failed: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@router.post("/api/completions/precompute/{document_id}")
async def precompute_document_context(document_id: int, content: str, _auth: str = auth_dependency):
    """Precompute document context"""
    try:
        completion_service = get_completion_service()
        completion_service.precompute_document_context(document_id, content)

        return JSONResponse(
            {"success": True, "message": f"Document {document_id} context precomputation completed"}
        )

    except Exception as e:
        logger.error(f"Failed to precompute document context: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@router.post("/api/completions/cache/clear")
async def clear_completion_cache(_auth: str = auth_dependency):
    """Clear completion cache"""
    try:
        completion_service = get_completion_service()
        completion_service.clear_cache()

        return JSONResponse({"success": True, "message": "Cache cleared"})

    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)
