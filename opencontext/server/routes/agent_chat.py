#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Agent Chat Routes
Intelligent conversation routing based on Context Agent
"""

import json
import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from opencontext.context_consumption.context_agent import ContextAgent
from opencontext.context_consumption.context_agent.models import WorkflowStage
from opencontext.context_consumption.context_agent.models.enums import EventType
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
    """Intelligent chat interface (streaming)"""

    async def generate():
        user_message_id = None
        assistant_message_id = None
        storage = None

        try:
            agent = get_agent()
            storage = get_storage()

            if not request.session_id:
                request.session_id = str(uuid.uuid4())

            # Save user message if conversation_id is provided
            if request.conversation_id:
                user_message_id = storage.create_message(
                    conversation_id=request.conversation_id,
                    role="user",
                    content=request.query,
                    is_complete=True
                )
                logger.info(f"Created user message {user_message_id} in conversation {request.conversation_id}")

                # Update conversation title with user's question only if not already set
                if request.query and request.query.strip():
                    conversation = storage.get_conversation(request.conversation_id)
                    if conversation and not conversation.get("title"):
                        title = request.query[:50].strip()
                        storage.update_conversation(
                            conversation_id=request.conversation_id,
                            title=title
                        )
                        logger.info(f"Set conversation {request.conversation_id} title from user query: {title}")

            # Create streaming assistant message if conversation_id is provided
            if request.conversation_id:
                assistant_message_id = storage.create_streaming_message(
                    conversation_id=request.conversation_id,
                    role="assistant"
                )
                logger.info(f"Created assistant streaming message {assistant_message_id}")
                # Register this message as an active stream
                active_streams[assistant_message_id] = False

            # Send session start event with assistant_message_id
            yield f"data: {json.dumps({'type': 'session_start', 'session_id': request.session_id, 'assistant_message_id': assistant_message_id}, ensure_ascii=False)}\n\n"

            args = {
                "query": request.query,
                "session_id": request.session_id,
                "user_id": request.user_id,
            }
            if request.context:
                args.update(request.context)

            accumulated_content = ""
            event_metadata = {}  # Store events by type
            interrupted = False  # Track if stream was interrupted

            async for event in agent.process_stream(**args):
                # Check interrupt flag (in-memory, no database query)
                if assistant_message_id and active_streams.get(assistant_message_id):
                    logger.info(f"Message {assistant_message_id} was interrupted, stopping stream")
                    interrupted = True
                    yield f"data: {json.dumps({'type': 'interrupted', 'content': 'Message generation was interrupted'}, ensure_ascii=False)}\n\n"
                    break

                converted_event = event.to_dict()

                # Save event content based on type
                if assistant_message_id and event.content:
                    # Check if this is a thinking event
                    if event.type == EventType.THINKING:
                        # Save thinking messages separately to message_thinking table
                        storage.add_message_thinking(
                            message_id=assistant_message_id,
                            content=event.content,
                            stage=event.stage.value if event.stage else None,
                            progress=event.progress if hasattr(event, 'progress') else 0.0,
                            metadata=event.metadata if hasattr(event, 'metadata') else None
                        )
                        logger.debug(f"Saved thinking to message {assistant_message_id}: stage={event.stage.value if event.stage else 'unknown'}, content_len={len(event.content)}")
                    elif event.type == EventType.STREAM_CHUNK:
                        # Only stream_chunk content goes to message.content
                        accumulated_content += event.content
                        storage.append_message_content(
                            message_id=assistant_message_id,
                            content_chunk=event.content,
                            token_count=1  # Approximate token count
                        )
                        logger.debug(f"Appended stream_chunk to message {assistant_message_id}: content_len={len(event.content)}")
                    else:
                        # Other event types (running, done, etc.) go to metadata as lists
                        event_type_key = event.type.value
                        if event_type_key not in event_metadata:
                            event_metadata[event_type_key] = []
                        event_metadata[event_type_key].append({
                            "content": event.content,
                            "timestamp": event.timestamp.isoformat() if hasattr(event, 'timestamp') else None,
                            "stage": event.stage.value if event.stage else None,
                            "progress": event.progress if hasattr(event, 'progress') else None,
                        })
                        logger.debug(f"Added {event_type_key} event to metadata for message {assistant_message_id}")

                yield f"data: {json.dumps(converted_event, ensure_ascii=False)}\n\n"

                if event.stage in [WorkflowStage.COMPLETED, WorkflowStage.FAILED]:
                    # Update metadata with collected events before finishing
                    if assistant_message_id and event_metadata:
                        storage.update_message_metadata(
                            message_id=assistant_message_id,
                            metadata=event_metadata
                        )
                        logger.info(f"Updated message {assistant_message_id} metadata with {len(event_metadata)} event types")

                    # Mark assistant message as finished
                    if assistant_message_id:
                        status = "completed" if event.stage == WorkflowStage.COMPLETED else "failed"
                        storage.mark_message_finished(
                            message_id=assistant_message_id,
                            status=status,
                            error_message=event.metadata.get("error") if status == "failed" else None
                        )
                        logger.info(f"Marked assistant message {assistant_message_id} as {status}")
                    break

            # Handle interrupted stream - save accumulated data and mark as cancelled
            if interrupted and assistant_message_id:
                # Update metadata with collected events
                if event_metadata:
                    storage.update_message_metadata(
                        message_id=assistant_message_id,
                        metadata=event_metadata
                    )
                    logger.info(f"Updated interrupted message {assistant_message_id} metadata with {len(event_metadata)} event types")

                # Mark message as cancelled (status already set by interrupt endpoint)
                logger.info(f"Message {assistant_message_id} interrupted with {len(accumulated_content)} characters saved")

        except Exception as e:
            logger.exception(f"Stream chat failed: {e}")

            # Mark assistant message as failed if it exists
            if assistant_message_id and storage:
                try:
                    storage.mark_message_finished(
                        message_id=assistant_message_id,
                        status="failed",
                        error_message=str(e)
                    )
                except Exception as mark_error:
                    logger.exception(f"Failed to mark message as failed: {mark_error}")

            yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"

        finally:
            # Clean up the interrupt flag when stream ends
            if assistant_message_id and assistant_message_id in active_streams:
                del active_streams[assistant_message_id]
                logger.debug(f"Cleaned up interrupt flag for message {assistant_message_id}")

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


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
