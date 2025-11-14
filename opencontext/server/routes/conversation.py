#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Conversation Management API Routes
Handles CRUD operations for chat conversations.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from opencontext.server.middleware.auth import auth_dependency
from opencontext.storage.global_storage import get_storage
from opencontext.utils.logging_utils import get_logger

logger = get_logger(__name__)

# Use the same prefix and tags as agent_chat.py for grouping
router = APIRouter(prefix="/api/agent/chat", tags=["agent_chat"])


# --- Pydantic Models ---
# Based on API spec 4.1.1 - 4.1.5

class CreateConversationRequest(BaseModel):
    """Request model for 4.1.1 Create Conversation"""
    page_name: str = Field(...,
                           description="Page name, e.g., 'home' or 'creation'")
    document_id: Optional[str] = Field(None,
                                       description="Optional document ID to store in metadata")


class ConversationResponse(BaseModel):
    """
    Response model for 4.1.1 (Create), 4.1.2 (Get Detail), 
    and 4.1.4 (Update Title).
    """
    id: int
    title: Optional[str] = None
    user_id: Optional[str] = None
    created_at: str
    updated_at: str
    metadata: str
    page_name: str
    status: str


class ConversationSummary(ConversationResponse):
    """Individual conversation item for list response (matches detail)"""
    pass


class GetConversationListResponse(BaseModel):
    """Response model for 4.1.3 Get Conversation List"""
    items: List[ConversationSummary]
    total: int


class UpdateConversationRequest(BaseModel):
    """Request model for 4.1.4 Update Title"""
    title: str


class DeleteConversationResponse(BaseModel):
    """Response model for 4.1.5 Delete Conversation"""
    success: bool
    id: int


# --- API Endpoints ---

@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(
    request: CreateConversationRequest,
    _auth: str = auth_dependency,
):
    """
    4.1.1 Create a new conversation
    """
    try:
        storage = get_storage()

        # Prepare metadata if document_id is provided
        metadata = None
        if request.document_id:
            metadata = {"document_id": request.document_id}

        # user_id is optional in the backend and can be added later
        conversation = storage.create_conversation(
            page_name=request.page_name,
            metadata=metadata
        )

        if not conversation:
            raise HTTPException(
                status_code=500, detail="Failed to create conversation in database"
            )

        # The backend's `create_conversation` calls `get_conversation`,
        # which returns a dict that matches the ConversationResponse model.
        return conversation

    except Exception as e:
        logger.exception(f"Failed to create conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/list", response_model=GetConversationListResponse)
async def get_conversation_list(
    limit: int = Query(default=20, description="Return limit"),
    offset: int = Query(default=0, description="Offset"),
    page_name: Optional[str] = Query(
        default=None, description="Filter by page_name"),
    user_id: Optional[str] = Query(
        default=None, description="Filter by user_id"),
    status: str = Query(
        default="active", description="Filter by status ('active', 'deleted')"),
    _auth: str = auth_dependency,
):
    """
    4.1.3 Get a list of conversations with pagination and filtering
    """
    try:
        storage = get_storage()

        # The backend method returns a dict: {"items": [], "total": 0}
        # which directly matches the GetConversationListResponse model.
        result = storage.get_conversation_list(
            limit=limit,
            offset=offset,
            page_name=page_name,
            user_id=user_id,
            status=status
        )

        return result

    except Exception as e:
        logger.exception(f"Failed to get conversation list: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/{cid}", response_model=ConversationResponse)
async def get_conversation_detail(
    cid: int,
    _auth: str = auth_dependency,
):
    """
    4.1.2 Get a single conversation's details
    """
    try:
        storage = get_storage()
        conversation = storage.get_conversation(conversation_id=cid)

        if not conversation:
            raise HTTPException(
                status_code=404, detail="Conversation not found")

        return conversation

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get conversation detail: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/conversations/{cid}/update", response_model=ConversationResponse)
async def update_conversation_title(
    cid: int,
    request: UpdateConversationRequest,
    _auth: str = auth_dependency,
):
    """
    4.1.4 Update a conversation's title
    """
    try:
        storage = get_storage()

        # The backend's `update_conversation` calls `get_conversation`
        # on success, returning the updated object.
        updated_convo = storage.update_conversation(
            conversation_id=cid,
            title=request.title
        )

        if not updated_convo:
            raise HTTPException(
                status_code=404, detail="Conversation not found or update failed"
            )

        return updated_convo

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to update conversation title: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/conversations/{cid}/update", response_model=DeleteConversationResponse)
async def delete_conversation(
    cid: int,
    _auth: str = auth_dependency,
):
    """
    4.1.5 Mark a conversation as deleted (soft delete)
    """
    try:
        storage = get_storage()

        # The backend's `delete_conversation` method handles setting
        # the status to 'deleted' and returns the exact format
        # required by `DeleteConversationResponse`.
        result = storage.delete_conversation(conversation_id=cid)

        if not result.get("success"):
            raise HTTPException(
                status_code=404, detail="Conversation not found or delete failed"
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to delete conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))
