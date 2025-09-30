"""
Tool: tool_definitions
"""

from context_lab.tools.retrieval_tools import *
from context_lab.tools.profile_tools import *
from context_lab.tools.operation_tools import *

BASIC_RETRIEVAL_TOOLS = [
    {"type": "function", "function": TextSearchTool.get_definition()},
    {"type": "function", "function": FilterContextTool.get_definition()},
    {"type": "function", "function": DocumentRetrievalTool.get_definition()},
]

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