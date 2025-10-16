# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
File utilities - Provides file operation helper functions
"""

import logging
import mimetypes
import os
from pathlib import Path
from typing import Any, List, Optional, Tuple

logger = logging.getLogger(__name__)


def ensure_dir(directory: str) -> bool:
    """
    Ensure directory exists, create if it doesn't exist

    Args:
        directory: Directory path

    Returns:
        Whether successfully created or already exists
    """
    try:
        Path(directory).mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Failed to create directory: {directory}, error: {e}")
        return False


def get_file_extension(file_path: str) -> str:
    """
    Get file extension (without dot)

    Args:
        file_path: File path

    Returns:
        File extension
    """
    return Path(file_path).suffix.lstrip(".")


def is_binary_file(file_path: str) -> bool:
    """
    Check if file is binary

    Args:
        file_path: File path

    Returns:
        Whether file is binary
    """
    # Check if file exists
    if not Path(file_path).exists():
        logger.warning(f"File does not exist: {file_path}")
        return False

    # Check by MIME type
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type and not mime_type.startswith("text/"):
        return True

    # Check for null bytes in first 4KB
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(4096)
            return b"\x00" in chunk
    except Exception as e:
        logger.error(f"Failed to read file: {file_path}, error: {e}")
        return False


def get_file_size(file_path: str) -> int:
    """
    Get file size in bytes

    Args:
        file_path: File path

    Returns:
        File size in bytes
    """
    try:
        return Path(file_path).stat().st_size
    except Exception as e:
        logger.error(f"Failed to get file size: {file_path}, error: {e}")
        return -1


def read_text_file(file_path: str, encoding: str = "utf-8") -> Optional[str]:
    """
    Read text file content

    Args:
        file_path: File path
        encoding: File encoding

    Returns:
        File content, None if read fails
    """
    try:
        with open(file_path, "r", encoding=encoding) as f:
            return f.read()
    except Exception as e:
        logger.error(f"Failed to read file: {file_path}, error: {e}")
        return None


def write_text_file(file_path: str, content: str, encoding: str = "utf-8") -> bool:
    """
    Write text file

    Args:
        file_path: File path
        content: File content
        encoding: File encoding

    Returns:
        Whether write succeeded
    """
    try:
        # Ensure directory exists
        ensure_dir(str(Path(file_path).parent))

        with open(file_path, "w", encoding=encoding) as f:
            f.write(content)
        return True
    except Exception as e:
        logger.error(f"Failed to write file: {file_path}, error: {e}")
        return False
