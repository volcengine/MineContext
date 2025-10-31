#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Intelligent Completion Service
An intelligent completion system based on vector retrieval and LLM generation
"""

import hashlib
import re
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from opencontext.config.global_config import get_prompt_manager
from opencontext.context_consumption.completion.completion_cache import get_completion_cache
from opencontext.llm.global_vlm_client import generate_with_messages
from opencontext.models.enums import CompletionType
from opencontext.storage.global_storage import get_storage
from opencontext.tools.retrieval_tools.semantic_context_tool import SemanticContextTool
from opencontext.utils.logging_utils import get_logger

logger = get_logger(__name__)


class CompletionSuggestion:
    """Completion suggestion data structure"""

    def __init__(
        self,
        text: str,
        completion_type: CompletionType,
        confidence: float,
        context_used: List[str] = None,
    ):
        self.text = text
        self.completion_type = completion_type
        self.confidence = confidence  # 0.0 - 1.0
        self.context_used = context_used or []
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            "text": self.text,
            "type": self.completion_type.value,
            "confidence": self.confidence,
            "context_used": self.context_used,
            "timestamp": self.timestamp.isoformat(),
        }


class CompletionService:
    """Core class for the intelligent completion service"""

    def __init__(self):
        self.storage = None
        self.embedding_client = None
        self.chat_client = None
        self.cache = get_completion_cache()  # Use a dedicated cache manager
        self.prompt_manager = None  # Prompt manager
        self.semantic_search_tool = None  # SemanticContextTool instance

        # Completion configuration
        self.max_context_length = 500  # Maximum context length
        self.max_suggestions = 3  # Maximum number of suggestions
        self.min_trigger_length = 3  # Minimum trigger length
        self.similarity_threshold = 0.7  # Similarity threshold

        self._initialize()

    def _initialize(self):
        """Initialize the service"""
        try:
            # Get storage and LLM manager
            self.storage = get_storage()

            self.prompt_manager = get_prompt_manager()

            # Initialize SemanticContextTool
            self.semantic_search_tool = SemanticContextTool()

            logger.info("CompletionService initialized successfully")

        except Exception as e:
            logger.error(f"CompletionService initialization failed: {e}")
            raise

    def get_completions(
        self,
        current_text: str,
        cursor_position: int,
        document_id: Optional[int] = None,
        user_context: Dict[str, Any] = None,
    ) -> List[CompletionSuggestion]:
        """
        Get intelligent completion suggestions

        Args:
            current_text: Current document content
            cursor_position: Cursor position
            document_id: Document ID (optional)
            user_context: User context information (optional)

        Returns:
            List[CompletionSuggestion]: List of completion suggestions
        """
        try:
            # Check if completion should be triggered
            if not self._should_trigger_completion(current_text, cursor_position):
                return []

            # Extract context
            context = self._extract_context(current_text, cursor_position)

            # Generate cache key
            cache_key = self._generate_cache_key(context, document_id)

            # Check cache
            cached_result = self.cache.get(cache_key)
            if cached_result:
                logger.debug("Returning completion suggestions from cache")
                return cached_result

            # Get different types of completion suggestions
            suggestions = []

            # 1. Semantic continuation completion
            semantic_suggestions = self._get_semantic_continuations(context)
            suggestions.extend(semantic_suggestions)

            # 2. Template completion
            template_suggestions = self._get_template_completions(context)
            suggestions.extend(template_suggestions)

            # 3. Reference suggestions
            reference_suggestions = self._get_reference_suggestions(context)
            suggestions.extend(reference_suggestions)

            # Rank and filter
            suggestions = self._rank_and_filter_suggestions(suggestions)

            # Cache results
            if suggestions:
                confidence_score = sum(s.confidence for s in suggestions) / len(suggestions)
                context_hash = hashlib.md5(str(context).encode()).hexdigest()
                self.cache.put(cache_key, suggestions, context_hash, confidence_score)

            logger.info(f"Generated {len(suggestions)} completion suggestions")
            return suggestions

        except Exception as e:
            logger.error(f"Failed to get completion suggestions: {e}")
            return []

    def _should_trigger_completion(self, text: str, cursor_pos: int) -> bool:
        """Determine if completion should be triggered"""
        if cursor_pos < self.min_trigger_length:
            return False

        # Get text before the cursor
        before_cursor = text[:cursor_pos]

        # If the last few characters before the cursor are whitespace, do not trigger completion
        if before_cursor.endswith(("  ", "\t", "\n\n")):
            return False

        # Check if in the middle of a word
        if cursor_pos < len(text) and text[cursor_pos].isalnum():
            return False

        return True

    def _extract_context(self, text: str, cursor_pos: int) -> Dict[str, Any]:
        """Extract context information"""
        # Get text before and after the cursor
        before_cursor = text[:cursor_pos]
        after_cursor = text[cursor_pos:]

        # Extract the current line
        lines = text[:cursor_pos].split("\n")
        current_line = lines[-1] if lines else ""

        # Extract the current paragraph
        paragraphs = text.split("\n\n")
        current_paragraph = ""
        char_count = 0
        for para in paragraphs:
            if char_count + len(para) >= cursor_pos:
                current_paragraph = para
                break
            char_count += len(para) + 2  # +2 for \n\n

        # Extract preceding context (up to 500 characters)
        context_before = before_cursor[-self.max_context_length :]
        context_after = after_cursor[:100]  # Shorter context after

        # Analyze document structure
        structure_info = self._analyze_document_structure(text, cursor_pos)

        return {
            "before_cursor": before_cursor,
            "after_cursor": after_cursor,
            "current_line": current_line,
            "current_paragraph": current_paragraph,
            "context_before": context_before,
            "context_after": context_after,
            "cursor_position": cursor_pos,
            "total_length": len(text),
            "structure": structure_info,
        }

    def _analyze_document_structure(self, text: str, cursor_pos: int) -> Dict[str, Any]:
        """Analyze document structure (heading levels, lists, etc.)"""
        lines = text[:cursor_pos].split("\n")
        current_line_idx = len(lines) - 1
        current_line = lines[current_line_idx] if lines else ""

        # Detect heading level
        heading_level = 0
        if current_line.startswith("#"):
            heading_level = len(current_line) - len(current_line.lstrip("#"))

        # Detect list items
        is_in_list = bool(re.match(r"^\s*[-*+]\s", current_line)) or bool(
            re.match(r"^\s*\d+\.\s", current_line)
        )

        # Detect code blocks
        code_block_count = text[:cursor_pos].count("```")
        in_code_block = code_block_count % 2 == 1

        return {
            "heading_level": heading_level,
            "in_list": is_in_list,
            "in_code_block": in_code_block,
            "line_number": current_line_idx + 1,
        }

    def _get_semantic_continuations(self, context: Dict[str, Any]) -> List[CompletionSuggestion]:
        """Get semantic continuation suggestions"""
        suggestions = []

        try:
            if not self.chat_client:
                return suggestions

            # Get prompt group
            prompt_group = self.prompt_manager.get_prompt_group(
                "completion_service.semantic_continuation"
            )
            system_prompt = prompt_group.get("system", "")

            # Build user prompt
            context_text = context.get("context_before", "")
            current_line = context.get("current_line", "")
            user_prompt_template = prompt_group.get(
                "user", "Please provide continuation suggestions for the text"
            )
            prompt = user_prompt_template.format(
                context_text=context_text, current_line=current_line
            )

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ]
            response = generate_with_messages(messages)

            if response and response.choices:
                content = response.choices[0].message.content.strip()

                # Parse multiple suggestions (separated by newlines)
                continuations = [c.strip() for c in content.split("\n") if c.strip()]

                for continuation in continuations[
                    :2
                ]:  # At most 2 semantic continuation suggestions
                    if continuation and len(continuation) > 3:
                        suggestions.append(
                            CompletionSuggestion(
                                text=continuation,
                                completion_type=CompletionType.SEMANTIC_CONTINUATION,
                                confidence=0.8,
                            )
                        )

        except Exception as e:
            logger.error(f"Failed to generate semantic continuations: {e}")

        return suggestions

    def _get_template_completions(self, context: Dict[str, Any]) -> List[CompletionSuggestion]:
        """Get template completion suggestions"""
        suggestions = []

        current_line = context.get("current_line", "")
        structure = context.get("structure", {})

        # Heading completion
        if current_line.startswith("#"):
            level = structure.get("heading_level", 1)
            if level < 6:  # Suggest a subheading
                suggestions.append(
                    CompletionSuggestion(
                        text=f"{'#' * (level + 1)} ",
                        completion_type=CompletionType.TEMPLATE_COMPLETION,
                        confidence=0.9,
                    )
                )

        # List completion
        elif structure.get("in_list"):
            # Detect list type and continue
            if re.match(r"^\s*[-*+]\s", current_line):
                indent = len(current_line) - len(current_line.lstrip())
                suggestions.append(
                    CompletionSuggestion(
                        text=f"\n{' ' * indent}- ",
                        completion_type=CompletionType.TEMPLATE_COMPLETION,
                        confidence=0.95,
                    )
                )
            elif re.match(r"^\s*(\d+)\.\s", current_line):
                match = re.match(r"^(\s*)(\d+)\.\s", current_line)
                if match:
                    indent, num = match.groups()
                    next_num = int(num) + 1
                    suggestions.append(
                        CompletionSuggestion(
                            text=f"\n{indent}{next_num}. ",
                            completion_type=CompletionType.TEMPLATE_COMPLETION,
                            confidence=0.95,
                        )
                    )

        # Code block completion
        elif current_line.strip() == "```":
            suggestions.append(
                CompletionSuggestion(
                    text="python\n\n```",
                    completion_type=CompletionType.TEMPLATE_COMPLETION,
                    confidence=0.8,
                )
            )

        return suggestions

    def _get_reference_suggestions(self, context: Dict[str, Any]) -> List[CompletionSuggestion]:
        """Get reference suggestions (based on vector search)"""
        suggestions = []

        try:
            if not self.semantic_search_tool:
                return suggestions

            # Use context for vector search
            search_text = context.get("context_before", "")
            if len(search_text) < 10:
                return suggestions

            # Use SemanticContextTool for semantic search
            search_results = self.semantic_search_tool.execute(query=search_text, top_k=5)

            # Process search results
            for result in search_results:
                # Check for errors
                if "error" in result:
                    logger.warning(f"Search error: {result['error']}")
                    continue

                # Get similarity score
                score = result.get("similarity_score", 0)
                if score < self.similarity_threshold:
                    continue

                # Extract relevant text snippets
                context_text = result.get("context", "")
                if context_text:
                    # Find relevant sentences
                    sentences = context_text.split(".")
                    for sentence in sentences[:2]:  # At most 2 sentences
                        sentence = sentence.strip()
                        if sentence and len(sentence) > 10:
                            # Get document description information
                            context_desc = result.get("context_description", "")
                            context_used = []
                            if context_desc:
                                context_used.append(f"Source: {context_desc}")

                            suggestions.append(
                                CompletionSuggestion(
                                    text=sentence + ".",
                                    completion_type=CompletionType.REFERENCE_SUGGESTION,
                                    confidence=score,
                                    context_used=context_used,
                                )
                            )

        except Exception as e:
            logger.error(f"Failed to generate reference suggestions: {e}")

        return suggestions

    def _rank_and_filter_suggestions(
        self, suggestions: List[CompletionSuggestion]
    ) -> List[CompletionSuggestion]:
        """Rank and filter suggestions"""
        if not suggestions:
            return []

        # Sort by confidence
        suggestions.sort(key=lambda x: x.confidence, reverse=True)

        # Deduplicate (based on text similarity)
        unique_suggestions = []
        for suggestion in suggestions:
            is_duplicate = False
            for existing in unique_suggestions:
                if self._is_similar_text(suggestion.text, existing.text):
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique_suggestions.append(suggestion)

        # Limit the maximum number
        return unique_suggestions[: self.max_suggestions]

    def _is_similar_text(self, text1: str, text2: str) -> bool:
        """Check if two texts are similar"""
        if text1 == text2:
            return True

        # Simple similarity check
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if len(words1) == 0 and len(words2) == 0:
            return True

        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))

        similarity = intersection / union if union > 0 else 0
        return similarity > 0.8

    def _generate_cache_key(self, context: Dict[str, Any], document_id: Optional[int]) -> str:
        """Generate a cache key"""
        key_data = {
            "context_before": context.get("context_before", "")[
                -100:
            ],  # Use only the last 100 characters
            "current_line": context.get("current_line", ""),
            "document_id": document_id,
        }

        key_str = str(key_data)
        return hashlib.md5(key_str.encode()).hexdigest()

    def clear_cache(self):
        """Clear the cache"""
        self.cache.invalidate()
        logger.info("Completion cache cleared")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return self.cache.get_stats()

    def precompute_document_context(self, document_id: int, content: str):
        """Precompute document context"""
        self.cache.precompute_context(document_id, content)

    def optimize_cache(self):
        """Optimize cache performance"""
        self.cache.optimize()


# Global singleton instance
_completion_service_instance = None


def get_completion_service() -> CompletionService:
    """Get the global completion service instance"""
    global _completion_service_instance
    if _completion_service_instance is None:
        _completion_service_instance = CompletionService()
    return _completion_service_instance
