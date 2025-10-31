#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Document Text Chunker - Specialized chunker for document text

Used in VLM mode to intelligently chunk extracted document text.
Splits based on semantic boundaries (paragraphs, sections) rather than simple character count.
"""

import asyncio
import re
from typing import Iterator, List, Optional

from opencontext.context_processing.chunker.chunkers import BaseChunker, ChunkingConfig
from opencontext.models.context import Chunk
from opencontext.utils.logging_utils import get_logger

logger = get_logger(__name__)


class DocumentTextChunker(BaseChunker):
    """
    Document Text Chunker

    Specifically for processing text extracted from VLM, using semantic boundary splitting strategy:
    1. Split by paragraphs first (double newlines)
    2. Then split by sentences
    3. Preserve section information (if available)
    """

    def __init__(self, config: Optional[ChunkingConfig] = None):
        """Initialize document text chunker"""
        super().__init__(config)

    def chunk_text(self, texts: List[str], document_title: str = None) -> List[Chunk]:
        """
        Split text list into multiple semantic chunks (intelligent semantic chunking)

        Strategy:
        1. Short documents (<10000 characters): Global semantic chunking - LLM analyzes entire document at once
        2. Long documents (≥10000 characters): Fallback to original paragraph-based chunking strategy
        """
        if not texts or all(not t.strip() for t in texts):
            logger.warning(f"Empty texts provided for chunking document")
            return []

        # Merge all text into complete document
        full_document = "\n\n".join([t.strip() for t in texts if t.strip()])

        # Choose strategy based on document length
        if len(full_document) < 10000:
            chunks = self._global_semantic_chunking(full_document, document_title)
        else:
            logger.info(f"Document too long ({len(full_document)} chars), using fallback strategy")
            # Fallback to original paragraph-based chunking strategy
            chunks = self._fallback_chunking(texts)

        logger.info(f"Created {len(chunks)} chunks from {len(texts)} text elements")
        return chunks

    def _collect_buffers(self, texts: List[str]) -> tuple:
        """
        Phase 1: Collect buffers that need LLM splitting

        Returns:
            (buffers_to_split, direct_chunks, oversized_elements)
            - buffers_to_split: [(buffer_text, position), ...] buffers that need LLM
            - direct_chunks: [(text, position), ...] text that can be used directly as chunks
            - oversized_elements: [(text, position), ...] oversized elements that need mechanical splitting
        """
        buffers_to_split = []
        direct_chunks = []
        oversized_elements = []

        buffer = ""
        position = 0  # Record insert position
        i = 0

        # Preprocessing: Expand oversized elements
        processed_texts = []
        for text in texts:
            text = text.strip()
            if not text:
                continue
            # If single element is oversized, split mechanically
            if len(text) > self.config.max_chunk_size:
                split_parts = self._split_oversized_element(text)
                processed_texts.extend(split_parts)
            else:
                processed_texts.append(text)

        # Main loop: Accumulate buffer
        i = 0
        while i < len(processed_texts):
            current_text = processed_texts[i]

            # Calculate accumulated length
            if buffer:
                potential_buffer = buffer + "\n\n" + current_text
            else:
                potential_buffer = current_text

            # Case 1: Accumulated length does not exceed threshold, continue accumulating
            if len(potential_buffer) <= self.config.max_chunk_size:
                buffer = potential_buffer
                i += 1
                continue

            # Case 2: Accumulated length exceeds threshold
            if buffer:
                # Buffer reaches threshold, needs LLM splitting
                if len(buffer.strip()) >= self.config.min_chunk_size:
                    buffers_to_split.append((buffer, position))
                    position += 1

                # Clear buffer, process current element next time
                buffer = ""
                # Don't increment i, reprocess current element in next iteration
            else:
                # Buffer is empty but still oversized (theoretically shouldn't happen, as already preprocessed)
                i += 1

        # Process last buffer
        if buffer and len(buffer.strip()) >= self.config.min_chunk_size:
            buffers_to_split.append((buffer, position))

        return buffers_to_split, direct_chunks, oversized_elements

    def _batch_split_with_llm(self, buffers: List[str]) -> List[List[str]]:
        """
        Phase 2: Batch concurrent LLM calls
        """
        # Create async tasks
        tasks = [self._split_with_llm_async(buf) for buf in buffers]

        # Run event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Execute all tasks concurrently
        results = loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))

        # Handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error splitting buffer {i}: {result}, falling back to mechanical split")
                processed_results.append(self._split_oversized_element(buffers[i]))
            else:
                processed_results.append(result)

        return processed_results

    def _assemble_chunks(self, buffers_to_split, llm_results, direct_chunks, oversized_elements) -> List[Chunk]:
        """
        Phase 3: Assemble final chunks
        """
        chunks = []
        chunk_idx = 0

        # Create chunks from LLM results
        for (buffer, position), split_chunks in zip(buffers_to_split, llm_results):
            for text_chunk in split_chunks:
                if len(text_chunk.strip()) >= self.config.min_chunk_size:
                    chunk = Chunk(
                        text=text_chunk,
                        chunk_index=chunk_idx,
                    )
                    chunks.append(chunk)
                    chunk_idx += 1

        return chunks

    async def _split_with_llm_async(self, text: str) -> List[str]:
        """
        Use LLM to intelligently split text (async version)
        """
        try:
            from opencontext.config.global_config import get_prompt_group
            from opencontext.llm.global_vlm_client import generate_with_messages_async
            from opencontext.utils.json_parser import parse_json_from_response

            prompt_group = get_prompt_group("document_processing.text_chunking")
            system_prompt = prompt_group["system"]
            user_prompt_template = prompt_group["user"]

            # Fill in prompt parameters
            user_prompt = user_prompt_template.format(
                text=text,
                max_chunk_size=self.config.max_chunk_size,
                min_chunk_size=self.config.min_chunk_size,
            )

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            # Async LLM call
            response = await generate_with_messages_async(messages=messages)

            # Parse JSON response
            chunks = parse_json_from_response(response)

            if not isinstance(chunks, list):
                logger.warning(f"LLM returned non-list response, falling back to oversized split")
                return self._split_oversized_element(text)

            logger.info(f"LLM split text into {len(chunks)} chunks")
            return chunks

        except Exception as e:
            logger.error(f"Error in async LLM text splitting: {e}, falling back to oversized split")
            return self._split_oversized_element(text)

    def _split_oversized_element(self, text: str) -> List[str]:
        """
        Split oversized element (mechanical splitting, no LLM call)
        Strategy:
        1. Split by periods first
        2. If no periods, split in half
        """
        # Split by periods (Chinese and English)
        sentence_pattern = r"([.。!?!?]+)"
        parts = re.split(sentence_pattern, text)

        # Recombine sentences and separators
        sentences = []
        for i in range(0, len(parts) - 1, 2):
            sentence = parts[i]
            separator = parts[i + 1] if i + 1 < len(parts) else ""
            sentences.append(sentence + separator)

        # If last element is a sentence (no separator)
        if len(parts) % 2 == 1:
            sentences.append(parts[-1])

        # If periods were found, return split result
        if len(sentences) > 1:
            logger.info(f"Split oversized element by punctuation into {len(sentences)} parts")
            return sentences

        # No periods, split in half
        mid_point = len(text) // 2
        logger.info(f"Split oversized element in half at position {mid_point}")
        return [text[:mid_point], text[mid_point:]]

    def _global_semantic_chunking(self, full_document: str, document_title: str = None) -> List[Chunk]:
        """
        Global semantic chunking - LLM analyzes and chunks entire document at once

        Suitable for short documents (<10000 characters)
        """
        try:
            from opencontext.config.global_config import get_prompt_group
            from opencontext.llm.global_vlm_client import generate_with_messages_async
            from opencontext.utils.json_parser import parse_json_from_response

            prompt_group = get_prompt_group("document_processing.global_semantic_chunking")
            system_prompt = prompt_group["system"]
            user_prompt_template = prompt_group["user"]

            # Fill in prompt parameters
            user_prompt = user_prompt_template.format(
                full_document=full_document,
                max_chunk_size=self.config.max_chunk_size,
                min_chunk_size=self.config.min_chunk_size,
            )

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            # Create async event loop
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Async LLM call
            response = loop.run_until_complete(
                generate_with_messages_async(
                    messages=messages,
                )
            )

            # Parse JSON response
            chunk_texts = parse_json_from_response(response)

            if not isinstance(chunk_texts, list):
                logger.warning(f"LLM returned non-list response, falling back")
                return self._fallback_chunking([full_document])

            # Create Chunk objects
            chunks = []
            for idx, text in enumerate(chunk_texts):
                if len(text.strip()) >= self.config.min_chunk_size:
                    chunk = Chunk(
                        text=text.strip(),
                        chunk_index=idx,
                    )
                    chunks.append(chunk)

            logger.info(f"Global semantic chunking created {len(chunks)} chunks")
            return chunks

        except Exception as e:
            logger.error(f"Error in global semantic chunking: {e}, falling back to default strategy")
            return self._fallback_chunking([full_document])

    def _fallback_chunking(self, texts: List[str]) -> List[Chunk]:
        """
        Fallback chunking strategy - used when document is too long or global chunking fails

        Uses original paragraph accumulation strategy
        """
        # Phase 1: Collect buffers that need splitting
        buffers_to_split, direct_chunks, oversized_elements = self._collect_buffers(texts)

        # Phase 2: Batch concurrent LLM calls
        llm_split_results = []
        if buffers_to_split:
            logger.info(f"Fallback: Batch splitting {len(buffers_to_split)} buffers with LLM")
            llm_split_results = self._batch_split_with_llm([buf for buf, _ in buffers_to_split])

        # Phase 3: Assemble chunks
        chunks = self._assemble_chunks(buffers_to_split, llm_split_results, direct_chunks, oversized_elements)

        return chunks

    def chunk(self, _context) -> Iterator[Chunk]:
        """
        Implement BaseChunker abstract method (compatibility)

        Note: DocumentTextChunker should be used via chunk_text() method
        """
        raise NotImplementedError(
            "DocumentTextChunker should be used via chunk_text() method"
        )
