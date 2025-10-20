#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Core Data Model Definition
Use dataclass to define all data structures to ensure type safety
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from .enums import ActionType, ContextSufficiency, DataSource, QueryType, ReflectionType, TaskStatus


@dataclass
class ChatMessage:
    """Chat message"""

    role: str  # user, assistant, system
    content: str
    # timestamp: datetime = field(default_factory=datetime.now)
    # metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WebSearchResult:
    """Web search result"""

    title: str
    url: str
    snippet: str
    relevance_score: float = 1.0
    source: str = "web"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Query:
    """User query encapsulation"""

    text: str
    query_type: Optional[QueryType] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    selected_content: Optional[str] = None
    document_id: Optional[str] = None


@dataclass
class Entity:
    """Entity information"""

    text: str
    type: str
    confidence: float = 1.0
    normalized: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Intent:
    """Intent analysis result"""

    original_query: str
    query_type: QueryType
    enhanced_query: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContextItem:
    """A single context item"""

    source: DataSource
    content: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: Optional[str] = None
    relevance_score: float = 1.0
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_relevant: bool = True
    relevance_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source.value,
            "content": self.content,
            "title": self.title,
            "relevance_score": self.relevance_score,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "is_relevant": self.is_relevant,
            "relevance_reason": self.relevance_reason,
        }


@dataclass
class DocumentInfo:
    """Document context"""

    id: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    summary: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "summary": self.summary,
            "tags": self.tags,
        }


@dataclass
class ContextCollection:
    """Context collection"""

    items: List[ContextItem] = field(default_factory=list)
    sufficiency: ContextSufficiency = ContextSufficiency.UNKNOWN
    missing_sources: Set[DataSource] = field(default_factory=set)
    collection_metadata: Dict[str, Any] = field(default_factory=dict)
    current_document: Optional[DocumentInfo] = None
    chat_history: List[ChatMessage] = field(default_factory=list)
    selected_content: Optional[str] = None

    def add_item(self, item: ContextItem):
        """Add a context item"""
        self.items.append(item)

    def get_by_source(self, source: DataSource) -> List[ContextItem]:
        """Get context by data source"""
        return [item for item in self.items if item.source == source]

    def is_sufficient(self) -> bool:
        """Check if the context is sufficient"""
        return self.sufficiency == ContextSufficiency.SUFFICIENT

    def prepare_context(self) -> Dict[str, Any]:
        import json
        from dataclasses import asdict

        """Prepare execution context, optimize loading strategy based on query_type"""
        context = {}
        # Convert ChatMessage objects to dictionaries before serializing
        chat_history_dicts = [asdict(msg) for msg in self.chat_history]
        context["chat_history"] = json.dumps(chat_history_dicts, ensure_ascii=False)
        if self.current_document:
            context["current_document"] = json.dumps(
                self.current_document.to_dict(), ensure_ascii=False
            )
        if self.selected_content:
            context["selected_content"] = self.selected_content or ""
        if self.items:
            context["collected_contexts"] = json.dumps(
                [item.to_dict() for item in self.items], ensure_ascii=False
            )
        return context

    def get_summary(self) -> str:
        """Get a summary of the context"""
        source_counts = {}
        for item in self.items:
            source_counts[item.source] = source_counts.get(item.source, 0) + 1

        summary_parts = [f"{source.value}: {count}" for source, count in source_counts.items()]
        return f"Collected {len(self.items)} context items ({', '.join(summary_parts)}), sufficiency: {self.sufficiency.value}"

    def get_chat_history(self) -> List[Dict[str, str]]:
        """Get chat history as a list of dictionaries"""
        return [{"role": msg.role, "content": msg.content} for msg in self.chat_history]


@dataclass
class ExecutionStep:
    """Execution step"""

    action: ActionType
    description: str = ""
    dependencies: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    def to_dict(self):
        """Convert to a dictionary"""
        return {
            "action": self.action.value,
            "description": self.description,
            "dependencies": self.dependencies,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
        }


@dataclass
class ExecutionPlan:
    """Execution plan"""

    steps: List[ExecutionStep] = field(default_factory=list)
    current_step: int = 0
    total_steps: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary"""
        return {
            "steps": [step.to_dict() for step in self.steps],
            "current_step": self.current_step,
            "total_steps": self.total_steps,
        }

    def add_step(self, step: ExecutionStep):
        """Add an execution step"""
        self.steps.append(step)
        self.total_steps = len(self.steps)

    def get_current_step(self) -> Optional[ExecutionStep]:
        """Get the current step"""
        if 0 <= self.current_step < len(self.steps):
            return self.steps[self.current_step]
        return None

    def advance(self):
        """Advance to the next step"""
        if self.current_step < self.total_steps - 1:
            self.current_step += 1


@dataclass
class ExecutionResult:
    """Execution result"""

    success: bool
    plan: ExecutionPlan
    outputs: List[Any] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReflectionResult:
    """Reflection result"""

    reflection_type: ReflectionType
    success_rate: float
    summary: str
    issues: List[str] = field(default_factory=list)
    improvements: List[str] = field(default_factory=list)
    should_retry: bool = False
    retry_strategy: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
