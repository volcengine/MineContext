#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
智能补全API路由
提供类似GitHub Copilot的笔记内容补全功能
"""

import json
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Request, HTTPException, Query, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from context_lab.context_consumption.completion import get_completion_service
from context_lab.utils.logging_utils import get_logger
from context_lab.models.enums import CompletionType
from context_lab.server.middleware.auth import auth_dependency

logger = get_logger(__name__)
router = APIRouter(tags=["completions"])


# API模型定义
class CompletionRequest(BaseModel):
    """补全请求模型"""
    text: str = Field(..., description="当前文档内容")
    cursor_position: int = Field(..., description="光标位置")
    document_id: Optional[int] = Field(None, description="文档ID")
    completion_types: Optional[list] = Field(
        default=None, 
        description="指定补全类型，如 ['semantic_continuation', 'template_completion']"
    )
    max_suggestions: Optional[int] = Field(default=3, description="最大建议数量")
    context: Optional[Dict[str, Any]] = Field(default=None, description="额外上下文信息")


class CompletionResponse(BaseModel):
    """补全响应模型"""
    success: bool
    suggestions: list
    processing_time_ms: float
    cache_hit: bool = False
    error: Optional[str] = None


@router.post("/api/completions/suggest")
async def get_completion_suggestions(
    request: CompletionRequest,
    _auth: str = auth_dependency
):
    """
    获取智能补全建议
    
    支持多种补全策略：
    - 语义续写：基于上下文的智能续写
    - 模板补全：标题、列表等结构化补全
    - 引用建议：从向量数据库召回相关内容
    """
    start_time = datetime.now()
    
    try:
        # 参数验证
        if not request.text.strip():
            raise HTTPException(status_code=400, detail="文本内容不能为空")
        
        if request.cursor_position < 0 or request.cursor_position > len(request.text):
            raise HTTPException(status_code=400, detail="光标位置无效")
        
        # 获取补全服务
        completion_service = get_completion_service()
        
        # 获取补全建议
        suggestions = completion_service.get_completions(
            current_text=request.text,
            cursor_position=request.cursor_position,
            document_id=request.document_id,
            user_context=request.context or {}
        )
        
        # 过滤指定类型的补全（如果有指定）
        if request.completion_types:
            valid_types = {ct.value for ct in CompletionType}
            filter_types = set(request.completion_types) & valid_types
            if filter_types:
                suggestions = [s for s in suggestions if s.completion_type.value in filter_types]
        
        # 限制建议数量
        if request.max_suggestions:
            suggestions = suggestions[:request.max_suggestions]
        
        # 计算处理时间
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # 转换为响应格式
        suggestion_dicts = [s.to_dict() for s in suggestions]
        
        logger.info(f"返回 {len(suggestion_dicts)} 个补全建议，处理时间: {processing_time:.2f}ms")
        
        return JSONResponse({
            "success": True,
            "suggestions": suggestion_dicts,
            "processing_time_ms": processing_time,
            "cache_hit": False,  # TODO: 实现缓存命中检测
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        logger.error(f"补全请求失败: {e}")
        
        return JSONResponse({
            "success": False,
            "suggestions": [],
            "processing_time_ms": processing_time,
            "error": str(e)
        }, status_code=500)


@router.post("/api/completions/suggest/stream")
async def get_completion_suggestions_stream(
    request: CompletionRequest,
    _auth: str = auth_dependency
):
    """
    流式获取补全建议
    适用于需要实时显示补全进度的场景
    """
    async def generate_completions():
        try:
            # 发送开始事件
            yield f"data: {json.dumps({'type': 'start', 'timestamp': datetime.now().isoformat()})}\n\n"
            
            # 获取补全服务
            completion_service = get_completion_service()
            
            # 模拟流式获取不同类型的补全
            completion_types = [
                CompletionType.TEMPLATE_COMPLETION,
                CompletionType.SEMANTIC_CONTINUATION,
                CompletionType.REFERENCE_SUGGESTION
            ]
            
            all_suggestions = []
            
            for comp_type in completion_types:
                # 发送处理状态
                yield f"data: {json.dumps({'type': 'processing', 'completion_type': comp_type.value})}\n\n"
                
                # 获取该类型的补全
                suggestions = completion_service.get_completions(
                    current_text=request.text,
                    cursor_position=request.cursor_position,
                    document_id=request.document_id,
                    user_context=request.context or {}
                )
                
                # 过滤当前类型的建议
                type_suggestions = [s for s in suggestions if s.completion_type == comp_type]
                
                if type_suggestions:
                    all_suggestions.extend(type_suggestions)
                    
                    # 发送该类型的建议
                    for suggestion in type_suggestions:
                        yield f"data: {json.dumps({'type': 'suggestion', 'data': suggestion.to_dict()})}\n\n"
                
                # 小延迟模拟处理时间
                await asyncio.sleep(0.1)
            
            # 发送完成事件
            yield f"data: {json.dumps({'type': 'complete', 'total_suggestions': len(all_suggestions)})}\n\n"
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            logger.error(f"流式补全失败: {e}")
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_completions(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )


@router.post("/api/completions/feedback")
async def submit_completion_feedback(
    suggestion_text: str,
    document_id: Optional[int] = None,
    accepted: bool = False,
    completion_type: Optional[str] = None,
    _auth: str = auth_dependency
):
    """
    提交补全反馈，用于改进补全质量
    
    Args:
        suggestion_text: 建议的文本
        document_id: 文档ID
        accepted: 用户是否接受了建议
        completion_type: 补全类型
    """
    try:
        # 记录反馈（这里可以存储到数据库用于后续优化）
        feedback_data = {
            "suggestion_text": suggestion_text,
            "document_id": document_id,
            "accepted": accepted,
            "completion_type": completion_type,
            "timestamp": datetime.now().isoformat()
        }
        
        # TODO: 存储反馈数据到数据库
        logger.info(f"收到补全反馈: {feedback_data}")
        
        return JSONResponse({
            "success": True,
            "message": "反馈已记录"
        })
        
    except Exception as e:
        logger.error(f"提交补全反馈失败: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


@router.get("/api/completions/stats")
async def get_completion_stats(
    _auth: str = auth_dependency
):
    """获取补全服务统计信息"""
    try:
        completion_service = get_completion_service()
        
        # 获取缓存统计
        cache_stats = completion_service.get_cache_stats()
        
        # TODO: 添加更多统计信息
        stats = {
            "service_status": "active",
            "cache_stats": cache_stats,
            "supported_types": [ct.value for ct in CompletionType],
            "timestamp": datetime.now().isoformat()
        }
        
        return JSONResponse({
            "success": True,
            "data": stats
        })
        
    except Exception as e:
        logger.error(f"获取补全统计失败: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


@router.get("/api/completions/cache/stats")
async def get_cache_stats(
    _auth: str = auth_dependency
):
    """获取补全缓存统计信息"""
    try:
        completion_service = get_completion_service()
        stats = completion_service.get_cache_stats()
        
        return JSONResponse({
            "success": True,
            "data": stats,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"获取缓存统计失败: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


@router.post("/api/completions/cache/optimize")
async def optimize_cache(
    _auth: str = auth_dependency
):
    """优化补全缓存"""
    try:
        completion_service = get_completion_service()
        completion_service.optimize_cache()
        
        # 获取优化后的统计信息
        stats = completion_service.get_cache_stats()
        
        return JSONResponse({
            "success": True,
            "message": "缓存优化完成",
            "stats": stats
        })
        
    except Exception as e:
        logger.error(f"缓存优化失败: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


@router.post("/api/completions/precompute/{document_id}")
async def precompute_document_context(
    document_id: int,
    content: str,
    _auth: str = auth_dependency
):
    """预计算文档上下文"""
    try:
        completion_service = get_completion_service()
        completion_service.precompute_document_context(document_id, content)
        
        return JSONResponse({
            "success": True,
            "message": f"文档 {document_id} 上下文预计算完成"
        })
        
    except Exception as e:
        logger.error(f"预计算文档上下文失败: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


@router.post("/api/completions/cache/clear")
async def clear_completion_cache(
    _auth: str = auth_dependency
):
    """清空补全缓存"""
    try:
        completion_service = get_completion_service()
        completion_service.clear_cache()
        
        return JSONResponse({
            "success": True,
            "message": "缓存已清空"
        })
        
    except Exception as e:
        logger.error(f"清空缓存失败: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)