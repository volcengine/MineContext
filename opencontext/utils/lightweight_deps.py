#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Lightweight utilities to reduce external dependencies.
Provides basic implementations to replace heavy third-party libraries.
"""

import json
import re
from typing import Any, Dict, Optional, Union
import urllib.request
import urllib.parse
import urllib.error


class LightweightHTTP:
    """
    Lightweight HTTP client as alternative to requests/httpx.
    
    Provides basic HTTP functionality without the overhead of full-featured clients.
    """
    
    def __init__(self, timeout: float = 30.0, user_agent: str = "OpenContext/1.0"):
        self.timeout = timeout
        self.default_headers = {
            "User-Agent": user_agent,
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate"
        }
    
    def get(
        self, 
        url: str, 
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, str]] = None
    ) -> 'HTTPResponse':
        """Make a GET request."""
        if params:
            query_string = urllib.parse.urlencode(params)
            url = f"{url}?{query_string}"
        
        return self._make_request("GET", url, headers=headers)
    
    def post(
        self, 
        url: str, 
        data: Optional[Union[str, bytes, Dict[str, Any]]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> 'HTTPResponse':
        """Make a POST request."""
        request_headers = self.default_headers.copy()
        if headers:
            request_headers.update(headers)
        
        # Handle JSON data
        if json_data:
            data = json.dumps(json_data).encode('utf-8')
            request_headers["Content-Type"] = "application/json"
        elif isinstance(data, dict):
            data = urllib.parse.urlencode(data).encode('utf-8')
            request_headers["Content-Type"] = "application/x-www-form-urlencoded"
        elif isinstance(data, str):
            data = data.encode('utf-8')
        
        return self._make_request("POST", url, data=data, headers=request_headers)
    
    def _make_request(
        self, 
        method: str, 
        url: str, 
        data: Optional[bytes] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> 'HTTPResponse':
        """Make HTTP request."""
        request_headers = self.default_headers.copy()
        if headers:
            request_headers.update(headers)
        
        req = urllib.request.Request(url, data=data, headers=request_headers, method=method)
        
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                content = response.read()
                return HTTPResponse(
                    status_code=response.getcode(),
                    headers=dict(response.getheaders()),
                    content=content,
                    url=response.geturl()
                )
        except urllib.error.HTTPError as e:
            return HTTPResponse(
                status_code=e.code,
                headers=dict(e.headers) if e.headers else {},
                content=e.read() if hasattr(e, 'read') else b'',
                url=url,
                error=str(e)
            )
        except Exception as e:
            return HTTPResponse(
                status_code=0,
                headers={},
                content=b'',
                url=url,
                error=str(e)
            )


class HTTPResponse:
    """HTTP response wrapper."""
    
    def __init__(
        self, 
        status_code: int, 
        headers: Dict[str, str], 
        content: bytes,
        url: str,
        error: Optional[str] = None
    ):
        self.status_code = status_code
        self.headers = headers
        self.content = content
        self.url = url
        self.error = error
    
    @property
    def text(self) -> str:
        """Get response text."""
        return self.content.decode('utf-8', errors='ignore')
    
    def json(self) -> Any:
        """Parse response as JSON."""
        return json.loads(self.text)
    
    @property
    def ok(self) -> bool:
        """Check if request was successful."""
        return 200 <= self.status_code < 300


class SimpleImageHash:
    """
    Lightweight image hashing as alternative to imagehash library.
    
    Provides basic perceptual hashing for duplicate detection.
    """
    
    @staticmethod
    def average_hash(image_path: str) -> str:
        """
        Compute average hash of image.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Hex string hash
        """
        try:
            # This is a simplified version - in production you might want
            # to use PIL or OpenCV for proper image processing
            import hashlib
            
            # For now, just hash the file content as a fallback
            with open(image_path, 'rb') as f:
                content = f.read()
                hash_obj = hashlib.md5(content)
                return hash_obj.hexdigest()[:16]  # 64-bit hash
                
        except Exception:
            # Return zero hash on error
            return "0" * 16
    
    @staticmethod
    def hamming_distance(hash1: str, hash2: str) -> int:
        """
        Calculate Hamming distance between two hashes.
        
        Args:
            hash1: First hash string
            hash2: Second hash string
            
        Returns:
            Hamming distance (number of different bits)
        """
        if len(hash1) != len(hash2):
            return max(len(hash1), len(hash2))
        
        # Convert hex to binary and compare
        try:
            bin1 = bin(int(hash1, 16))[2:].zfill(len(hash1) * 4)
            bin2 = bin(int(hash2, 16))[2:].zfill(len(hash2) * 4)
            
            return sum(c1 != c2 for c1, c2 in zip(bin1, bin2))
        except ValueError:
            return len(hash1)  # Maximum distance on error


# Create lightweight client instance
http_client = LightweightHTTP()

# Export main utilities
__all__ = [
    'LightweightHTTP',
    'HTTPResponse', 
    'SimpleImageHash',
    'http_client'
]