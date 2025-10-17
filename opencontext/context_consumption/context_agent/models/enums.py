#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Enum Definition Module
Defines all enumeration types to avoid magic strings
"""

from enum import Enum


class NodeType(str, Enum):
    """Node type enumeration"""

    INTENT = "intent"
    CONTEXT = "context"
    EXECUTE = "execute"
    REFLECT = "reflect"


class WorkflowStage(str, Enum):
    """Workflow stage enumeration"""

    INIT = "init"
    INTENT_ANALYSIS = "intent_analysis"
    CONTEXT_GATHERING = "context_gathering"
    EXECUTION = "execution"
    REFLECTION = "reflection"
    COMPLETED = "completed"
    FAILED = "failed"
    NEXT = "next"


class DataSource(str, Enum):
    """Data source type enumeration"""

    DOCUMENT = "document"  # Document library
    WEB_SEARCH = "web_search"  # Web search
    AGENT_MEMORY = "agent_memory"  # Agent memory
    CONTEXT_DB = "context_db"  # Context database
    CHAT_HISTORY = "chat_history"  # Chat history
    PROCESSED = "processed"  # Processed context
    ENTITY = "entity"  # Entity-related
    UNKNOWN = "unknown"  # Unknown source


class TaskStatus(str, Enum):
    """Task status enumeration"""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    INSUFFICIENT_INFO = "insufficient_info"


class ActionType(str, Enum):
    """Action type enumeration"""

    ANSWER = "answer"
    EDIT = "edit"
    CREATE_DOC = "create_doc"
    GENERATE = "generate"


class EventType(str, Enum):
    """Event type enumeration"""

    THINKING = "thinking"
    RUNNING = "running"
    DONE = "done"
    FAIL = "fail"
    COMPLETED = "completed"

    STREAM_CHUNK = "stream_chunk"
    STREAM_COMPLETE = "stream_complete"


class QueryType(str, Enum):
    """Query type enumeration - five categories"""

    SIMPLE_CHAT = "simple_chat"  # Simple chat (daily greetings, small talk, etc.)
    DOCUMENT_EDIT = "document_edit"  # Document editing and rewriting (preserving existing facts/not introducing new information)
    QA_ANALYSIS = "qa_analysis"  # Q&A (covering summarization, analysis, and dialogue based on documents and complex context)
    CONTENT_GENERATION = (
        "content_generation"  # Document content generation/expansion (allowing new information)
    )
    CLARIFICATION_NEEDED = (
        "clarification_needed"  # Query is too vague or ambiguous, needs user clarification
    )


class ContextSufficiency(str, Enum):
    """Context sufficiency enumeration"""

    SUFFICIENT = "sufficient"  # Sufficient
    PARTIAL = "partial"  # Partially sufficient
    INSUFFICIENT = "insufficient"  # Insufficient
    UNKNOWN = "unknown"  # Unknown


class ReflectionType(str, Enum):
    """Reflection type enumeration"""

    SUCCESS = "success"  # Successfully completed
    PARTIAL_SUCCESS = "partial_success"  # Partially successful
    FAILURE = "failure"  # Failed
    NEED_MORE_INFO = "need_more_info"  # Needs more information
    NEED_RETRY = "need_retry"  # Needs retry
