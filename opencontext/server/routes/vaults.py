#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Vaults文档管理API路由
专注于文档的CRUD操作，AI对话功能由advanced_chat处理
"""

import json
import asyncio
from pathlib import Path
from typing import Optional
from datetime import datetime
import os

from fastapi import APIRouter, Request, Query, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from opencontext.utils.logging_utils import get_logger
from opencontext.storage.global_storage import get_storage
from opencontext.models.enums import VaultType
from opencontext.server.middleware.auth import auth_dependency

logger = get_logger(__name__)
router = APIRouter(tags=["vaults"])

templates_path = Path(__file__).parent.parent.parent / "web" / "templates"
templates = Jinja2Templates(directory=templates_path)


# API模型定义
class VaultDocument(BaseModel):
    """Vault文档模型"""
    id: Optional[int] = None
    title: str
    content: str
    summary: Optional[str] = None
    tags: Optional[str] = None
    document_type: str = VaultType.NOTE.value

@router.get("/vaults", response_class=HTMLResponse)
async def vaults_workspace(request: Request):
    """
    Vaults工作空间主页面 - 重定向到统一的文档协作界面
    """
    try:
        return templates.TemplateResponse("agent_chat.html", {
            "request": request,
            "title": "智能 Agent 对话"
        })
    except Exception as e:
        logger.exception(f"渲染文档协作页面失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vaults/editor", response_class=HTMLResponse)
async def note_editor_page(request: Request):
    """
    智能笔记编辑器页面
    提供带有AI补全功能的Markdown编辑器
    """
    try:
        return templates.TemplateResponse("note_editor.html", {
            "request": request,
            "title": "智能笔记编辑器"
        })
    except Exception as e:
        logger.exception(f"渲染笔记编辑器页面失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/vaults/list")
async def get_documents_list(
    limit: int = Query(default=50, description="返回数量限制"),
    offset: int = Query(default=0, description="偏移量"),
    _auth: str = auth_dependency
):
    """
    获取文档列表
    """
    try:
        storage = get_storage()
        documents = storage.get_vaults(limit=limit, offset=offset, is_deleted=False)
        
        # 格式化返回数据
        result = []
        for doc in documents:
            result.append({
                "id": doc["id"],
                "title": doc["title"],
                "summary": doc["summary"][:100] + "..." if doc["summary"] and len(doc["summary"]) > 100 else doc["summary"],
                "created_at": doc["created_at"],
                "updated_at": doc["updated_at"],
                "document_type": doc["document_type"],
                "content_length": len(doc["content"]) if doc["content"] else 0
            })
        
        return JSONResponse({
            "success": True,
            "data": result,
            "total": len(result)
        })
        
    except Exception as e:
        logger.exception(f"获取文档列表失败: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


@router.post("/api/vaults/create")
async def create_document(
    document: VaultDocument,
    background_tasks: BackgroundTasks,
    _auth: str = auth_dependency
):
    """
    创建新文档
    """
    try:
        logger.info(f"Creating document with data: {document}")
        storage = get_storage()
        
        # 创建新文档 - 使用insert_vaults方法
        doc_id = storage.insert_vaults(
            title=document.title,
            summary=document.summary, 
            content=document.content, # insert_vaults会自动处理None的情况
            document_type=document.document_type,
            tags=document.tags,
        )
        
        # 异步触发context处理
        document_data = {
            'title': document.title,
            'content': document.content,
            'summary': document.summary,
            'tags': document.tags,
            'document_type': document.document_type
        }
        background_tasks.add_task(trigger_document_processing, doc_id, document_data, "created")
        
        return JSONResponse({
            "success": True,
            "message": "文档创建成功",
            "doc_id": doc_id,
            "table_name": "vaults",
            "context_processing": "triggered"  # 表示已触发context处理
        })
        
    except Exception as e:
        logger.exception(f"创建文档失败: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


@router.get("/api/vaults/{document_id}")
async def get_document(
    document_id: int,
    _auth: str = auth_dependency
):
    """
    获取文档详情
    """
    try:
        storage = get_storage()
        # 获取所有文档来查找指定ID的文档
        documents = storage.get_vaults(limit=100, offset=0, is_deleted=False)
        
        # 找到指定ID的文档
        document = None
        for doc in documents:
            if doc["id"] == document_id:
                document = doc
                break
        
        if not document:
            raise HTTPException(status_code=404, detail="文档未找到")
        
        return JSONResponse({
            "success": True,
            "data": {
                "id": document["id"],
                "title": document["title"],
                "content": document["content"],
                "summary": document["summary"],
                "tags": document["tags"],
                "created_at": document["created_at"],
                "updated_at": document["updated_at"],
                "document_type": document["document_type"]
            }
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"获取文档详情失败: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


@router.post("/api/vaults/{document_id}")
async def save_document(
    document_id: int,
    document: VaultDocument,
    background_tasks: BackgroundTasks,
    _auth: str = auth_dependency
):
    """
    保存文档
    """
    try:
        storage = get_storage()
        
        # 先清理旧的context数据
        background_tasks.add_task(cleanup_document_context, document_id)
        
        # 更新现有文档
        success = storage.update_vault(
            vault_id=document_id,
            title=document.title,
            content=document.content,
            summary=document.summary,
            tags=document.tags
        )
        
        if success:
            # 异步触发新的context处理
            document_data = {
                'title': document.title,
                'content': document.content,
                'summary': document.summary,
                'tags': document.tags,
                'document_type': document.document_type
            }
            background_tasks.add_task(trigger_document_processing, document_id, document_data, "updated")
            
            return JSONResponse({
                "success": True,
                "message": "文档保存成功",
                "doc_id": document_id,
                "table_name": "vaults",
                "context_processing": "reprocessing"  # 表示重新处理context
            })
        else:
            raise HTTPException(status_code=404, detail="文档未找到或更新失败")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"保存文档失败: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


@router.delete("/api/vaults/{document_id}")
async def delete_document(
    document_id: int,
    background_tasks: BackgroundTasks,
    _auth: str = auth_dependency
):
    """
    删除文档（软删除）
    """
    try:
        storage = get_storage()
        
        # 软删除文档
        success = storage.update_vault(
            vault_id=document_id,
            is_deleted=True
        )
        
        if success:
            # 异步清理相关的context数据
            background_tasks.add_task(cleanup_document_context, document_id)
            
            return JSONResponse({
                "success": True,
                "message": "文档删除成功",
                "context_cleanup": "triggered"  # 表示已触发context清理
            })
        else:
            raise HTTPException(status_code=404, detail="文档未找到")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"删除文档失败: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


@router.get("/api/vaults/{document_id}/context")
async def get_document_context_status(
    document_id: int,
    _auth: str = auth_dependency
):
    """
    获取文档的context处理状态
    """
    try:
        # 获取context信息
        context_info = get_document_context_info(document_id)
        
        return JSONResponse({
            "success": True,
            "document_id": document_id,
            **context_info
        })
        
    except Exception as e:
        logger.exception(f"获取文档context状态失败: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


# Context处理辅助函数

async def trigger_document_processing(doc_id: int, document_data: dict, event_type: str = "created"):
    """
    异步触发文档的context处理
    
    Args:
        doc_id: 文档ID
        document_data: 文档数据
        event_type: 事件类型 (created/updated/deleted)
    """
    try:
        from opencontext.models.context import RawContextProperties
        from opencontext.models.enums import ContextSource, ContentFormat
        from opencontext.context_processing.processor.document_processor import DocumentProcessor
        
        # 创建RawContextProperties
        context_data = RawContextProperties(
            source=ContextSource.TEXT,
            content_format=ContentFormat.TEXT,
            content_text=document_data.get('content', ''),
            create_time=datetime.now(),
            object_id=f"vault_{doc_id}",
            additional_info={
                'vault_id': doc_id,
                'title': document_data.get('title', ''),
                'summary': document_data.get('summary', ''),
                'tags': document_data.get('tags', ''),
                'document_type': document_data.get('document_type', 'vaults'),
                'event_type': event_type,
                'folder_path': f"/vault_{doc_id}"  # 简化的路径
            }
        )
        
        # 获取文档处理器并触发处理
        processor = DocumentProcessor()
        success = processor.process(context_data)
        
        if success:
            logger.info(f"文档 {doc_id} 的context处理已触发 ({event_type})")
        else:
            logger.warning(f"文档 {doc_id} 的context处理触发失败 ({event_type})")
            
    except Exception as e:
        logger.exception(f"触发文档context处理失败: {e}")


async def cleanup_document_context(doc_id: int):
    """
    清理文档的所有context数据
    
    Args:
        doc_id: 文档ID
    """
    try:
        from opencontext.tools.retrieval_tools.document_retrieval_tool import DocumentRetrievalTool
        
        # 使用DocumentRetrievalTool删除相关chunks
        retrieval_tool = DocumentRetrievalTool()
        result = retrieval_tool.delete_document_chunks(
            raw_type="vaults",
            raw_id=str(doc_id)
        )
        
        if result.get('success'):
            logger.info(f"已清理文档 {doc_id} 的 {result.get('deleted_count', 0)} 个context chunks")
        else:
            logger.warning(f"清理文档 {doc_id} 的context失败: {result.get('error')}")
            
    except Exception as e:
        logger.exception(f"清理文档context失败: {e}")


def get_document_context_info(doc_id: int) -> dict:
    """
    获取文档的context处理信息
    
    Args:
        doc_id: 文档ID
        
    Returns:
        context信息字典
    """
    try:
        from opencontext.tools.retrieval_tools.document_retrieval_tool import DocumentRetrievalTool
        
        retrieval_tool = DocumentRetrievalTool()
        result = retrieval_tool.get_document_by_id(
            raw_type="vaults",
            raw_id=str(doc_id),
            return_chunks=False
        )
        
        if result.get('success'):
            return {
                'has_context': True,
                'total_chunks': result.get('total_chunks', 0),
                'document_info': result.get('document', {})
            }
        else:
            return {
                'has_context': False,
                'total_chunks': 0,
                'document_info': None
            }
            
    except Exception as e:
        logger.exception(f"获取文档context信息失败: {e}")
        return {
            'has_context': False,
            'total_chunks': 0,
            'error': str(e)
        }