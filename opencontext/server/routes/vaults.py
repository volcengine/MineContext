#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Vaults document management API routes
Focuses on document CRUD operations, AI chat functionality handled by advanced_chat
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from opencontext.models.enums import VaultType
from opencontext.server.middleware.auth import auth_dependency
from opencontext.storage.global_storage import get_storage
from opencontext.utils.logging_utils import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["vaults"])

templates_path = Path(__file__).parent.parent.parent / "web" / "templates"
templates = Jinja2Templates(directory=templates_path)


# API model definitions
class VaultDocument(BaseModel):
    """Vault document model"""

    id: Optional[int] = None
    title: str
    content: str
    summary: Optional[str] = None
    tags: Optional[str] = None
    document_type: str = VaultType.NOTE.value


@router.get("/vaults", response_class=HTMLResponse)
async def vaults_workspace(request: Request):
    """
    Vaults workspace main page - redirects to unified document collaboration interface
    """
    try:
        return templates.TemplateResponse(
            "agent_chat.html", {"request": request, "title": "Intelligent Agent Chat"}
        )
    except Exception as e:
        logger.exception(f"Failed to render document collaboration page: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vaults/editor", response_class=HTMLResponse)
async def note_editor_page(request: Request):
    """
    Intelligent note editor page
    Provides Markdown editor with AI completion functionality
    """
    try:
        return templates.TemplateResponse(
            "note_editor.html", {"request": request, "title": "Intelligent Note Editor"}
        )
    except Exception as e:
        logger.exception(f"Failed to render note editor page: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/vaults/list")
async def get_documents_list(
    limit: int = Query(default=50, description="Return limit"),
    offset: int = Query(default=0, description="Offset"),
    _auth: str = auth_dependency,
):
    """
    Get document list
    """
    try:
        storage = get_storage()
        documents = storage.get_vaults(limit=limit, offset=offset, is_deleted=False)

        # Format return data
        result = []
        for doc in documents:
            result.append(
                {
                    "id": doc["id"],
                    "title": doc["title"],
                    "summary": (
                        doc["summary"][:100] + "..."
                        if doc["summary"] and len(doc["summary"]) > 100
                        else doc["summary"]
                    ),
                    "created_at": doc["created_at"],
                    "updated_at": doc["updated_at"],
                    "document_type": doc["document_type"],
                    "content_length": len(doc["content"]) if doc["content"] else 0,
                }
            )

        return JSONResponse({"success": True, "data": result, "total": len(result)})

    except Exception as e:
        logger.exception(f"Failed to get document list: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@router.post("/api/vaults/create")
async def create_document(
    document: VaultDocument, background_tasks: BackgroundTasks, _auth: str = auth_dependency
):
    """
    Create new document
    """
    try:
        logger.info(f"Creating document with data: {document}")
        storage = get_storage()

        # Create new document - use insert_vaults method
        doc_id = storage.insert_vaults(
            title=document.title,
            summary=document.summary,
            content=document.content,  # insert_vaults will automatically handle None
            document_type=document.document_type,
            tags=document.tags,
        )

        # Asynchronously trigger context processing
        document_data = {
            "title": document.title,
            "content": document.content,
            "summary": document.summary,
            "tags": document.tags,
            "document_type": document.document_type,
        }
        background_tasks.add_task(trigger_document_processing, doc_id, document_data, "created")

        return JSONResponse(
            {
                "success": True,
                "message": "Document created successfully",
                "doc_id": doc_id,
                "table_name": "vaults",
                "context_processing": "triggered",  # Indicates context processing has been triggered
            }
        )

    except Exception as e:
        logger.exception(f"Failed to create document: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@router.get("/api/vaults/{document_id}")
async def get_document(document_id: int, _auth: str = auth_dependency):
    """
    Get document details
    """
    try:
        storage = get_storage()
        # Get all documents to find the document with specified ID
        documents = storage.get_vaults(limit=100, offset=0, is_deleted=False)

        # Find the document with specified ID
        document = None
        for doc in documents:
            if doc["id"] == document_id:
                document = doc
                break

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        return JSONResponse(
            {
                "success": True,
                "data": {
                    "id": document["id"],
                    "title": document["title"],
                    "content": document["content"],
                    "summary": document["summary"],
                    "tags": document["tags"],
                    "created_at": document["created_at"],
                    "updated_at": document["updated_at"],
                    "document_type": document["document_type"],
                },
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get document details: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@router.post("/api/vaults/{document_id}")
async def save_document(
    document_id: int,
    document: VaultDocument,
    background_tasks: BackgroundTasks,
    _auth: str = auth_dependency,
):
    """
    Save document
    """
    try:
        storage = get_storage()

        # First clean up old context data
        background_tasks.add_task(cleanup_document_context, document_id)

        # Update existing document
        success = storage.update_vault(
            vault_id=document_id,
            title=document.title,
            content=document.content,
            summary=document.summary,
            tags=document.tags,
        )

        if success:
            # Asynchronously trigger new context processing
            document_data = {
                "title": document.title,
                "content": document.content,
                "summary": document.summary,
                "tags": document.tags,
                "document_type": document.document_type,
            }
            background_tasks.add_task(
                trigger_document_processing, document_id, document_data, "updated"
            )

            return JSONResponse(
                {
                    "success": True,
                    "message": "Document saved successfully",
                    "doc_id": document_id,
                    "table_name": "vaults",
                    "context_processing": "reprocessing",  # Indicates reprocessing context
                }
            )
        else:
            raise HTTPException(status_code=404, detail="Document not found or update failed")

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to save document: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@router.delete("/api/vaults/{document_id}")
async def delete_document(
    document_id: int, background_tasks: BackgroundTasks, _auth: str = auth_dependency
):
    """
    Delete document (soft delete)
    """
    try:
        storage = get_storage()

        # Soft delete document
        success = storage.update_vault(vault_id=document_id, is_deleted=True)

        if success:
            # Asynchronously clean up related context data
            background_tasks.add_task(cleanup_document_context, document_id)

            return JSONResponse(
                {
                    "success": True,
                    "message": "Document deleted successfully",
                    "context_cleanup": "triggered",  # Indicates context cleanup has been triggered
                }
            )
        else:
            raise HTTPException(status_code=404, detail="Document not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to delete document: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@router.get("/api/vaults/{document_id}/context")
async def get_document_context_status(document_id: int, _auth: str = auth_dependency):
    """
    Get document context processing status
    """
    try:
        # Get context information
        context_info = get_document_context_info(document_id)

        return JSONResponse({"success": True, "document_id": document_id, **context_info})

    except Exception as e:
        logger.exception(f"Failed to get document context status: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


# Context processing helper functions


async def trigger_document_processing(
    doc_id: int, document_data: dict, event_type: str = "created"
):
    """
    Asynchronously trigger document context processing

    Args:
        doc_id: Document ID
        document_data: Document data
        event_type: Event type (created/updated/deleted)
    """
    try:
        from opencontext.context_processing.processor.document_processor import DocumentProcessor
        from opencontext.models.context import RawContextProperties
        from opencontext.models.enums import ContentFormat, ContextSource

        # Create RawContextProperties
        context_data = RawContextProperties(
            source=ContextSource.TEXT,
            content_format=ContentFormat.TEXT,
            content_text=document_data.get("content", ""),
            create_time=datetime.now(),
            object_id=f"vault_{doc_id}",
            additional_info={
                "vault_id": doc_id,
                "title": document_data.get("title", ""),
                "summary": document_data.get("summary", ""),
                "tags": document_data.get("tags", ""),
                "document_type": document_data.get("document_type", "vaults"),
                "event_type": event_type,
                "folder_path": f"/vault_{doc_id}",  # Simplified path
            },
        )

        # Get document processor and trigger processing
        processor = DocumentProcessor()
        success = processor.process(context_data)

        if success:
            logger.info(f"Context processing triggered for document {doc_id} ({event_type})")
        else:
            logger.warning(
                f"Failed to trigger context processing for document {doc_id} ({event_type})"
            )

    except Exception as e:
        logger.exception(f"Failed to trigger document context processing: {e}")


async def cleanup_document_context(doc_id: int):
    """
    Clean up all context data for a document

    Args:
        doc_id: Document ID
    """
    try:
        from opencontext.tools.retrieval_tools.document_management_tool import (
            DocumentManagementTool,
        )

        # Use DocumentManagementTool to delete related chunks
        management_tool = DocumentManagementTool()
        result = management_tool.delete_document_chunks(raw_type="vaults", raw_id=str(doc_id))

        if result.get("success"):
            logger.info(
                f"Cleaned up {result.get('deleted_count', 0)} context chunks for document {doc_id}"
            )
        else:
            logger.warning(
                f"Failed to cleanup context for document {doc_id}: {result.get('error')}"
            )

    except Exception as e:
        logger.exception(f"Failed to cleanup document context: {e}")


def get_document_context_info(doc_id: int) -> dict:
    """
    Get document context processing information

    Args:
        doc_id: Document ID

    Returns:
        Context information dictionary
    """
    try:
        from opencontext.tools.retrieval_tools.document_management_tool import (
            DocumentManagementTool,
        )

        management_tool = DocumentManagementTool()
        result = management_tool.get_document_by_id(
            raw_type="vaults", raw_id=str(doc_id), return_chunks=False
        )

        if result.get("success"):
            return {
                "has_context": True,
                "total_chunks": result.get("total_chunks", 0),
                "document_info": result.get("document", {}),
            }
        else:
            return {"has_context": False, "total_chunks": 0, "document_info": None}

    except Exception as e:
        logger.exception(f"Failed to get document context information: {e}")
        return {"has_context": False, "total_chunks": 0, "error": str(e)}
