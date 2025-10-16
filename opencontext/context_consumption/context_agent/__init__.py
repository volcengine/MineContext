"""
Context Agent Package
智能上下文处理代理
"""

from .agent import ContextAgent, process_query, process_query_stream

__version__ = "1.0.0"
__all__ = ["ContextAgent", "process_query", "process_query_stream"]
