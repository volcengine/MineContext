#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Workflow State Management
Manages the state of the entire workflow.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..models.enums import WorkflowStage
from ..models.events import EventBuffer, StreamEvent
from ..models.schemas import (
    ChatMessage,
    ContextCollection,
    ExecutionPlan,
    ExecutionResult,
    Intent,
    Query,
    ReflectionResult,
)


@dataclass
class WorkflowMetadata:
    """Workflow metadata."""

    workflow_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    version: str = "1.0.0"
    tags: List[str] = field(default_factory=list)
    custom_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowState:
    """Workflow state."""

    # Core data
    query: Query
    stage: WorkflowStage = WorkflowStage.INIT

    # Results of each stage
    intent: Optional[Intent] = None
    contexts: ContextCollection = field(default_factory=ContextCollection)
    execution_plan: Optional[ExecutionPlan] = None
    execution_result: Optional[ExecutionResult] = None
    reflection: Optional[ReflectionResult] = None

    # Tool call history - track all tool calls and validations
    tool_history: List[Dict[str, Any]] = field(default_factory=list)

    # Streaming processing
    event_buffer: EventBuffer = field(default_factory=EventBuffer)
    streaming_enabled: bool = True
    final_content: str = ""
    final_method: str = ""

    # Metadata
    metadata: WorkflowMetadata = field(default_factory=WorkflowMetadata)

    # Errors and status
    errors: str = ""
    is_cancelled: bool = False
    retry_count: int = 0
    max_retries: int = 3

    def update_stage(self, new_stage: WorkflowStage):
        """Update the workflow stage."""
        self.stage = new_stage
        self.metadata.updated_at = datetime.now()

    def add_tool_history_entry(self, entry: Dict[str, Any]):
        """Add a tool history entry."""
        entry["timestamp"] = datetime.now().isoformat()
        self.tool_history.append(entry)
        self.metadata.updated_at = datetime.now()

    def get_tool_history_summary(self) -> str:
        """Get a summary of tool history for LLM context."""
        if not self.tool_history:
            return "No tool calls yet."

        summary_lines = []
        for i, entry in enumerate(self.tool_history, 1):
            entry_type = entry.get("type", "unknown")
            if entry_type == "tool_call":
                tool_calls = entry.get("tool_calls", [])
                tool_names = [
                    call.get("function", {}).get("name", "unknown") for call in tool_calls
                ]
                summary_lines.append(
                    f"Round {i}: Called {len(tool_calls)} tools - {', '.join(tool_names)}"
                )
            elif entry_type == "validation":
                result_count = entry.get("result_count", 0)
                filtered_count = entry.get("filtered_count", 0)
                feedback = entry.get("feedback", "")
                summary_lines.append(
                    f"  Validation: {filtered_count}/{result_count} results kept. {feedback}"
                )

        return "\n".join(summary_lines)

    def add_event(self, event: StreamEvent):
        """Add an event to the buffer."""
        if self.streaming_enabled:
            self.event_buffer.add(event)

    def add_error(self, error: str):
        """Add an error message."""
        self.errors += f"{error}\n"
        self.metadata.updated_at = datetime.now()

    def should_retry(self) -> bool:
        """Check if a retry is needed."""
        return (
            self.retry_count < self.max_retries
            and not self.is_cancelled
            and self.stage != WorkflowStage.COMPLETED
        )

    def increment_retry(self):
        """Increment the retry counter."""
        self.retry_count += 1

    def is_complete(self) -> bool:
        """Check if the workflow is complete."""
        return self.stage in [WorkflowStage.COMPLETED, WorkflowStage.FAILED]

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the state."""
        return {
            "workflow_id": self.metadata.workflow_id,
            "stage": self.stage.value,
            "query": self.query.text,
            "has_intent": self.intent is not None,
            "context_count": len(self.contexts.items),
            "context_sufficient": self.contexts.is_sufficient(),
            "has_execution_plan": self.execution_plan is not None,
            "has_execution_result": self.execution_result is not None,
            "has_reflection": self.reflection is not None,
            "error_count": len(self.errors),
            "retry_count": self.retry_count,
            "created_at": self.metadata.created_at.isoformat(),
            "updated_at": self.metadata.updated_at.isoformat(),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "query": {
                "text": self.query.text,
                "type": self.query.query_type.value if self.query.query_type else None,
                "timestamp": self.query.timestamp.isoformat(),
            },
            "stage": self.stage.value,
            "intent": (
                {
                    "query_type": self.intent.query_type.value,
                    "enhanced_query": self.intent.enhanced_query,
                    "entities": [{"text": e.text, "type": e.type} for e in self.intent.entities],
                    "confidence": self.intent.confidence,
                }
                if self.intent
                else None
            ),
            "contexts": {
                "count": len(self.contexts.items),
                "sufficiency": self.contexts.sufficiency.value,
                "summary": self.contexts.get_summary(),
            },
            "execution": (
                {
                    "success": self.execution_result.success,
                    "outputs_count": len(self.execution_result.outputs),
                    "errors": self.execution_result.errors,
                    "execution_time": self.execution_result.execution_time,
                }
                if self.execution_result
                else None
            ),
            "reflection": (
                {
                    "type": self.reflection.reflection_type.value,
                    "success_rate": self.reflection.success_rate,
                    "summary": self.reflection.summary,
                    "should_retry": self.reflection.should_retry,
                }
                if self.reflection
                else None
            ),
            "metadata": {
                "workflow_id": self.metadata.workflow_id,
                "session_id": self.metadata.session_id,
                "user_id": self.metadata.user_id,
                "created_at": self.metadata.created_at.isoformat(),
                "updated_at": self.metadata.updated_at.isoformat(),
            },
            "errors": self.errors,
            "retry_count": self.retry_count,
        }


class StateManager:
    """State manager."""

    def __init__(self):
        self.states: Dict[str, WorkflowState] = {}

    def create_state(self, query_obj: Query, **kwargs) -> WorkflowState:
        """Create a new workflow state."""
        metadata = WorkflowMetadata(
            session_id=kwargs.get("session_id"), user_id=kwargs.get("user_id")
        )

        state = WorkflowState(
            query=query_obj,
            metadata=metadata,
            streaming_enabled=kwargs.get("streaming_enabled", True),
        )

        # Add extra context
        if "chat_history" in kwargs:
            for chat in kwargs["chat_history"]:
                state.contexts.chat_history.append(ChatMessage(chat["role"], chat["content"]))
        if "selected_content" in kwargs:
            state.contexts.selected_content = kwargs["selected_content"]

        self.states[state.metadata.workflow_id] = state
        return state

    def get_state(self, workflow_id: str) -> Optional[WorkflowState]:
        """Get the workflow state."""
        return self.states.get(workflow_id)

    def update_state(self, workflow_id: str, updates: Dict[str, Any]):
        """Update the workflow state."""
        state = self.get_state(workflow_id)
        if state:
            for key, value in updates.items():
                if hasattr(state, key):
                    setattr(state, key, value)
            state.metadata.updated_at = datetime.now()

    def delete_state(self, workflow_id: str):
        """Delete the workflow state."""
        if workflow_id in self.states:
            del self.states[workflow_id]

    def get_active_states(self) -> List[WorkflowState]:
        """Get all active workflow states."""
        return [
            state
            for state in self.states.values()
            if not state.is_complete() and not state.is_cancelled
        ]

    def cleanup_old_states(self, hours: int = 24):
        """Clean up old workflow states."""
        from datetime import timedelta

        cutoff_time = datetime.now() - timedelta(hours=hours)

        to_delete = []
        for workflow_id, state in self.states.items():
            if state.metadata.updated_at < cutoff_time and state.is_complete():
                to_delete.append(workflow_id)

        for workflow_id in to_delete:
            self.delete_state(workflow_id)
