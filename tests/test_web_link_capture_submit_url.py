# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""Regression tests for WebLinkCapture.submit_url().

opencontext/server/routes/documents.py::upload_weblink() calls
``component.submit_url(request.url, request.filename_hint)``. submit_url() used to
accept only ``url``, so every POST /api/weblinks/upload raised
``TypeError: submit_url() takes 2 positional arguments but 3 were given``, which the
route's blanket ``except Exception`` turned into a generic HTTP 500.
"""

import inspect
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# opencontext.context_capture.__init__ eagerly imports capture backends that need
# optional deps (mss, PIL, watchdog); skip it but keep real submodule resolution.
_pkg = types.ModuleType("opencontext.context_capture")
_pkg.__path__ = [str(ROOT / "opencontext" / "context_capture")]
sys.modules.setdefault("opencontext.context_capture", _pkg)

from opencontext.context_capture.web_link_capture import WebLinkCapture  # noqa: E402


class WebLinkCaptureSubmitUrlTest(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.component = WebLinkCapture()
        self.assertTrue(self.component.initialize({"output_dir": self.tmpdir.name}))
        self.assertTrue(self.component.start())
        self.addCleanup(self.component.stop)

        def fake_convert(url, filename_hint=None):
            self.calls.append((url, filename_hint))
            path = (
                Path(self.tmpdir.name)
                / f"{self.component._make_safe_filename(url, filename_hint)}.md"
            )
            path.write_text("stub", encoding="utf-8")
            return {"url": url, "md_path": str(path)}

        self.component.convert_url_to_markdown = fake_convert

    def test_route_call_signature_is_accepted(self):
        """The route passes two positional args; submit_url must accept them."""
        route_source = (ROOT / "opencontext" / "server" / "routes" / "documents.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("component.submit_url(request.url, request.filename_hint)", route_source)
        self.assertIn("filename_hint", inspect.signature(WebLinkCapture.submit_url).parameters)
        results = self.component.submit_url("https://example.com/page", "my-page")
        self.assertEqual(len(results), 1)

    def test_filename_hint_reaches_the_converter(self):
        self.component.submit_url("https://example.com/page", "my-page")
        self.assertEqual(self.calls, [("https://example.com/page", "my-page")])
        self.assertTrue(
            any(p.name.startswith("my-page") for p in Path(self.tmpdir.name).glob("*.md"))
        )
        self.assertEqual(self.component._filename_hints, {})

    def test_submit_url_without_hint_still_works(self):
        self.assertEqual(len(self.component.submit_url("https://example.com/page")), 1)
        self.assertEqual(self.calls, [("https://example.com/page", None)])

    def test_invalid_url_is_still_rejected(self):
        self.assertEqual(self.component.submit_url("ftp://example.com/x", "hint"), [])
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()
