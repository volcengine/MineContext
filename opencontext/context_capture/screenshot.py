#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0


"""
Screenshot capture component for periodic screen capturing
"""

import os
import threading
from datetime import datetime
from io import BytesIO
from typing import Any, Dict, List

from PIL import Image

from opencontext.context_capture import BaseCaptureComponent
from opencontext.models.context import RawContextProperties
from opencontext.models.enums import ContentFormat, ContextSource
from opencontext.utils.logger import LogManager

logger = LogManager.get_logger(__name__)


class ScreenshotCapture(BaseCaptureComponent):
    """
    Screenshot capture component for periodic screen capturing
    """

    def __init__(self):
        """
        Initialize screenshot capture component
        """
        super().__init__(
            name="ScreenshotCapture",
            description="Periodic screen capturing",
            source_type=ContextSource.SCREENSHOT,
        )
        self._screenshot_lib = None
        self._screenshot_count = 0
        self._last_screenshot_path = None
        self._last_screenshot_time = None
        self._screenshot_format = "png"
        self._screenshot_quality = 80
        self._screenshot_region = None
        self._save_screenshots = False
        self._screenshot_dir = None
        self._dedup_enabled = True
        self._last_screenshots: Dict[str, tuple[Image.Image, RawContextProperties]] = (
            {}
        )  # Used to store the last stable screenshot for each monitor
        self._similarity_threshold = 95  # Image similarity threshold (0-100), default 95
        self._max_image_size = None  # Add maximum image size
        self._resize_quality = 95  # Add image scaling quality
        self._lock = threading.RLock()

    def _initialize_impl(self, config: Dict[str, Any]) -> bool:
        """
        Initialize screenshot capture component

        Args:
            config (Dict[str, Any]): Component configuration

        Returns:
            bool: Whether initialization was successful
        """
        try:
            # Try to import screenshot library
            try:
                self._screenshot_lib = "mss"
                logger.info("Using mss library for screenshots")
            except ImportError:
                logger.error("Unable to import mss screenshot library, please install mss")
                return False

            # Set screenshot format
            if "screenshot_format" in config:
                self._screenshot_format = config["screenshot_format"].lower()
                if self._screenshot_format not in ["png", "jpg", "jpeg"]:
                    logger.warning(
                        f"Unsupported screenshot format: {self._screenshot_format}, using default format: png"
                    )
                    self._screenshot_format = "png"

            # Set screenshot quality
            if "screenshot_quality" in config:
                self._screenshot_quality = max(1, min(100, int(config["screenshot_quality"])))

            # Set screenshot region
            if "screenshot_region" in config:
                region = config["screenshot_region"]
                if isinstance(region, dict) and all(
                    k in region for k in ["left", "top", "width", "height"]
                ):
                    self._screenshot_region = (
                        int(region["left"]),
                        int(region["top"]),
                        int(region["left"]) + int(region["width"]),
                        int(region["top"]) + int(region["height"]),
                    )

            # Set whether to save screenshots
            storage_path = config.get("storage_path", "./screenshots")
            if storage_path:
                self._save_screenshots = True
                self._screenshot_dir = storage_path
                os.makedirs(self._screenshot_dir, exist_ok=True)
                logger.info(f"Screenshots will be saved to directory: {self._screenshot_dir}")

            # Set whether to enable deduplication
            self._dedup_enabled = config.get("dedup_enabled", True)

            # Set similarity threshold
            self._similarity_threshold = config.get("similarity_threshold", 98)

            # Set image scaling size and quality
            self._max_image_size = config.get("max_image_size", 2048)
            self._resize_quality = config.get("resize_quality", 95)

            return True
        except Exception as e:
            logger.exception(f"Failed to initialize screenshot capture component: {str(e)}")
            return False

    def _start_impl(self) -> bool:
        """
        Start screenshot capture component

        Returns:
            bool: Whether startup was successful
        """
        try:
            # Check if screenshot library is loaded
            if not self._screenshot_lib:
                logger.error(
                    "Screenshot library not loaded, cannot start screenshot capture component"
                )
                return False

            logger.info(
                f"Screenshot capture component started using {self._screenshot_lib} library"
            )
            return True
        except Exception as e:
            logger.exception(f"Failed to start screenshot capture component: {str(e)}")
            return False

    def _stop_impl(self, graceful: bool = True) -> bool:
        """
        Stop screenshot capture component. Before stopping, submit all pending stable screenshots based on graceful parameter.

        Returns:
            bool: Whether stopping was successful
        """
        try:
            if graceful:
                # Submit all remaining stable screenshots
                pending_contexts = list(item[1] for item in self._last_screenshots.values())
                if pending_contexts:
                    logger.info(
                        f"Submitting {len(pending_contexts)} pending screenshot contexts..."
                    )
                    if self._callback:
                        self._callback(pending_contexts)

            self._last_screenshots.clear()
            logger.info("Screenshot capture component stopped")
            return True
        except Exception as e:
            logger.exception(f"Failed to stop screenshot capture component: {str(e)}")
            return False

    def _create_new_context(
        self, screenshot_bytes: bytes, screenshot_format: str, timestamp: datetime, details: dict
    ) -> RawContextProperties:
        """Create a RawContextProperties object for a new screenshot"""
        screenshot_path = None
        if self._save_screenshots:
            monitor_id = details.get("monitor", "monitor_1")
            timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S_%f")
            filename = f"screenshot_{monitor_id}_{timestamp_str}.{self._screenshot_format}"
            filepath = os.path.join(self._screenshot_dir, filename)
            with open(filepath, "wb") as f:
                f.write(screenshot_bytes)
            screenshot_path = os.path.abspath(filepath)
            self._last_screenshot_path = screenshot_path

        metadata = {
            "format": screenshot_format,
            "timestamp": timestamp.isoformat(),
            "last_seen_timestamp": timestamp.isoformat(),
            "lib": self._screenshot_lib,
            "region": self._screenshot_region,
            "screenshot_format": screenshot_format,
            "screenshot_path": screenshot_path,
            "duration_count": 1,  # Initial count
        }
        metadata.update(details)
        metadata["tags"] = [
            "screenshot",
            screenshot_format,
            self._screenshot_lib,
            str(details.get("monitor", "monitor_1")),
        ]

        return RawContextProperties(
            source=ContextSource.SCREENSHOT,
            content_format=ContentFormat.IMAGE,
            content_path=screenshot_path,
            additional_info=metadata,
            create_time=timestamp,
        )

    def _capture_impl(self) -> List[RawContextProperties]:
        """
        Execute screenshot capture and return all captured screenshots at once.

        Returns:
            List[RawContextProperties]: List of captured context data
        """
        try:
            screenshots = self._take_screenshot()
            if not screenshots:
                return []

            captured_contexts = []
            now = datetime.now()

            for screenshot_bytes, screenshot_format, details in screenshots:
                new_ctx = self._create_new_context(
                    screenshot_bytes, screenshot_format, now, details
                )
                captured_contexts.append(new_ctx)
                self._screenshot_count += 1

            self._last_screenshot_time = now
            # logger.info(f"Screenshot capture completed, generated {len(captured_contexts)} new contexts.")
            return captured_contexts
        except Exception as e:
            logger.exception(f"Screenshot capture failed: {str(e)}")
            return []

    def _take_screenshot(self) -> list:
        """
        Capture screen screenshots using configured library

        Returns:
            list: (screenshot binary data, format, details_dict)
        """
        try:
            screenshots = []

            if self._screenshot_lib == "mss":
                import mss
                from PIL import Image

                with mss.mss() as sct:
                    monitors_to_capture = []
                    if self._screenshot_region:
                        monitors_to_capture.append(
                            {
                                "left": self._screenshot_region[0],
                                "top": self._screenshot_region[1],
                                "width": self._screenshot_region[2] - self._screenshot_region[0],
                                "height": self._screenshot_region[3] - self._screenshot_region[1],
                            }
                        )
                    else:
                        # sct.monitors[0] is all monitors, [1:] are individuals
                        monitors_to_capture.extend(sct.monitors[1:])

                    for i, monitor in enumerate(monitors_to_capture):
                        sct_img = sct.grab(monitor)
                        img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

                        # Convert to binary data
                        buffer = BytesIO()
                        if self._screenshot_format in ["jpg", "jpeg"]:
                            img.save(buffer, format="JPEG", quality=self._screenshot_quality)
                            format_name = "jpeg"
                        else:
                            img.save(buffer, format="PNG")
                            format_name = "png"

                        details = {"monitor": f"monitor_{i+1}", "coordinates": monitor}
                        screenshots.append((buffer.getvalue(), format_name, details))

            else:
                logger.error(f"Unsupported screenshot library: {self._screenshot_lib}")
                return []

            return screenshots
        except Exception as e:
            logger.exception(f"Screenshot failed: {str(e)}")
            return []

    def _get_config_schema_impl(self) -> Dict[str, Any]:
        """
        Get configuration schema implementation

        Returns:
            Dict[str, Any]: Configuration schema
        """
        return {
            "properties": {
                "capture_interval": {
                    "type": "number",
                    "description": "Screenshot capture interval (seconds)",
                    "default": 5.0,
                    "minimum": 0.1,
                },
                "screenshot_format": {
                    "type": "string",
                    "description": "Screenshot format (png, jpg, jpeg)",
                    "enum": ["png", "jpg", "jpeg"],
                    "default": "png",
                },
                "screenshot_quality": {
                    "type": "integer",
                    "description": "Screenshot quality (1-100, only valid for jpg/jpeg)",
                    "minimum": 1,
                    "maximum": 100,
                    "default": 80,
                },
                "screenshot_region": {
                    "type": "object",
                    "description": "Screenshot region (if not specified, capture entire screen)",
                    "properties": {
                        "left": {"type": "integer", "minimum": 0},
                        "top": {"type": "integer", "minimum": 0},
                        "width": {"type": "integer", "minimum": 1},
                        "height": {"type": "integer", "minimum": 1},
                    },
                    "required": ["left", "top", "width", "height"],
                },
                "storage_path": {"type": "string", "description": "Screenshot save directory"},
                "dedup_enabled": {
                    "type": "boolean",
                    "description": "Whether to enable screenshot deduplication (skip screenshots identical to the previous one)",
                    "default": True,
                },
                "similarity_threshold": {
                    "type": "number",
                    "description": "Image similarity threshold (0-100), higher values require more similarity. Default 98",
                    "default": 98,
                    "minimum": 0,
                    "maximum": 100,
                },
            }
        }

    def _validate_config_impl(self, config: Dict[str, Any]) -> bool:
        """
        Validate configuration implementation

        Args:
            config (Dict[str, Any]): Configuration to validate

        Returns:
            bool: Whether configuration is valid
        """
        try:
            # Validate capture interval
            if "capture_interval" in config:
                try:
                    interval = float(config["capture_interval"])
                    if interval <= 0:
                        logger.error(f"Capture interval must be greater than 0: {interval}")
                        return False
                except (ValueError, TypeError):
                    logger.error(f"Capture interval must be numeric: {config['capture_interval']}")
                    return False

            # Validate screenshot format
            if "screenshot_format" in config:
                format_value = config["screenshot_format"].lower()
                if format_value not in ["png", "jpg", "jpeg"]:
                    logger.error(
                        f"Unsupported screenshot format: {format_value}, supported formats: png, jpg, jpeg"
                    )
                    return False

            # Validate screenshot quality
            if "screenshot_quality" in config:
                try:
                    quality = int(config["screenshot_quality"])
                    if quality < 1 or quality > 100:
                        logger.error(f"Screenshot quality must be between 1-100: {quality}")
                        return False
                except (ValueError, TypeError):
                    logger.error(
                        f"Screenshot quality must be integer: {config['screenshot_quality']}"
                    )
                    return False

            # Validate similarity threshold
            if "similarity_threshold" in config:
                try:
                    threshold = float(config["similarity_threshold"])
                    if threshold < 0 or threshold > 100:
                        logger.error(f"Similarity threshold must be between 0-100: {threshold}")
                        return False
                except (ValueError, TypeError):
                    logger.error(
                        f"Similarity threshold must be numeric: {config['similarity_threshold']}"
                    )
                    return False

            # Validate screenshot region
            if "screenshot_region" in config:
                region = config["screenshot_region"]
                if not isinstance(region, dict):
                    logger.error(f"Screenshot region must be a dictionary: {region}")
                    return False

                required_keys = ["left", "top", "width", "height"]
                if not all(k in region for k in required_keys):
                    logger.error(
                        f"Screenshot region must contain the following keys: {', '.join(required_keys)}"
                    )
                    return False

                try:
                    left = int(region["left"])
                    top = int(region["top"])
                    width = int(region["width"])
                    height = int(region["height"])

                    if left < 0 or top < 0 or width <= 0 or height <= 0:
                        logger.error(
                            f"Screenshot region parameters invalid: left={left}, top={top}, width={width}, height={height}"
                        )
                        return False
                except (ValueError, TypeError):
                    logger.error(f"Screenshot region parameters must be integers")
                    return False

            # Validate screenshot save directory
            if self._save_screenshots:
                screenshot_dir = config["storage_path"]
                if not isinstance(screenshot_dir, str):
                    logger.error(f"Screenshot save directory must be a string: {screenshot_dir}")
                    return False

            return True
        except Exception as e:
            logger.exception(
                f"Failed to validate screenshot capture component configuration: {str(e)}"
            )
            return False

    def _get_status_impl(self) -> Dict[str, Any]:
        """
        Get status implementation

        Returns:
            Dict[str, Any]: Status information
        """
        return {
            "screenshot_lib": self._screenshot_lib,
            "screenshot_format": self._screenshot_format,
            "screenshot_quality": self._screenshot_quality,
            "screenshot_region": self._screenshot_region,
            "save_screenshots": self._save_screenshots,
            "screenshot_dir": self._screenshot_dir,
            "dedup_enabled": self._dedup_enabled,
            "similarity_threshold": self._similarity_threshold,
            "last_screenshot_time": (
                self._last_screenshot_time.isoformat() if self._last_screenshot_time else None
            ),
            "last_screenshot_path": self._last_screenshot_path,
        }

    def _get_statistics_impl(self) -> Dict[str, Any]:
        """
        Get statistics implementation

        Returns:
            Dict[str, Any]: Statistics information
        """
        active_contexts_info = {}
        for monitor_id, history in self._active_screenshots.items():
            active_contexts_info[monitor_id] = [
                {
                    "uuid": ctx.uuid,
                    "duration_count": ctx.metadata.get("duration_count"),
                    "timestamp": ctx.metadata.get("timestamp"),
                }
                for img, ctx in history
            ]

        return {
            "screenshot_count": self._screenshot_count,
            "active_screenshots": active_contexts_info,
        }

    def _reset_statistics_impl(self) -> None:
        """
        Reset statistics implementation
        """
        self._screenshot_count = 0
        self._active_screenshots = {}
        self._last_screenshot_time = None
        self._last_screenshot_path = None
