# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
OpenContext module: image
"""

from typing import Optional

import imagehash
from PIL import Image


def calculate_bytes2phash(image_bytes: bytes) -> Optional[str]:
    """
    Calculate perceptual hash of image (cached).
    Uses difference hash instead of average hash for better performance.
    """
    try:
        import io

        from PIL import Image

        image = Image.open(io.BytesIO(image_bytes))
        hash_result = str(imagehash.dhash(image, hash_size=8))
        return hash_result
    except Exception:
        return None


def calculate_phash(path: str) -> Optional[str]:
    """
    Calculate perceptual hash of image file (cached).
    """
    try:
        from PIL import Image

        image = Image.open(path)
        return str(imagehash.dhash(image, hash_size=8))
    except Exception:
        return None


def resize_image(path: str, max_size: int, resize_quality: int) -> bool:
    """
    Scale image proportionally if size exceeds maximum limit.
    Optimization: uses more efficient scaling algorithm.
    """
    try:
        with Image.open(path) as img:
            if max_size and (img.width > max_size or img.height > max_size):
                img.thumbnail((max_size, max_size), Image.Resampling.BILINEAR)
                if path.lower().endswith((".jpg", ".jpeg")):
                    img.save(path, quality=resize_quality, format="JPEG", optimize=True)
                elif path.lower().endswith(".png"):
                    img.save(path, format="PNG", optimize=True, compress_level=6)
                else:
                    img.save(path, format=img.format if img.format else "PNG")
                return True
    except Exception as e:
        from opencontext.utils.logging_utils import get_logger

        logger = get_logger(__name__)
        logger.error(f"Failed to resize image {path}: {e}")
    return False
