# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
API Key Authentication Middleware
"""

import fnmatch
from math import log
from typing import List, Optional

from fastapi import Depends, Header, HTTPException, Query, Request

from opencontext.config.global_config import get_config
from opencontext.utils.logging_utils import get_logger

logger = get_logger(__name__)

# Global variables to cache auth configuration
_auth_config = None


def reset_auth_cache():
    """Reset authentication cache - useful for testing"""
    global _auth_config
    _auth_config = None


def get_auth_config() -> dict:
    """Get authentication configuration."""
    return get_config("api_auth") or {}


def is_auth_enabled() -> bool:
    """Check if API authentication is enabled."""
    auth_config = get_auth_config()
    return auth_config.get("enabled", False)


def get_valid_api_keys() -> List[str]:
    """Get list of valid API keys."""
    auth_config = get_auth_config()
    api_keys = auth_config.get("api_keys", [])
    # Filter out empty keys
    return [key for key in api_keys if key and key.strip()]


def get_excluded_paths() -> List[str]:
    """Get list of paths excluded from authentication."""
    auth_config = get_auth_config()
    return auth_config.get("excluded_paths", ["/health", "/api/health", "/", "/static/*"])


def is_path_excluded(path: str) -> bool:
    """Check if a path is excluded from authentication."""
    excluded_paths = get_excluded_paths()

    for excluded_path in excluded_paths:
        # Support wildcard matching
        if fnmatch.fnmatch(path, excluded_path):
            return True

    return False


def verify_api_key(
    request: Request,
    api_key_header: Optional[str] = Header(None, alias="X-API-Key"),
    api_key_query: Optional[str] = Query(None, alias="api_key"),
) -> str:
    """
    Verify API key from header or query parameter.
    """
    # Check if authentication is enabled
    if not is_auth_enabled():
        return "auth_disabled"

    # Check if current path is excluded
    if is_path_excluded(request.url.path):
        logger.debug(f"Path {request.url.path} is excluded from authentication")
        return "path_excluded"

    # Get API key from header or query parameter
    api_key = api_key_header or api_key_query

    if not api_key:
        logger.warning(f"No API key provided for {request.url.path}")
        raise HTTPException(
            status_code=401,
            detail="API key required. Provide it via X-API-Key header or api_key query parameter.",
        )

    # Validate API key
    valid_keys = get_valid_api_keys()

    if not valid_keys:
        logger.warning("No valid API keys configured")
        raise HTTPException(
            status_code=500, detail="Server configuration error: No API keys configured"
        )

    if api_key not in valid_keys:
        logger.warning(f"Invalid API key provided for {request.url.path}: {api_key[:8]}...")
        raise HTTPException(status_code=401, detail="Invalid API key")

    logger.debug(f"API key authenticated successfully for {request.url.path}")
    return api_key


auth_dependency = Depends(verify_api_key)
