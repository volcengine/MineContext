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
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from opencontext.context_consumption.context_agent import ContextAgent
from opencontext.context_consumption.context_agent.models import WorkflowStage
from opencontext.utils.logging_utils import get_logger
from opencontext.server.middleware.auth import auth_dependency

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/agent",
    tags=["agent_chat"]
)

# Global Context Agent instance
agent_instance = None


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
async def chat(
    request: ChatRequest,
    _auth: str = auth_dependency
) -> ChatResponse:
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
            context=request.context
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
            errors=result.get("errors")
        )
        
        return response
        
    except Exception as e:
        logger.exception(f"Chat failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    _auth: str = auth_dependency
):
    """Intelligent chat interface (streaming)"""
    
    async def generate():
        try:
            agent = get_agent()
            if not request.session_id:
                request.session_id = str(uuid.uuid4())
            yield f"data: {json.dumps({'type': 'session_start', 'session_id': request.session_id}, ensure_ascii=False)}\n\n"
            args = {
                "query": request.query,
                "session_id": request.session_id,
                "user_id": request.user_id,
            }
            if request.context:
                args.update(request.context)
            async for event in agent.process_stream(**args):
                converted_event = event.to_dict()
                yield f"data: {json.dumps(converted_event, ensure_ascii=False)}\n\n"
                if event.stage in [WorkflowStage.COMPLETED, WorkflowStage.FAILED]:
                    break
        except Exception as e:
            logger.exception(f"Stream chat failed: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/resume/{workflow_id}")
async def resume_workflow(
    workflow_id: str,
    request: ResumeRequest,
    _auth: str = auth_dependency
):
    """Resume workflow execution"""
    try:
        agent = get_agent()
        
        # Resume workflow
        result = await agent.resume(
            workflow_id=workflow_id,
            user_input=request.user_input
        )
        
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
            errors=result.get("errors")
        )
        
        return response
        
    except Exception as e:
        logger.exception(f"Resume workflow failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/state/{workflow_id}")
async def get_workflow_state(
    workflow_id: str,
    _auth: str = auth_dependency
):
    """Get workflow state"""
    try:
        agent = get_agent()
        state = await agent.get_state(workflow_id)
        
        if state:
            return {
                "success": True,
                "state": state
            }
        else:
            return {
                "success": False,
                "error": "Workflow not found"
            }
            
    except Exception as e:
        logger.exception(f"Get workflow state failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.delete("/cancel/{workflow_id}")
async def cancel_workflow(
    workflow_id: str,
    _auth: str = auth_dependency
):
    """Cancel workflow"""
    try:
        agent = get_agent()
        agent.cancel(workflow_id)
        
        return {
            "success": True,
            "message": f"Workflow {workflow_id} cancelled"
        }
        
    except Exception as e:
        logger.exception(f"Cancel workflow failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/test")
async def test_agent(
    _auth: str = auth_dependency
):
    """Test if Context Agent is working properly"""
    try:
        agent = get_agent()
        
        # Test simple query
        result = await agent.process(query="Hello, test the system")
        
        return {
            "success": True,
            "message": "Context Agent is working",
            "test_response": result
        }
        
    except Exception as e:
        logger.exception(f"Test failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }