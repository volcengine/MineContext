#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Execution Node
Executes specific tasks
"""

from datetime import datetime
from typing import Any, Dict

from opencontext.config.global_config import get_prompt_group
from opencontext.llm.global_vlm_client import generate_stream_for_agent
from opencontext.storage.global_storage import get_storage

from ..core.state import StreamEvent, WorkflowState
from ..models.enums import ActionType, EventType, NodeType, TaskStatus, WorkflowStage
from ..models.schemas import ExecutionPlan, ExecutionResult, ExecutionStep, QueryType
from .base import BaseNode


class ExecutorNode(BaseNode):
    """Execution node"""

    def __init__(self, streaming_manager=None):
        super().__init__(NodeType.EXECUTE, streaming_manager)
        self.storage = get_storage()

    async def process(self, state: WorkflowState) -> WorkflowState:
        """Process execution"""
        state.update_stage(WorkflowStage.EXECUTION)
        await self.streaming_manager.emit(
            StreamEvent(
                type=EventType.THINKING,
                content="Starting to execute the task...",
                stage=WorkflowStage.EXECUTION,
                progress=0.0,
            )
        )
        plan = await self._generate_execution_plan(state)
        await self.streaming_manager.emit(
            StreamEvent(
                type=EventType.DONE,
                content="Execution plan has been generated",
                stage=WorkflowStage.EXECUTION,
                progress=0.0,
                metadata={"plan": plan.to_dict()},
            )
        )
        state.execution_plan = plan
        outputs = []
        errors = []
        total_steps = len(plan.steps)
        for i, step in enumerate(plan.steps):
            progress = (i + 1) / total_steps
            await self.streaming_manager.emit(
                StreamEvent(
                    type=EventType.RUNNING,
                    content=f"Executing step {i+1}/{total_steps}: {step.description}",
                    stage=WorkflowStage.EXECUTION,
                    progress=progress,
                )
            )
            step_result = await self._execute_step(step, state)
            outputs.append(step_result["output"])
            step.status = TaskStatus.SUCCESS
            step.result = step_result["output"]
            step.end_time = datetime.now()
        state.execution_result = ExecutionResult(
            success=len(errors) == 0,
            plan=plan,
            outputs=outputs,
            errors=errors,
            execution_time=(
                (datetime.now() - plan.steps[0].start_time).total_seconds() if plan.steps else 0
            ),
        )
        # print(f"Task execution completed, {len(outputs)} successful, {len(errors)} failed")
        await self.streaming_manager.emit(
            StreamEvent(
                type=EventType.DONE,
                content=f"Task execution completed, {len(outputs)} successful, {len(errors)} failed",
                stage=WorkflowStage.EXECUTION,
                progress=1.0,
            )
        )
        return state

    async def _generate_execution_plan(self, state: WorkflowState) -> ExecutionPlan:
        """Generate execution plan"""
        plan = ExecutionPlan()
        query_type = state.intent.query_type
        if query_type == QueryType.DOCUMENT_EDIT:
            step = ExecutionStep(action=ActionType.EDIT)
            plan.add_step(step)
        elif query_type == QueryType.QA_ANALYSIS:
            step = ExecutionStep(action=ActionType.ANSWER)
            plan.add_step(step)
        elif query_type == QueryType.CONTENT_GENERATION:
            step = ExecutionStep(action=ActionType.GENERATE)
            plan.add_step(step)
        return plan

    async def _execute_step(self, step: ExecutionStep, state: WorkflowState) -> Dict[str, Any]:
        """Execute a single step"""
        step.start_time = datetime.now()
        step.status = TaskStatus.RUNNING
        if step.action == ActionType.GENERATE:
            result = await self._execute_generate(state)
        elif step.action == ActionType.EDIT:
            result = await self._execute_edit(state)
        # elif step.action == ActionType.CREATE_DOC:
        #     result = await self._execute_create_doc(state)
        elif step.action == ActionType.ANSWER:
            result = await self._execute_answer(state)
        state.final_content = result["output"].get("content", "")
        state.final_method = step.action.value
        return result

    async def _execute_generate(self, state: WorkflowState) -> Dict[str, Any]:
        """Execute generation task with streaming"""
        prompt_group = get_prompt_group("chat_workflow.executor.generate")

        system_prompt = prompt_group["system"]

        context = state.contexts.prepare_context()
        user_prompt = prompt_group["user"]
        user_prompt = user_prompt.format(
            query=state.intent.original_query,
            enhanced_query=state.intent.enhanced_query,
            collected_contexts=context.get("collected_contexts", ""),
            chat_history=context.get("chat_history", ""),
            current_document=context.get("current_document", ""),
            selected_content=context.get("selected_content", ""),
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        # Use streaming generation
        full_content = ""
        chunk_index = 0
        async for chunk in generate_stream_for_agent(messages):
            if chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if hasattr(delta, "content") and delta.content:
                    full_content += delta.content
                    # Emit streaming chunk event
                    await self.streaming_manager.emit(
                        StreamEvent(
                            type=EventType.STREAM_CHUNK,
                            content=delta.content,
                            stage=WorkflowStage.EXECUTION,
                            progress=0.5,  # Progress is unknown during streaming
                            metadata={"index": chunk_index},
                        )
                    )
                    chunk_index += 1

        return {"success": True, "output": {"type": "generated_content", "content": full_content}}

    async def _execute_edit(self, state: WorkflowState) -> Dict[str, Any]:
        """Execute edit/rewrite task with streaming"""
        context = state.contexts.prepare_context()
        prompt_group = get_prompt_group("chat_workflow.executor.edit")

        system_prompt = prompt_group["system"]
        user_prompt = prompt_group["user"]
        user_prompt = user_prompt.format(
            query=state.intent.original_query,
            enhanced_query=state.intent.enhanced_query,
            collected_contexts=context.get("collected_contexts", ""),
            chat_history=context.get("chat_history", ""),
            current_document=context.get("current_document", ""),
            selected_content=context.get("selected_content", ""),
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        # Use streaming generation
        full_content = ""
        chunk_index = 0
        async for chunk in generate_stream_for_agent(messages):
            if chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if hasattr(delta, "content") and delta.content:
                    full_content += delta.content
                    # Emit streaming chunk event
                    await self.streaming_manager.emit(
                        StreamEvent(
                            type=EventType.STREAM_CHUNK,
                            content=delta.content,
                            stage=WorkflowStage.EXECUTION,
                            progress=0.5,
                            metadata={"index": chunk_index},
                        )
                    )
                    chunk_index += 1

        return {"success": True, "output": {"type": "edited_content", "content": full_content}}

    # async def _execute_create_doc(self, state: WorkflowState) -> Dict[str, Any]:
    #     """Execute create document task"""
    #     generated_content = None
    #     if state.execution_result and state.execution_result.outputs:
    #         for output in state.execution_result.outputs:
    #             if output.get("type") == "generated_content":
    #                 generated_content = output.get("content")
    #                 break

    #     if not generated_content:
    #         return {"success": False, "error": "No content available to create a document"}

    #     # Create document
    #     title = params.get("title", f"Document_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    #     doc_id = self.storage.insert_vaults(
    #         title=title,
    #         content=generated_content,
    #         summary=generated_content[:200] if len(generated_content) > 200 else generated_content,
    #         document_type=VaultType.NOTE.value,
    #         tags=params.get("tags", [])
    #     )

    #     return {
    #         "success": True,
    #         "output": {
    #             "type": "document_created",
    #             "doc_id": doc_id,
    #             "title": title
    #         }
    #     }

    async def _execute_answer(self, state: WorkflowState) -> Dict[str, Any]:
        """Execute answer task - intelligently handle Q&A, summarization, analysis, etc. with streaming"""
        context = state.contexts.prepare_context()
        prompt_group = get_prompt_group("chat_workflow.executor.answer")
        system_prompt = prompt_group["system"]
        user_prompt = prompt_group["user"]
        user_prompt = user_prompt.format(
            query=state.intent.original_query,
            enhanced_query=state.intent.enhanced_query,
            collected_contexts=context.get("collected_contexts", ""),
            chat_history=context.get("chat_history", ""),
            current_document=context.get("current_document", ""),
            selected_content=context.get("selected_content", ""),
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        # Use streaming generation
        full_content = ""
        chunk_index = 0
        async for chunk in generate_stream_for_agent(messages):
            if chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if hasattr(delta, "content") and delta.content:
                    full_content += delta.content
                    # Emit streaming chunk event
                    await self.streaming_manager.emit(
                        StreamEvent(
                            type=EventType.STREAM_CHUNK,
                            content=delta.content,
                            stage=WorkflowStage.EXECUTION,
                            progress=0.5,
                            metadata={"index": chunk_index},
                        )
                    )
                    chunk_index += 1

        return {"success": True, "output": {"type": "answer", "content": full_content}}
