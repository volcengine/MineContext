# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
OpenContext module: prompt_manager
"""

import os
from typing import Dict
import yaml
from loguru import logger

class PromptManager:
    def __init__(self, prompt_config_path: str = None):
        self.prompts = {}
        if prompt_config_path and os.path.exists(prompt_config_path):
            with open(prompt_config_path, 'r', encoding='utf-8') as f:
                self.prompts = yaml.safe_load(f)
        else:
            logger.warning("Prompt config file not found, using default prompts.")
            raise FileNotFoundError("Prompt config file not found.")

    def get_prompt(self, name: str, default: str = None) -> str:
        keys = name.split('.')
        value = self.prompts
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                logger.warning(f"Prompt '{name}' not found.")
                return default
        return value if isinstance(value, str) else default

    def get_prompt_group(self, name: str) -> Dict[str, str]:
        keys = name.split('.')
        value = self.prompts
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                logger.warning(f"Prompt group '{name}' not found.")
                return {}
        return value if isinstance(value, dict) else {}

    def get_context_type_descriptions(self) -> str:
        """
        Get descriptions of all context types, formatted as a YAML-style string.
        """
        # Use the method in enums to get the descriptions
        from opencontext.models.enums import get_context_type_descriptions_for_prompts
        return get_context_type_descriptions_for_prompts()
    
    def get_context_type_descriptions_for_extraction(self) -> str:
        """
        Get context type descriptions for content extraction scenarios
        """
        from opencontext.models.enums import get_context_type_descriptions_for_extraction
        return get_context_type_descriptions_for_extraction()
    
    def get_context_type_descriptions_for_retrieval(self) -> str:
        """
        Get context type descriptions for retrieval scenarios
        """
        from opencontext.models.enums import get_context_type_descriptions_for_retrieval
        return get_context_type_descriptions_for_retrieval()