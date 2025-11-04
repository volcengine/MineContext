#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Reflection Node
Evaluates the execution results and provides suggestions for improvement
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from opencontext.llm.global_vlm_client import generate_with_messages_async

from ..core.state import WorkflowState
from ..models.enums import ContextSufficiency, EventType, NodeType, ReflectionType, WorkflowStage
from ..models.schemas import ReflectionResult
from .base import BaseNode


class ReflectionNode(BaseNode):
    """Reflection node"""

    def __init__(self, streaming_manager=None):
        super().__init__(NodeType.REFLECT, streaming_manager)

    async def process(self, state: WorkflowState) -> WorkflowState:
        """Process reflection"""
        await self.emit_stream_event(EventType.REFLECTING, "Evaluating task execution results...")

        # Update stage
        state.update_stage(WorkflowStage.REFLECTION)

        try:
            # 1. Evaluate execution results
            evaluation = await self._evaluate_execution(state)

            # 2. Analyze issues
            issues = await self._analyze_issues(state, evaluation)

            # 3. Generate improvement suggestions
            improvements = await self._generate_improvements(state, issues)

            # 4. Decide whether to retry
            should_retry, retry_strategy = await self._decide_retry(state, evaluation, issues)

            # 5. Generate summary
            summary = await self._generate_summary(state, evaluation)

            # Create reflection result
            state.reflection = ReflectionResult(
                reflection_type=evaluation["type"],
                success_rate=evaluation["success_rate"],
                summary=summary,
                issues=issues,
                improvements=improvements,
                should_retry=should_retry,
                retry_strategy=retry_strategy,
            )

            # Send completion event
            await self.emit_stream_event(
                EventType.NODE_COMPLETE,
                f"Reflection complete: {evaluation['type'].value}",
                progress=1.0,
                data={
                    "success_rate": evaluation["success_rate"],
                    "issue_count": len(issues),
                    "improvement_count": len(improvements),
                    "should_retry": should_retry,
                },
            )

            return state

        except Exception as e:
            self.logger.exception(f"Reflection failed: {e}")
            # Reflection failure should not cause the entire process to fail, create a default reflection
            state.reflection = ReflectionResult(
                reflection_type=ReflectionType.PARTIAL_SUCCESS,
                success_rate=0.5,
                summary="An error occurred during the reflection process, but the task has been executed",
                issues=[str(e)],
                improvements=[],
                should_retry=False,
            )
            return state

    async def _evaluate_execution(self, state: WorkflowState) -> Dict[str, Any]:
        """Evaluate execution results"""
        evaluation = {"type": ReflectionType.FAILURE, "success_rate": 0.0, "metrics": {}}

        # Check if there are execution results
        if not state.execution_result:
            evaluation["type"] = ReflectionType.FAILURE
            evaluation["success_rate"] = 0.0
            return evaluation

        exec_result = state.execution_result

        # Calculate success rate
        if exec_result.plan and exec_result.plan.steps:
            total_steps = len(exec_result.plan.steps)
            successful_steps = sum(
                1
                for step in exec_result.plan.steps
                if step.status and step.status.value == "success"
            )
            success_rate = successful_steps / total_steps if total_steps > 0 else 0.0
        else:
            success_rate = 1.0 if exec_result.success else 0.0

        evaluation["success_rate"] = success_rate

        # Determine reflection type
        if success_rate >= 0.9:
            evaluation["type"] = ReflectionType.SUCCESS
        elif success_rate >= 0.5:
            evaluation["type"] = ReflectionType.PARTIAL_SUCCESS
        else:
            evaluation["type"] = ReflectionType.FAILURE

        # Add metrics
        evaluation["metrics"] = {
            "total_outputs": len(exec_result.outputs),
            "total_errors": len(exec_result.errors),
            "execution_time": exec_result.execution_time,
            "context_sufficiency": (
                state.contexts.sufficiency.value if state.contexts else "unknown"
            ),
        }

        # Special case judgment
        if state.contexts and state.contexts.sufficiency == ContextSufficiency.INSUFFICIENT:
            evaluation["type"] = ReflectionType.NEED_MORE_INFO

        return evaluation

    async def _analyze_issues(self, state: WorkflowState, evaluation: Dict[str, Any]) -> List[str]:
        """Analyze issues"""
        issues = []

        # Check for errors
        if state.execution_result and state.execution_result.errors:
            for error in state.execution_result.errors:
                issues.append(f"Execution error: {error}")

        # Check context sufficiency
        if state.contexts and state.contexts.sufficiency == ContextSufficiency.INSUFFICIENT:
            missing_sources = [s.value for s in state.contexts.missing_sources]
            issues.append(
                f"Insufficient context information, missing data sources: {', '.join(missing_sources)}"
            )

        # Check execution time
        if evaluation["metrics"].get("execution_time", 0) > 30:
            issues.append(
                f"Execution time too long: {evaluation['metrics']['execution_time']:.1f}s"
            )

        # Check output quality (using LLM evaluation)
        if state.execution_result and state.execution_result.outputs:
            quality_issues = await self._analyze_output_quality(
                state.query.text, state.execution_result.outputs
            )
            issues.extend(quality_issues)

        return issues

    async def _analyze_output_quality(self, query: str, outputs: List[Any]) -> List[str]:
        """Analyze output quality"""
        issues = []

        try:
            # Use LLM to evaluate output quality
            output_summary = str(outputs)[:1000]  # Limit length

            prompt = f"""
            Evaluate whether the following output adequately answers the user's query.
            
            User query: {query}
            Output result: {output_summary}
            
            Please list the existing issues (if any). If there are no issues, return "None".
            """

            messages = [
                {"role": "system", "content": "You are a quality assessment expert."},
                {"role": "user", "content": prompt},
            ]

            response = await generate_with_messages_async(messages)

            if response and response.strip() != "None":
                # Parse issues
                for line in response.split("\n"):
                    line = line.strip()
                    if line and not line.startswith("#"):
                        issues.append(f"Output quality issue: {line}")

        except Exception as e:
            self.logger.error(f"Output quality analysis failed: {e}")

        return issues

    async def _generate_improvements(self, state: WorkflowState, issues: List[str]) -> List[str]:
        """Generate improvement suggestions"""
        improvements = []

        # Generate improvement suggestions based on issues
        for issue in issues:
            if "Insufficient context information" in issue:
                improvements.append("Collect more relevant context information")
                improvements.append("Try using web search to get the latest information")
            elif "Execution error" in issue:
                improvements.append("Check the validity of input parameters")
                improvements.append("Optimize the error handling mechanism")
            elif "Execution time too long" in issue:
                improvements.append("Optimize the algorithm or use caching")
                improvements.append("Consider parallel processing")
            elif "Output quality issue" in issue:
                improvements.append("Enhance the prompt to get better output")
                improvements.append("Add an output validation step")

        # Use LLM to generate more specific suggestions
        if issues:
            try:
                prompt = f"""
                Based on the following issues, provide specific improvement suggestions:
                
                List of issues:
                {chr(10).join(f'- {issue}' for issue in issues)}
                
                Original query: {state.query.text}
                
                Please provide 3-5 specific and feasible improvement suggestions.
                """

                messages = [
                    {"role": "system", "content": "You are a process optimization expert."},
                    {"role": "user", "content": prompt},
                ]

                response = await generate_with_messages_async(messages)

                # Parse suggestions
                for line in response.split("\n"):
                    line = line.strip()
                    if line and (line.startswith("-") or line.startswith("•") or line[0].isdigit()):
                        # Clean up format
                        suggestion = line.lstrip("-•0123456789. ")
                        if suggestion and suggestion not in improvements:
                            improvements.append(suggestion)

            except Exception as e:
                self.logger.error(f"Failed to generate improvement suggestions: {e}")

        # If there are no specific suggestions, add general ones
        if not improvements:
            improvements.append("Continue to monitor system performance")
            improvements.append("Collect user feedback for continuous improvement")

        return improvements[:5]  # Return at most 5 suggestions

    async def _decide_retry(
        self, state: WorkflowState, evaluation: Dict[str, Any], issues: List[str]
    ) -> tuple[bool, Optional[str]]:
        """Decide whether to retry"""
        should_retry = False
        retry_strategy = None

        # Check retry conditions
        if state.retry_count >= state.max_retries:
            # Maximum number of retries has been reached
            return False, None

        # Decide based on evaluation results
        if evaluation["type"] == ReflectionType.NEED_MORE_INFO:
            should_retry = True
            retry_strategy = "Retry after collecting more information"
        elif evaluation["type"] == ReflectionType.FAILURE and evaluation["success_rate"] < 0.3:
            # Severe failure, consider retrying
            if any("temporary" in issue or "network" in issue for issue in issues):
                should_retry = True
                retry_strategy = "Retry after a delay (possibly a temporary issue)"
            elif any("parameter" in issue for issue in issues):
                should_retry = True
                retry_strategy = "Retry after adjusting parameters"

        return should_retry, retry_strategy

    async def _generate_summary(self, state: WorkflowState, evaluation: Dict[str, Any]) -> str:
        """Generate summary"""
        # Build summary content
        summary_parts = []

        # Task completion status
        if evaluation["type"] == ReflectionType.SUCCESS:
            summary_parts.append("✅ Task completed successfully")
        elif evaluation["type"] == ReflectionType.PARTIAL_SUCCESS:
            summary_parts.append("⚠️ Task partially completed")
        elif evaluation["type"] == ReflectionType.FAILURE:
            summary_parts.append("❌ Task execution failed")
        elif evaluation["type"] == ReflectionType.NEED_MORE_INFO:
            summary_parts.append("ℹ️ More information needed")

        # Success rate
        summary_parts.append(f"Success rate: {evaluation['success_rate']:.1%}")

        # Key metrics
        metrics = evaluation.get("metrics", {})
        if metrics:
            if metrics.get("total_outputs", 0) > 0:
                summary_parts.append(f"Generated {metrics['total_outputs']} outputs")
            if metrics.get("total_errors", 0) > 0:
                summary_parts.append(f"Encountered {metrics['total_errors']} errors")
            if metrics.get("execution_time", 0) > 0:
                summary_parts.append(f"Took {metrics['execution_time']:.1f} seconds")

        # Main achievements
        if state.execution_result and state.execution_result.outputs:
            for output in state.execution_result.outputs[:2]:  # Show at most 2
                if isinstance(output, dict):
                    output_type = output.get("type", "output")
                    if output_type == "document_created":
                        summary_parts.append(
                            f"📄 Document created: {output.get('title', 'untitled')}"
                        )
                    elif output_type == "summary":
                        summary_parts.append("📝 Summary generated")
                    elif output_type == "analysis":
                        summary_parts.append("📊 Analysis completed")

        return " | ".join(summary_parts)
