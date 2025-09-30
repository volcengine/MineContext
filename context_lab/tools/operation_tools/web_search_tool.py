#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
联网搜索工具
提供互联网搜索能力，帮助获取最新信息
"""

from typing import Dict, Any, List
from context_lab.tools.base import BaseTool
from context_lab.utils.logging_utils import get_logger
from context_lab.config.global_config import get_config

logger = get_logger(__name__)

class WebSearchTool(BaseTool):
    """联网搜索工具"""
    
    def __init__(self):
        super().__init__()
        self.config = get_config('tools.operation_tools.web_search_tool') or {}
        # 从配置中获取搜索引擎设置
        self.search_config = self.config.get('web_search', {})
        self.default_engine = self.search_config.get('engine', 'duckduckgo')
        self.max_results = self.search_config.get('max_results', 5)
        self.timeout = self.search_config.get('timeout', 10)
        # 代理设置
        self.proxy = self.search_config.get('proxy', None)
        if self.proxy:
            self.proxies = {
                'http': self.proxy,
                'https': self.proxy
            }
        else:
            self.proxies = None
    
    @classmethod
    def get_name(cls) -> str:
        return "web_search"
    
    @classmethod
    def get_description(cls) -> str:
        return "搜索互联网获取最新信息。支持关键词搜索，返回相关网页标题、摘要和链接。适用于获取实时信息、新闻、技术文档等。"
    
    @classmethod
    def get_parameters(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词或问题"
                },
                "max_results": {
                    "type": "integer",
                    "description": "最大结果数量，默认5",
                    "minimum": 1,
                    "maximum": 20,
                    "default": 5
                },
                "lang": {
                    "type": "string", 
                    "description": "搜索语言偏好，如 'zh-cn', 'en' 等",
                    "default": "zh-cn"
                }
            },
            "required": ["query"]
        }
    
    def execute(self, query: str, max_results: int = None, lang: str = "zh-cn", **kwargs) -> Dict[str, Any]:
        """执行网络搜索，支持自动降级"""
        if max_results is None:
            max_results = self.max_results
        
        max_results = min(max_results, 20)  # 限制最大结果数
        
        logger.info(f"Using primary search engine: {self.default_engine}")
        if self.default_engine == 'duckduckgo':
            results = self._search_duckduckgo(query, max_results, lang)
        else:
            raise ValueError(f"Unknown search engine: {self.default_engine}")
            
        if results:
            logger.info(f"Successfully retrieved {len(results)} results from {self.default_engine}")
            return {
                "success": True,
                "query": query,
                "results_count": len(results),
                "results": results,
                "engine": self.default_engine
            }
        
        # 所有搜索引擎都失败
        return {
            "success": False,
            "query": query,
            "error": "All search engines failed",
            "results": []
        }
    
    def _search_duckduckgo(self, query: str, max_results: int, lang: str) -> List[Dict[str, Any]]:
        """使用 ddgs 库进行搜索"""
        try:
            from ddgs import DDGS
            
            # 获取区域设置
            region = self._get_region(lang)
            results = []
            
            # 使用 ddgs API，启用SSL验证以确保安全连接
            with DDGS(proxy=self.proxy, timeout=self.timeout, verify=True) as ddgs:
                # 新版 API: text(query, ...) 作为第一个位置参数
                search_results = list(ddgs.text(
                    query,  # 第一个位置参数
                    region=region,
                    safesearch='moderate',
                    max_results=max_results
                ))
            
            # 格式化结果
            for r in search_results:
                results.append({
                    'title': r.get('title', ''),
                    'snippet': r.get('body', ''),
                    'url': r.get('href', ''),
                    'source': 'DuckDuckGo'
                })
            
            return results
            
        except ImportError:
            logger.error("ddgs library not installed")
            raise Exception("ddgs library not installed. Please install with: pip install ddgs")
        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {e}")
            raise

    def _get_region(self, lang: str) -> str:
        """根据语言获取区域代码（用于 DuckDuckGo）"""
        region_map = {
            'zh-cn': 'cn-zh',
            'zh': 'cn-zh',
            'en': 'us-en',
            'en-us': 'us-en',
            'en-gb': 'gb-en',
            'ja': 'jp-ja',
            'ko': 'kr-ko',
            'fr': 'fr-fr',
            'de': 'de-de',
            'es': 'es-es',
            'ru': 'ru-ru',
        }
        
        return region_map.get(lang.lower(), 'wt-wt')  # wt-wt 表示无特定区域