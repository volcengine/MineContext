import os
import tempfile
import unittest

import yaml

from opencontext.config.prompt_manager import PromptManager


class PromptManagerTest(unittest.TestCase):
    def test_user_prompts_are_saved_to_configured_user_directory(self):
        with tempfile.TemporaryDirectory() as base_dir:
            bundled_config_dir = os.path.join(base_dir, "readonly_config")
            user_config_dir = os.path.join(base_dir, "user_config")
            os.makedirs(bundled_config_dir)

            prompt_path = os.path.join(bundled_config_dir, "prompts_zh.yaml")
            with open(prompt_path, "w", encoding="utf-8") as f:
                yaml.safe_dump({"generation": {"example": {"system": "s", "user": "u"}}}, f)

            manager = PromptManager(prompt_path, user_prompts_dir=user_config_dir)

            self.assertTrue(manager.save_prompts({"generation": {"example": {"system": "new"}}}))
            self.assertTrue(os.path.exists(os.path.join(user_config_dir, "user_prompts_zh.yaml")))
            self.assertFalse(
                os.path.exists(os.path.join(bundled_config_dir, "user_prompts_zh.yaml"))
            )

    def test_screenshot_analyze_falls_back_to_legacy_prompt_name(self):
        with tempfile.TemporaryDirectory() as base_dir:
            prompt_path = os.path.join(base_dir, "prompts_en.yaml")
            with open(prompt_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(
                    {
                        "processing": {
                            "extraction": {
                                "screenshot_contextual_batch": {
                                    "system": "legacy system",
                                    "user": "legacy user",
                                }
                            }
                        }
                    },
                    f,
                )

            manager = PromptManager(prompt_path)

            self.assertEqual(
                manager.get_prompt_group("processing.extraction.screenshot_analyze"),
                {"system": "legacy system", "user": "legacy user"},
            )


if __name__ == "__main__":
    unittest.main()
