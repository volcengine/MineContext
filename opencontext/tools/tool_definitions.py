"""
Tool: tool_definitions
"""

from opencontext.tools.operation_tools import *
from opencontext.tools.profile_tools import *
from opencontext.tools.retrieval_tools import *

# Context retrieval tools (ChromaDB-based)
CONTEXT_RETRIEVAL_TOOLS = [
    {"type": "function", "function": ActivityContextTool.get_definition()},
    {"type": "function", "function": IntentContextTool.get_definition()},
    {"type": "function", "function": SemanticContextTool.get_definition()},
    {"type": "function", "function": ProceduralContextTool.get_definition()},
    {"type": "function", "function": StateContextTool.get_definition()},
]

# Document retrieval tools (SQLite-based)
DOCUMENT_RETRIEVAL_TOOLS = [
    {"type": "function", "function": GetDailyReportsTool.get_definition()},
    {"type": "function", "function": GetActivitiesTool.get_definition()},
    {"type": "function", "function": GetTipsTool.get_definition()},
    {"type": "function", "function": GetTodosTool.get_definition()},
]


ALL_PROFILE_TOOL_DEFINITIONS = [
    {"type": "function", "function": ProfileEntityTool.get_definition()},
]

WEB_SEARCH_TOOL_DEFINITION = [
    {"type": "function", "function": WebSearchTool.get_definition()},
]

ALL_RETRIEVAL_TOOL_DEFINITIONS = CONTEXT_RETRIEVAL_TOOLS + DOCUMENT_RETRIEVAL_TOOLS

ALL_TOOL_DEFINITIONS = (
    ALL_RETRIEVAL_TOOL_DEFINITIONS + ALL_PROFILE_TOOL_DEFINITIONS + WEB_SEARCH_TOOL_DEFINITION
)
