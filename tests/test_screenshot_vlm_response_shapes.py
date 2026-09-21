# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""Regression test for issue #326: a VLM answering with a top-level JSON array
instead of {"items": [...]} used to crash _process_vlm_single() with
"'list' object has no attribute 'get'". Heavy optional deps are stubbed.
"""

import asyncio
import base64
import datetime
import importlib
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
ONE_PIXEL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)
ITEM = '{"context_type": "activity_context", "title": "T", "summary": "S", "importance": 7}'
VLM_RESPONSE = {"text": ""}


def _load_processor():
    noop = lambda *args, **kwargs: None  # noqa: E731

    async def fake_vlm(messages, **kwargs):
        return VLM_RESPONSE["text"]

    def stub(name, **attrs):
        sys.modules[name] = module = types.ModuleType(name)
        module.__dict__.update(attrs)
        return module

    # Skip package __init__ side effects, keep real submodule resolution.
    pkgs = "llm storage tools monitoring context_processing context_processing.processor"
    for pkg in pkgs.split():
        stub("opencontext." + pkg).__path__ = [str(ROOT.joinpath("opencontext", *pkg.split(".")))]
    proc = "opencontext.context_processing.processor"
    stub("opencontext.llm.global_vlm_client", generate_with_messages_async=fake_vlm)
    stub("opencontext.llm.global_embedding_client", do_vectorize_async=noop)
    stub("opencontext.storage.global_storage", get_storage=noop)
    stub("opencontext.tools.tool_definitions", ALL_TOOL_DEFINITIONS=[])
    stub("opencontext.utils.image", calculate_phash=noop, resize_image=noop)
    stub("opencontext.monitoring.monitor", record_processing_error=noop)
    stub(proc + ".base_processor", BaseContextProcessor=object)
    stub(proc + ".entity_processor", refresh_entities=noop, validate_and_clean_entities=noop)
    sys.modules["opencontext.monitoring"].__dict__.update(
        increment_data_count=noop, increment_recording_stat=noop, record_processing_metrics=noop
    )
    import yaml

    with open(ROOT / "config" / "prompts_zh.yaml", encoding="utf-8") as handle:
        prompts = yaml.safe_load(handle)["processing"]["extraction"]["screenshot_analyze"]
    module = importlib.import_module(proc + ".screenshot_processor")
    module.get_prompt_group = lambda key: prompts
    return module


class ScreenshotVLMResponseShapeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sp = _load_processor()
        from opencontext.models.context import RawContextProperties
        from opencontext.models.enums import ContentFormat, ContextSource

        cls.tmpdir = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmpdir.cleanup)
        path = os.path.join(cls.tmpdir.name, "shot.png")
        with open(path, "wb") as handle:
            handle.write(ONE_PIXEL_PNG)
        cls.raw = RawContextProperties(
            source=ContextSource.SCREENSHOT,
            content_format=ContentFormat.IMAGE,
            content_path=path,
            content_text="",
            create_time=datetime.datetime(2026, 1, 2, 3, 4, 5),
        )

    def _titles(self, vlm_text):
        VLM_RESPONSE["text"] = vlm_text
        processor = self.sp.ScreenshotProcessor.__new__(self.sp.ScreenshotProcessor)
        items = asyncio.run(processor._process_vlm_single(self.raw))
        return [(i.extracted_data.title, i.extracted_data.importance) for i in items]

    def test_object_with_items_is_parsed(self):
        self.assertEqual(self._titles('{"items": [%s]}' % ITEM), [("T", 7)])

    def test_top_level_array_is_parsed(self):
        self.assertEqual(self._titles("[%s]" % ITEM), [("T", 7)])
        self.assertEqual(self._titles("```json\n[%s]\n```" % ITEM), [("T", 7)])

    def test_unusable_shapes_are_skipped_or_rejected_cleanly(self):
        self.assertEqual(self._titles('["not", "an", "item"]'), [])
        self.assertEqual(self._titles('{"items": "nope"}'), [])
        self.assertRaises(ValueError, self._titles, "42")

    def test_empty_response_still_raises_value_error(self):
        for text in ("", "null", "[]", "I am sorry, I cannot help with that."):
            with self.subTest(text=text), self.assertRaises(ValueError) as ctx:
                self._titles(text)
            self.assertIn("Empty VLM response", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
