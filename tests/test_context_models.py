import unittest

from opencontext.models.context import ExtractedData
from opencontext.models.enums import ContextType


class ExtractedDataTest(unittest.TestCase):
    def test_coerces_non_string_summary_and_title(self):
        extracted = ExtractedData(
            title={"text": "Dashboard"},
            summary=["Step 1: open app", "Step 2: start recording"],
            keywords=["recording", {"kind": "screen"}],
            entities="MineContext",
            context_type=ContextType.ACTIVITY_CONTEXT,
        )

        self.assertEqual(extracted.title, '{"text": "Dashboard"}')
        self.assertEqual(extracted.summary, "Step 1: open app\nStep 2: start recording")
        self.assertEqual(extracted.keywords, ["recording", '{"kind": "screen"}'])
        self.assertEqual(extracted.entities, ["MineContext"])


if __name__ == "__main__":
    unittest.main()
