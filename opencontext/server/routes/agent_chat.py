#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Agent Chat Routes
Intelligent conversation routing based on Context Agent
"""

import asyncio
import json
import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from opencontext.context_consumption.context_agent import ContextAgent
from opencontext.context_consumption.context_agent.models import WorkflowStage
from opencontext.context_consumption.context_agent.models.enums import EventType
from opencontext.server.background_generation import (
    DONE_SENTINEL,
    _safe_put,
    get_background_manager,
)
from opencontext.server.middleware.auth import auth_dependency
from opencontext.storage.global_storage import get_storage
from opencontext.utils.logging_utils import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/agent", tags=["agent_chat"])

# Global Context Agent instance
agent_instance = None

# Interrupt flags for active streaming messages
# Key: message_id, Value: True if interrupted
active_streams = {}


def get_agent():
    """Get or create Context Agent instance"""
    global agent_instance
    if agent_instance is None:
        agent_instance = ContextAgent(enable_streaming=True)
        logger.info("Context Agent initialized")
    return agent_instance


# Request models
class ChatRequest(BaseModel):
    """Chat request"""

    query: str = Field(..., description="User query")
    context: Dict[str, Any] = Field(default_factory=dict, description="Context information")
    session_id: Optional[str] = Field(None, description="Session ID")
    user_id: Optional[str] = Field(None, description="User ID")
    conversation_id: Optional[int] = Field(None, description="Conversation ID for message storage")


class ResumeRequest(BaseModel):
    """Resume workflow request"""

    workflow_id: str = Field(..., description="Workflow ID")
    user_input: Optional[str] = Field(None, description="User input")


class ChatResponse(BaseModel):
    """Chat response"""

    success: bool
    workflow_id: str
    stage: str
    query: str
    intent: Optional[Dict[str, Any]] = None
    context: Optional[Dict[str, Any]] = None
    execution: Optional[Dict[str, Any]] = None
    reflection: Optional[Dict[str, Any]] = None
    errors: Optional[list] = None


@router.post("/chat")
async def chat(request: ChatRequest, _auth: str = auth_dependency) -> ChatResponse:
    """Intelligent chat interface (non-streaming)"""
    try:
        agent = get_agent()

        # Generate session_id
        if not request.session_id:
            request.session_id = str(uuid.uuid4())

        # Process query
        result = await agent.process(
            query=request.query,
            session_id=request.session_id,
            user_id=request.user_id,
            context=request.context,
        )

        # Build response
        response = ChatResponse(
            success=result.get("success", False),
            workflow_id=result.get("workflow_id", ""),
            stage=result.get("stage", "unknown"),
            query=result.get("query", request.query),
            intent=result.get("intent"),
            context=result.get("context"),
            execution=result.get("execution"),
            reflection=result.get("reflection"),
            errors=result.get("errors"),
        )

        return response

    except Exception as e:
        logger.exception(f"Chat failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest, _auth: str = auth_dependency):
    """Intelligent chat interface (streaming, background generation)"""

    manager = get_background_manager()
    storage = get_storage()

    if not request.session_id:
        request.session_id = str(uuid.uuid4())

    user_message_id: Optional[int] = None
    assistant_message_id: Optional[int] = None

    # ------------------------------------------------------------------ #
    # Create DB rows before starting the background task so that the      #
    # SSE session_start event can carry the real assistant_message_id.    #
    # ------------------------------------------------------------------ #
    if request.conversation_id:
        user_message_id = storage.create_message(
            conversation_id=request.conversation_id,
            role="user",
            content=request.query,
            is_complete=True,
        )
        logger.info(
            f"Created user message {user_message_id} in conversation {request.conversation_id}"
        )

        if request.query and request.query.strip():
            conversation = storage.get_conversation(request.conversation_id)
            if conversation and not conversation.get("title"):
                title = request.query[:50].strip()
                storage.update_conversation(conversation_id=request.conversation_id, title=title)
                logger.info(f"Set conversation {request.conversation_id} title: {title}")

        assistant_message_id = storage.create_streaming_message(
            conversation_id=request.conversation_id,
            role="assistant",
        )
        logger.info(f"Created assistant streaming message {assistant_message_id}")
        active_streams[assistant_message_id] = False  # interrupt flag

    # ------------------------------------------------------------------ #
    # Background coroutine: runs the agent and writes all output to DB.   #
    # Events are also forwarded to the per-task asyncio.Queue so that     #
    # the SSE generator (below) can relay them to the HTTP client.        #
    # If the HTTP client disconnects, the queue accumulates events but    #
    # the coroutine keeps running until generation finishes.              #
    # ------------------------------------------------------------------ #
    # Capture local references for the closure
    _session_id = request.session_id
    _query = request.query
    _user_id = request.user_id
    _context = request.context
    _conv_id = request.conversation_id
    _asst_mid = assistant_message_id

    async def generation_coro(queue: asyncio.Queue) -> None:
        try:
            agent = get_agent()
            args: Dict[str, Any] = {"query": _query, "session_id": _session_id, "user_id": _user_id}
            if _context:
                args.update(_context)

            event_metadata: Dict[str, Any] = {}
            interrupted = False

            async for event in agent.process_stream(**args):
                # Check in-memory interrupt flag
                if _asst_mid and active_streams.get(_asst_mid):
                    logger.info(f"Message {_asst_mid} was interrupted, stopping stream")
                    interrupted = True
                    await _safe_put(
                        queue,
                        {"type": "interrupted", "content": "Message generation was interrupted"},
                    )
                    break

                converted_event = event.to_dict()

                # Persist event to DB
                if _asst_mid and event.content:
                    if event.type == EventType.THINKING:
                        storage.add_message_thinking(
                            message_id=_asst_mid,
                            content=event.content,
                            stage=event.stage.value if event.stage else None,
                            progress=getattr(event, "progress", 0.0),
                            metadata=getattr(event, "metadata", None),
                        )
                    elif event.type == EventType.STREAM_CHUNK:
                        storage.append_message_content(
                            message_id=_asst_mid,
                            content_chunk=event.content,
                            token_count=1,
                        )
                    else:
                        key = event.type.value
                        event_metadata.setdefault(key, []).append(
                            {
                                "content": event.content,
                                "timestamp": (
                                    event.timestamp.isoformat()
                                    if hasattr(event, "timestamp")
                                    else None
                                ),
                                "stage": event.stage.value if event.stage else None,
                                "progress": getattr(event, "progress", None),
                            }
                        )

                await _safe_put(queue, converted_event)

                if event.stage in [WorkflowStage.COMPLETED, WorkflowStage.FAILED]:
                    if _asst_mid and event_metadata:
                        storage.update_message_metadata(
                            message_id=_asst_mid, metadata=event_metadata
                        )
                    if _asst_mid:
                        status = "completed" if event.stage == WorkflowStage.COMPLETED else "failed"
                        storage.mark_message_finished(
                            message_id=_asst_mid,
                            status=status,
                            error_message=(
                                event.metadata.get("error") if status == "failed" else None
                            ),
                        )
                        logger.info(f"Marked assistant message {_asst_mid} as {status}")
                    break

            if interrupted and _asst_mid:
                if event_metadata:
                    storage.update_message_metadata(message_id=_asst_mid, metadata=event_metadata)
                logger.info(f"Message {_asst_mid} interrupted (partial content saved)")

        except asyncio.CancelledError:
            logger.info(f"Generation task cancelled for session {_session_id}")
            if _asst_mid:
                try:
                    storage.mark_message_finished(message_id=_asst_mid, status="cancelled")
                except Exception:
                    pass
            raise

        except Exception as exc:
            logger.exception(f"Background generation failed: {exc}")
            if _asst_mid:
                try:
                    storage.mark_message_finished(
                        message_id=_asst_mid, status="failed", error_message=str(exc)
                    )
                except Exception:
                    pass
            await _safe_put(queue, {"type": "error", "content": str(exc)})

        finally:
            if _asst_mid and _asst_mid in active_streams:
                del active_streams[_asst_mid]

    # Submit the background task; raises HTTPException 429 if limit reached
    try:
        queue = await manager.submit_task(
            session_id=_session_id,
            conversation_id=_conv_id or 0,
            coro_factory=generation_coro,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=429, detail=str(exc))

    # ------------------------------------------------------------------ #
    # SSE generator: relays events from the queue to the HTTP client.     #
    # If the client disconnects, this generator exits but the background  #
    # task continues running.                                             #
    # ------------------------------------------------------------------ #
    async def generate():
        # Send session_start immediately (carries assistant_message_id)
        yield f"data: {json.dumps({'type': 'session_start', 'session_id': _session_id, 'assistant_message_id': _asst_mid}, ensure_ascii=False)}\n\n"

        while True:
            try:
                item = await asyncio.wait_for(queue.get(), timeout=30.0)
            except asyncio.TimeoutError:
                # Keep-alive heartbeat
                yield f"data: {json.dumps({'type': 'heartbeat'}, ensure_ascii=False)}\n\n"
                continue

            if item is DONE_SENTINEL:
                break

            yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/generation/status")
async def get_generation_status(_auth: str = auth_dependency):
    """Return all active background generation sessions."""
    manager = get_background_manager()
    return {"success": True, "active_sessions": manager.get_active_sessions()}


@router.delete("/generation/{session_id}")
async def cancel_generation(session_id: str, _auth: str = auth_dependency):
    """Cancel an active background generation task by session_id."""
    manager = get_background_manager()
    if not manager.is_running(session_id):
        return {"success": False, "message": f"No active generation for session {session_id}"}
    await manager.cancel_task(session_id)
    return {"success": True, "message": f"Generation {session_id} cancelled"}


@router.post("/resume/{workflow_id}")
async def resume_workflow(workflow_id: str, request: ResumeRequest, _auth: str = auth_dependency):
    """Resume workflow execution"""
    try:
        agent = get_agent()

        # Resume workflow
        result = await agent.resume(workflow_id=workflow_id, user_input=request.user_input)

        # Build response
        response = ChatResponse(
            success=result.get("success", False),
            workflow_id=result.get("workflow_id", workflow_id),
            stage=result.get("stage", "unknown"),
            query=result.get("query", ""),
            intent=result.get("intent"),
            context=result.get("context"),
            execution=result.get("execution"),
            reflection=result.get("reflection"),
            errors=result.get("errors"),
        )

        return response

    except Exception as e:
        logger.exception(f"Resume workflow failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/state/{workflow_id}")
async def get_workflow_state(workflow_id: str, _auth: str = auth_dependency):
    """Get workflow state"""
    try:
        agent = get_agent()
        state = await agent.get_state(workflow_id)

        if state:
            return {"success": True, "state": state}
        else:
            return {"success": False, "error": "Workflow not found"}

    except Exception as e:
        logger.exception(f"Get workflow state failed: {e}")
        return {"success": False, "error": str(e)}


@router.delete("/cancel/{workflow_id}")
async def cancel_workflow(workflow_id: str, _auth: str = auth_dependency):
    """Cancel workflow"""
    try:
        agent = get_agent()
        agent.cancel(workflow_id)

        return {"success": True, "message": f"Workflow {workflow_id} cancelled"}

    except Exception as e:
        logger.exception(f"Cancel workflow failed: {e}")
        return {"success": False, "error": str(e)}


@router.get("/test")
async def test_agent(_auth: str = auth_dependency):
    """Test if Context Agent is working properly"""
    try:
        agent = get_agent()

        # Test simple query
        result = await agent.process(query="Hello, test the system")

        return {"success": True, "message": "Context Agent is working", "test_response": result}

    except Exception as e:
        logger.exception(f"Test failed: {e}")
        return {"success": False, "error": str(e)}
