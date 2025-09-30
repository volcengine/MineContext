"""
Tool: tool_definitions
简化后的工具定义
"""

from context_lab.tools.retrieval_tools import *
from context_lab.tools.profile_tools import *
from context_lab.tools.operation_tools import *

# 基础检索工具
BASIC_RETRIEVAL_TOOLS = [
    {"type": "function", "function": TextSearchTool.get_definition()},
    {"type": "function", "function": FilterContextTool.get_definition()},
    {"type": "function", "function": DocumentRetrievalTool.get_definition()},
]

# 所有检索工具定义
ALL_RETRIEVAL_TOOL_DEFINITIONS = (
    BASIC_RETRIEVAL_TOOLS
)

ALL_PROFILE_TOOL_DEFINITIONS = [
  {"type": "function", "function": ProfileEntityTool.get_definition()},
]

WEB_SEARCH_TOOL_DEFINITION = [
  {"type": "function", "function": WebSearchTool.get_definition()},
]

ALL_TOOL_DEFINITIONS = ALL_RETRIEVAL_TOOL_DEFINITIONS + ALL_PROFILE_TOOL_DEFINITIONS + WEB_SEARCH_TOOL_DEFINITION