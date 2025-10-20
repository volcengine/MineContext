#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Web search tool
Provides internet search capabilities to help obtain the latest information
"""

from typing import Any, Dict, List

from opencontext.config.global_config import get_config
from opencontext.tools.base import BaseTool
from opencontext.utils.logging_utils import get_logger

logger = get_logger(__name__)


class WebSearchTool(BaseTool):
    """Web search tool"""

    def __init__(self):
        super().__init__()
        self.config = get_config("tools.operation_tools.web_search_tool") or {}
        # Get search engine settings from config
        self.search_config = self.config.get("web_search", {})
        self.default_engine = self.search_config.get("engine", "duckduckgo")
        self.max_results = self.search_config.get("max_results", 5)
        self.timeout = self.search_config.get("timeout", 10)
        # Proxy settings
        self.proxy = self.search_config.get("proxy", None)
        if self.proxy:
            self.proxies = {"http": self.proxy, "https": self.proxy}
        else:
            self.proxies = None

    @classmethod
    def get_name(cls) -> str:
        return "web_search"

    @classmethod
    def get_description(cls) -> str:
        return """Internet search tool for retrieving real-time information from the web. Returns relevant webpage titles, snippets, and URLs based on search queries.

**When to use this tool:**
- When you need current, real-time information not in the local knowledge base
- When looking for recent news, events, or updates
- When seeking external references, documentation, or resources
- When the user's question requires up-to-date information beyond the system's stored context
- When verifying facts or finding additional sources

**When NOT to use this tool:**
- For searching stored contexts or history → use text_search, filter_context
- For entity lookups within the system → use profile_entity instead
- When the answer can be found in local context → prioritize local tools first
- For information that doesn't require real-time data

**Key features:**
- Keyword-based web search with natural language support
- Returns webpage titles, summaries, and links
- Configurable result count (1-20, default 5)
- Language preference support (zh-cn, en, ja, etc.)
- Uses DuckDuckGo for privacy-focused search
- Automatic proxy support for restricted networks

**Best practices:**
- Use specific, focused search queries for better results
- Specify language preference when appropriate
- Combine with local search tools to provide comprehensive answers
- Use when local context is insufficient or outdated

**Use cases:**
- "What's the latest news about AI developments?" → web_search
- "Find documentation for library X version Y" → web_search
- "What happened in the world today?" → web_search
- "Current price of Bitcoin" → web_search
"""

    @classmethod
    def get_parameters(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search keywords or question"},
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results, default 5",
                    "minimum": 1,
                    "maximum": 20,
                    "default": 5,
                },
                "lang": {
                    "type": "string",
                    "description": "Search language preference, e.g. 'zh-cn', 'en', etc.",
                    "default": "zh-cn",
                },
            },
            "required": ["query"],
        }

    def execute(
        self, query: str, max_results: int = None, lang: str = "zh-cn", **kwargs
    ) -> Dict[str, Any]:
        """Execute web search with automatic fallback support"""
        if max_results is None:
            max_results = self.max_results

        max_results = min(max_results, 20)  # Limit maximum results

        logger.info(f"Using primary search engine: {self.default_engine}")
        if self.default_engine == "duckduckgo":
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
                "engine": self.default_engine,
            }

        # All search engines failed
        return {
            "success": False,
            "query": query,
            "error": "All search engines failed",
            "results": [],
        }

    def _search_duckduckgo(self, query: str, max_results: int, lang: str) -> List[Dict[str, Any]]:
        """Search using ddgs library"""
        try:
            from ddgs import DDGS

            # Get region settings
            region = self._get_region(lang)
            results = []

            # Use ddgs API with SSL verification enabled for secure connection
            with DDGS(proxy=self.proxy, timeout=self.timeout, verify=True) as ddgs:
                # New API: text(query, ...) as the first positional argument
                search_results = list(
                    ddgs.text(
                        query,  # First positional argument
                        region=region,
                        safesearch="moderate",
                        max_results=max_results,
                    )
                )

            # Format results
            for r in search_results:
                results.append(
                    {
                        "title": r.get("title", ""),
                        "snippet": r.get("body", ""),
                        "url": r.get("href", ""),
                        "source": "DuckDuckGo",
                    }
                )

            return results

        except ImportError:
            logger.error("ddgs library not installed")
            raise Exception("ddgs library not installed. Please install with: pip install ddgs")
        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {e}")
            raise

    def _get_region(self, lang: str) -> str:
        """Get region code based on language (for DuckDuckGo)"""
        region_map = {
            "zh-cn": "cn-zh",
            "zh": "cn-zh",
            "en": "us-en",
            "en-us": "us-en",
            "en-gb": "gb-en",
            "ja": "jp-ja",
            "ko": "kr-ko",
            "fr": "fr-fr",
            "de": "de-de",
            "es": "es-es",
            "ru": "ru-ru",
        }

        return region_map.get(lang.lower(), "wt-wt")  # wt-wt means no specific region
