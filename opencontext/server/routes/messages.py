#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Conversation Message Management API Routes
Handles CRUD operations for individual messages within a conversation.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from opencontext.server.middleware.auth import auth_dependency
from opencontext.storage.global_storage import get_storage
from opencontext.utils.logging_utils import get_logger

logger = get_logger(__name__)

# Use the same prefix and tags as agent_chat.py for grouping
router = APIRouter(prefix="/api/agent/chat", tags=["agent_chat"])

# Import active_streams from agent_chat to set interrupt flags
# This will be initialized when agent_chat module is loaded
try:
    from opencontext.server.routes import agent_chat
    def get_active_streams():
        return agent_chat.active_streams
except ImportError:
    # Fallback if agent_chat is not loaded yet
    def get_active_streams():
        return {}


# --- Pydantic Models ---
# Based on API spec 4.2.2 - 4.2.7

class CreateMessageParams(BaseModel):
    """Request model for 4.2.2 Create Message"""
    conversation_id: int
    role: str
    content: str
    is_complete: Optional[bool] = False
    token_count: Optional[int] = 0


class CreateStreamingMessageParams(BaseModel):
    """Request model for 4.2.3 Create Streaming Message"""
    conversation_id: int
    role: str


class UpdateMessageContentParams(BaseModel):
    """
    Request model for 4.2.4 Update Message.
    Note: message_id is in the body per spec, though redundant with URL.
    """
    message_id: int
    new_content: str
    is_complete: Optional[bool] = False
    token_count: Optional[int] = None


class AppendMessageContentParams(BaseModel):
    """
    Request model for 4.2.5 Append Message Content.
    Note: message_id is in the body per spec, though redundant with URL.
    """
    message_id: int
    content_chunk: str
    token_count: Optional[int] = None


class ConversationMessage(BaseModel):
    """Response model for a single message in a list (4.2.7)"""
    id: int
    conversation_id: int
    parent_message_id: Optional[str] = None
    role: str
    content: str
    status: str
    token_count: int
    metadata: str  # JSON string
    latency_ms: int
    error_message: str
    thinking: List[Dict[str, Any]] = []  # Thinking records for this message
    completed_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class MessageInterruptResponse(BaseModel):
    """Response model for Interrupt Message"""
    message_id: str


# --- API Endpoints ---

@router.post("/message/{mid}/create", response_model=int)
async def create_message(
    mid: str,  # Interpreted as parent_message_id per spec
    request: CreateMessageParams,
    _auth: str = auth_dependency,
):
    """
    4.2.2 Create a new message.
    'mid' from URL is used as parent_message_id.
    """
    try:
        storage = get_storage()

        # Use create_message with is_complete parameter
        message_id = storage.create_message(
            conversation_id=request.conversation_id,
            role=request.role,
            content=request.content,
            is_complete=request.is_complete,
            token_count=request.token_count,
            parent_message_id=mid,
        )

        if not message_id:
            raise HTTPException(
                status_code=500, detail="Failed to create message")

        return message_id

    except Exception as e:
        logger.exception(f"Failed to create message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/message/stream/{mid}/create", response_model=int)
async def create_streaming_message(
    mid: str,  # Interpreted as parent_message_id per spec
    request: CreateStreamingMessageParams,
    _auth: str = auth_dependency,
):
    """
    4.2.3 Create a new streaming message (placeholder).
    'mid' from URL is used as parent_message_id.
    """
    try:
        storage = get_storage()

        # Use create_streaming_message method
        message_id = storage.create_streaming_message(
            conversation_id=request.conversation_id,
            role=request.role,
            parent_message_id=mid,
        )

        if not message_id:
            raise HTTPException(
                status_code=500, detail="Failed to create streaming message")

        return message_id

    except Exception as e:
        logger.exception(f"Failed to create streaming message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/message/{mid}/update", response_model=bool)
async def update_message(
    mid: int,  # Message ID from URL
    request: UpdateMessageContentParams,
    _auth: str = auth_dependency,
):
    """
    4.2.4 Update a message's content.
    Uses 'mid' from URL as the primary message_id.
    """
    try:
        storage = get_storage()

        # Use update_message which returns Optional[Dict] or None
        result = storage.update_message(
            message_id=mid,
            new_content=request.new_content,
            is_complete=request.is_complete,
            token_count=request.token_count
        )

        if not result:
            raise HTTPException(
                status_code=404, detail="Message not found or update failed")

        return True

    except Exception as e:
        logger.exception(f"Failed to update message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/message/{mid}/append", response_model=bool)
async def append_message(
    mid: int,  # Message ID from URL
    request: AppendMessageContentParams,
    _auth: str = auth_dependency,
):
    """
    4.2.5 Append content to an existing message (for streaming).
    Uses 'mid' from URL as the primary message_id.
    """
    try:
        storage = get_storage()

        # Use append_message_content with correct parameter name
        success = storage.append_message_content(
            message_id=mid,
            content_chunk=request.content_chunk,
            token_count=request.token_count or 0
        )

        if not success:
            raise HTTPException(
                status_code=404, detail="Message not found or append failed")

        return success

    except Exception as e:
        logger.exception(f"Failed to append message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/message/{mid}/finished", response_model=bool)
async def mark_message_finished_route(
    mid: int,  # Message ID from URL
    _auth: str = auth_dependency,
):
    """
    4.2.6 Mark a message as complete.
    """
    try:
        storage = get_storage()

        # Use mark_message_finished method
        success = storage.mark_message_finished(
            message_id=mid,
            status='completed'
        )

        if not success:
            raise HTTPException(
                status_code=404, detail="Message not found or update failed")

        return success

    except Exception as e:
        logger.exception(f"Failed to mark message finished: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/{cid}/messages", response_model=List[ConversationMessage])
async def get_conversation_messages(
    cid: int,
    _auth: str = auth_dependency,
):
    """
    4.2.7 Get all messages for a specific conversation.
    Note: The spec defines the response as a direct array.
    """
    try:
        storage = get_storage()

        # Use get_conversation_messages method
        messages = storage.get_conversation_messages(conversation_id=cid)

        # The response_model=List[ConversationMessage] will handle
        # validating and returning the list directly.
        return messages

    except Exception as e:
        logger.exception(f"Failed to get conversation messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/messages/{mid}/interrupt", response_model=MessageInterruptResponse)
async def interrupt_message_generation(
    mid: str,  # Message ID from URL
    _auth: str = auth_dependency,
):
    """
    Interrupt message generation (mark as 'cancelled').
    Sets both database status and in-memory interrupt flag for immediate response.
    """
    try:
        storage = get_storage()
        message_id = int(mid)

        # Set in-memory interrupt flag for immediate effect
        active_streams = get_active_streams()
        if message_id in active_streams:
            active_streams[message_id] = True
            logger.info(f"Set interrupt flag for active message {message_id}")

        # Also update database status
        success = storage.mark_message_finished(
            message_id=message_id,
            status='cancelled'
        )

        if not success:
            raise HTTPException(
                status_code=404, detail="Message not found or interrupt failed")

        return MessageInterruptResponse(message_id=mid)

    except Exception as e:
        logger.exception(f"Failed to interrupt message: {e}")
        raise HTTPException(status_code=500, detail=str(e))
