#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

import hashlib
import queue
import re
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from opencontext.context_capture.base import BaseCaptureComponent
from opencontext.models.context import RawContextProperties
from opencontext.models.enums import ContentFormat, ContextSource
from opencontext.utils.logging_utils import get_logger

logger = get_logger(__name__)


class WebLinkCapture(BaseCaptureComponent):
    def __init__(self):
        super().__init__(
            name="WebLinkCapture",
            description="Capture web links, render to PDF, and enqueue for processing",
            source_type=ContextSource.WEB_LINK,
        )
        self._output_dir: Path = Path("uploads/weblinks").resolve()
        self._queue: "queue.Queue[Dict[str, Optional[str]]]" = queue.Queue(maxsize=100)
        self._timeout: int = 30000
        self._wait_until: str = "networkidle"
        self._pdf_options: Dict[str, Any] = {
            "format": "A4",
            "print_background": True,
            "landscape": False,
        }
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_worker = threading.Event()
        self._total_converted = 0
        self._last_activity_time: Optional[datetime] = None

    def submit_url(self, url: str, filename_hint: Optional[str] = None) -> bool:
        try:
            if not isinstance(url, str) or not url.lower().startswith(("http://", "https://")):
                logger.error(f"Invalid URL: {url}")
                return False
            self._queue.put({"url": url, "filename_hint": filename_hint}, block=False)
            return True
        except queue.Full:
            logger.error("WebLink queue is full")
            return False
        except Exception as e:
            logger.exception(f"Failed to submit URL: {e}")
            return False

    def convert_url_to_pdf(self, url: str, filename_hint: Optional[str] = None) -> Optional[str]:
        try:
            from playwright.sync_api import sync_playwright
        except Exception as e:
            logger.error(f"Playwright not available: {e}")
            return None

        safe_name = self._make_safe_filename(url, filename_hint)
        output_path = self._output_dir / f"{safe_name}.pdf"

        try:
            self._output_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.exception(f"Failed to create output dir {self._output_dir}: {e}")
            return None

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context()
                page = context.new_page()
                page.goto(url, timeout=self._timeout, wait_until=self._wait_until)
                try:
                    title = page.title()
                except Exception:
                    title = None
                page.emulate_media(media="screen")
                page.pdf(
                    path=str(output_path),
                    format=self._pdf_options.get("format", "A4"),
                    print_background=self._pdf_options.get("print_background", True),
                    landscape=self._pdf_options.get("landscape", False),
                )
                context.close()
                browser.close()
            return str(output_path)
        except Exception as e:
            logger.exception(f"Failed to render URL to PDF: {url}, error: {e}")
            return None

    def _initialize_impl(self, config: Dict[str, Any]) -> bool:
        try:
            output_dir = config.get("output_dir")
            if output_dir:
                self._output_dir = Path(output_dir).expanduser().resolve()
            self._timeout = int(config.get("timeout", 30000))
            self._wait_until = str(config.get("wait_until", "networkidle"))
            self._pdf_options = {
                "format": config.get("pdf_format", "A4"),
                "print_background": bool(config.get("print_background", True)),
                "landscape": bool(config.get("landscape", False)),
            }
            queue_maxsize = int(config.get("queue_maxsize", 100))
            if queue_maxsize != self._queue.maxsize:
                self._queue = queue.Queue(maxsize=queue_maxsize)
            self._output_dir.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            logger.exception(f"WebLinkCapture initialize failed: {e}")
            return False

    def _start_impl(self) -> bool:
        try:
            if not self._worker_thread or not self._worker_thread.is_alive():
                self._stop_worker.clear()
                self._worker_thread = threading.Thread(
                    target=self._worker_loop, name="weblink_worker", daemon=True
                )
                self._worker_thread.start()
            return True
        except Exception as e:
            logger.exception(f"WebLinkCapture start failed: {e}")
            return False

    def _stop_impl(self, graceful: bool = True) -> bool:
        try:
            self._stop_worker.set()
            if self._worker_thread and self._worker_thread.is_alive():
                self._worker_thread.join(timeout=10 if graceful else 1)
            return True
        except Exception as e:
            logger.exception(f"WebLinkCapture stop failed: {e}")
            return False

    def _capture_impl(self) -> List[RawContextProperties]:
        results: List[RawContextProperties] = []
        try:
            task = self._queue.get_nowait()
        except queue.Empty:
            return []

        try:
            url = task.get("url") or ""
            if not url:
                return []

            pdf_path = self.convert_url_to_pdf(url, task.get("filename_hint"))
            if not pdf_path:
                return []

            self._total_converted += 1
            self._last_activity_time = datetime.now()
            raw = RawContextProperties(
                source=ContextSource.WEB_LINK,
                content_format=ContentFormat.FILE,
                content_path=pdf_path,
                content_text="",
                create_time=datetime.now(),
                additional_info={
                    "url": url,
                    "pdf_path": pdf_path,
                },
                enable_merge=False,
            )
            results.append(raw)
            return results
        except Exception as e:
            logger.exception(f"WebLinkCapture capture failed: {e}")
            return []

    def _get_config_schema_impl(self) -> Dict[str, Any]:
        return {
            "properties": {
                "output_dir": {
                    "type": "string",
                    "description": "Directory to store generated PDFs",
                    "default": "uploads/weblinks",
                },
                "queue_maxsize": {
                    "type": "integer",
                    "description": "Max queue size",
                    "minimum": 1,
                    "default": 100,
                },
                "timeout": {
                    "type": "integer",
                    "description": "Page load timeout (ms)",
                    "minimum": 1000,
                    "default": 30000,
                },
                "wait_until": {
                    "type": "string",
                    "description": "Wait condition for page.goto",
                    "default": "networkidle",
                },
                "pdf_format": {
                    "type": "string",
                    "description": "PDF page format",
                    "default": "A4",
                },
                "print_background": {
                    "type": "boolean",
                    "description": "Print CSS backgrounds",
                    "default": True,
                },
                "landscape": {
                    "type": "boolean",
                    "description": "Landscape orientation",
                    "default": False,
                },
            }
        }

    def _validate_config_impl(self, config: Dict[str, Any]) -> bool:
        try:
            if "output_dir" in config and not isinstance(config["output_dir"], str):
                logger.error("output_dir must be a string")
                return False
            for k in ["queue_maxsize", "timeout"]:
                if k in config:
                    v = config[k]
                    if not isinstance(v, int) or v < 1:
                        logger.error(f"{k} must be integer >= 1")
                        return False
            return True
        except Exception as e:
            logger.exception(f"Config validation failed: {e}")
            return False

    def _get_status_impl(self) -> Dict[str, Any]:
        return {
            "output_dir": str(self._output_dir),
            "queue_size": self._queue.qsize(),
            "last_activity_time": (
                self._last_activity_time.isoformat() if self._last_activity_time else None
            ),
        }

    def _get_statistics_impl(self) -> Dict[str, Any]:
        return {
            "total_converted": self._total_converted,
        }

    def _reset_statistics_impl(self) -> None:
        self._total_converted = 0
        with self._queue.mutex:
            self._queue.queue.clear()

    def _worker_loop(self):
        while not self._stop_worker.is_set():
            try:
                self.capture()
                self._stop_worker.wait(1.0)
            except Exception as e:
                logger.exception(f"Worker loop error: {e}")
                self._stop_worker.wait(2.0)

    def _make_safe_filename(self, url: str, filename_hint: Optional[str]) -> str:
        if filename_hint:
            base = filename_hint
        else:
            try:
                from urllib.parse import urlparse

                p = urlparse(url)
                hostname = p.hostname or "page"
                base = hostname
            except Exception:
                base = "page"
        base = re.sub(r"[^a-zA-Z0-9._-]", "_", base)[:80]
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:10]
        return f"{base}_{digest}"
