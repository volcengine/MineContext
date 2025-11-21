#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

import hashlib
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from opencontext.context_capture.base import BaseCaptureComponent
from opencontext.models.context import RawContextProperties
from opencontext.models.enums import ContentFormat, ContextSource
from opencontext.utils.logging_utils import get_logger

logger = get_logger(__name__)


class WebLinkCapture(BaseCaptureComponent):
    """ """

    def __init__(self):
        super().__init__(
            name="WebLinkCapture",
            description="Capture web links, render to PDF, and enqueue for processing",
            source_type=ContextSource.WEB_LINK,
        )
        self._output_dir: Path = Path("uploads/weblinks").resolve()
        self._timeout: int = 30000
        self._wait_until: str = "networkidle"
        self._pdf_options: Dict[str, Any] = {
            "format": "A4",
            "print_background": True,
            "landscape": False,
        }
        self._total_converted = 0
        self._last_activity_time: Optional[datetime] = None
        # Use a lock for thread-safe statistics updates
        self._stats_lock = threading.Lock()
        # Max workers for PDF conversion
        self._max_workers = 4
        # Temporary storage for URLs passed to the overridden capture method
        self._urls_to_process: List[str] = []

    def submit_url(self, url: str) -> List[RawContextProperties]:
        """
        Submits a single URL for immediate capture and processing.
        This is a convenience method that directly calls the main capture logic.
        """
        if not isinstance(url, str) or not url.lower().startswith(("http://", "https://")):
            logger.error(f"Invalid URL submitted: {url}")
            return []
        # Directly invoke the capture mechanism for a single URL
        return self.capture(urls=[url])

    def convert_url_to_pdf(
        self, url: str, filename_hint: Optional[str] = None
    ) -> Optional[Dict[str, str]]:
        """
        Converts a single URL to a PDF file.

        Returns:
            A dictionary containing the original URL and the path to the generated PDF, or None on failure.
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.error(
                "Playwright is not installed. Please install it with 'pip install playwright' and 'playwright install'."
            )
            return None
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
                page = browser.new_page()
                page.goto(url, timeout=self._timeout, wait_until=self._wait_until)
                page.emulate_media(media="screen")
                page.pdf(path=str(output_path), **self._pdf_options)
                browser.close()
            logger.info(f"Successfully converted URL '{url}' to PDF '{output_path}'")
            return {"url": url, "pdf_path": str(output_path)}
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
            self._max_workers = config.get("max_workers", 4)
            self._output_dir.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            logger.exception(f"WebLinkCapture initialize failed: {e}")
            return False

    def _start_impl(self) -> bool:
        # Nothing to start, the process is driven by direct calls to capture.
        return True

    def _stop_impl(self, graceful: bool = True) -> bool:
        # Nothing to stop, no background threads are managed by this component.
        return True

    def capture(self, urls: Optional[List[str]] = None) -> List[RawContextProperties]:
        """
        Overrides the base capture method to accept a list of URLs.
        It stores the URLs and then calls the base class's capture method.
        """
        if urls:
            self._urls_to_process = urls
        # Call the base implementation which will, in turn, call _capture_impl
        return super().capture()

    def _capture_impl(self) -> List[RawContextProperties]:
        """
        Processes the list of URLs stored in self._urls_to_process.
        """
        urls_to_process = self._urls_to_process
        if not urls_to_process:
            return []

        logger.info(f"Starting capture for {len(urls_to_process)} URLs.")
        results: List[RawContextProperties] = []
        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            # Submit all URL conversion tasks to the thread pool
            future_to_url = {
                executor.submit(self.convert_url_to_pdf, url): url for url in urls_to_process
            }

            for future in as_completed(future_to_url):
                try:
                    conversion_result = future.result()
                    if conversion_result:
                        pdf_path = conversion_result["pdf_path"]
                        url = conversion_result["url"]
                        raw_context = RawContextProperties(
                            source=ContextSource.WEB_LINK,
                            content_format=ContentFormat.FILE,
                            content_path=pdf_path,
                            content_text="",
                            create_time=datetime.now(),
                            filter_path=url,  # Use URL for deduplication
                            additional_info={"url": url, "pdf_path": pdf_path},
                            enable_merge=False,
                        )
                        results.append(raw_context)
                        with self._stats_lock:
                            self._total_converted += 1
                            self._last_activity_time = datetime.now()
                except Exception as exc:
                    url = future_to_url[future]
                    logger.error(f"URL '{url}' generated an exception during conversion: {exc}")

        # Clear the list for the next capture call
        self._urls_to_process = []

        logger.info(
            f"Finished capture. Successfully converted {len(results)} out of {len(urls_to_process)} URLs."
        )
        return results

    def _get_config_schema_impl(self) -> Dict[str, Any]:
        return {
            "properties": {
                "output_dir": {
                    "type": "string",
                    "description": "Directory to store generated PDFs",
                    "default": "uploads/weblinks",
                },
                "max_workers": {
                    "type": "integer",
                    "description": "Max number of parallel threads for PDF conversion.",
                    "default": 4,
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
                "pdf_format": {"type": "string", "description": "PDF page format", "default": "A4"},
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
            for k in ["max_workers", "timeout"]:
                if k in config:
                    v = config[k]
                    if not isinstance(v, int) or v < 1:
                        logger.error(f"{k} must be an integer >= 1")
                        return False
            return True
        except Exception as e:
            logger.exception(f"Config validation failed: {e}")
            return False

    def _get_status_impl(self) -> Dict[str, Any]:
        return {
            "output_dir": str(self._output_dir),
            "max_workers": self._max_workers,
            "last_activity_time": (
                self._last_activity_time.isoformat() if self._last_activity_time else None
            ),
        }

    def _get_statistics_impl(self) -> Dict[str, Any]:
        return {
            "total_converted": self._total_converted,
        }

    def _reset_statistics_impl(self) -> None:
        with self._stats_lock:
            self._total_converted = 0

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
