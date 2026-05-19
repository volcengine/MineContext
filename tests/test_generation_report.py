import datetime
import importlib.util
from pathlib import Path
import sys
import types
import unittest

fake_vlm_client = types.ModuleType("opencontext.llm.global_vlm_client")


async def _fake_generate_with_messages_async(*_args, **_kwargs):
    return ""


fake_vlm_client.generate_with_messages_async = _fake_generate_with_messages_async
fake_vlm_client.generate_with_messages = lambda *_args, **_kwargs: ""
sys.modules.setdefault("opencontext.llm.global_vlm_client", fake_vlm_client)

fake_debug_helper = types.ModuleType("opencontext.context_consumption.generation.debug_helper")


class _FakeDebugHelper:
    pass


fake_debug_helper.DebugHelper = _FakeDebugHelper
sys.modules.setdefault("opencontext.context_consumption.generation.debug_helper", fake_debug_helper)

fake_tool_definitions = types.ModuleType("opencontext.tools.tool_definitions")
fake_tool_definitions.ALL_TOOL_DEFINITIONS = []
sys.modules.setdefault("opencontext.tools.tool_definitions", fake_tool_definitions)

fake_tools_executor = types.ModuleType("opencontext.tools.tools_executor")


class _FakeToolsExecutor:
    pass


fake_tools_executor.ToolsExecutor = _FakeToolsExecutor
sys.modules.setdefault("opencontext.tools.tools_executor", fake_tools_executor)

module_path = (
    Path(__file__).resolve().parents[1]
    / "opencontext"
    / "context_consumption"
    / "generation"
    / "generation_report.py"
)
spec = importlib.util.spec_from_file_location("generation_report_for_test", module_path)
generation_report_module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(generation_report_module)
ReportGenerator = generation_report_module.ReportGenerator


class ReportGeneratorTest(unittest.TestCase):
    def test_normalizes_fenced_report_with_start_date_heading(self):
        generator = ReportGenerator.__new__(ReportGenerator)
        normalized = generator._normalize_report_content(
            "```markdown\n# 日报 - 2026年05月18日\n\ncontent\n```",
            datetime.date(2026, 5, 19),
        )

        self.assertEqual(normalized, "# 日报 - 2026年05月19日\n\ncontent")


if __name__ == "__main__":
    unittest.main()
