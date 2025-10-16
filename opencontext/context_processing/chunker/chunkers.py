#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Optimized document and text chunking strategies.
Only includes essential chunkers: BaseChunker, StructuredFileChunker, FAQChunker.
PDF, Text, Image and Cloud processing are now handled by LLMDocumentChunker.
"""

import io
import re
from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Generator, Iterator, List, Optional, Tuple

import pandas as pd

from opencontext.models.context import Chunk, RawContextProperties
from opencontext.utils.logging_utils import get_logger

logger = get_logger(__name__)


class ChunkingConfig:
    """Configuration for chunking operations."""

    def __init__(
        self,
        max_chunk_size: int = 1000,
        chunk_overlap: int = 200,
        min_chunk_size: int = 100,
        batch_size: int = 100,
        enable_caching: bool = True,
    ):
        self.max_chunk_size = max_chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.batch_size = batch_size
        self.enable_caching = enable_caching


class BaseChunker(ABC):
    """
    Abstract base class for document chunking strategies.

    Provides memory-efficient chunking with configurable parameters.
    """

    def __init__(self, config: Optional[ChunkingConfig] = None):
        self.config = config or ChunkingConfig()
        self._chunk_cache = {} if self.config.enable_caching else None

    @abstractmethod
    def chunk(self, context: RawContextProperties) -> Iterator[Chunk]:
        """
        Chunk content from context data using iterator for memory efficiency.

        Args:
            context: RawContextProperties object containing content to chunk

        Yields:
            Chunk objects representing portions of the original content
        """
        pass

    def chunk_to_list(self, context: RawContextProperties) -> List[Chunk]:
        """
        Convert iterator to list for backward compatibility.

        Args:
            context: RawContextProperties object

        Returns:
            List of chunks
        """
        return list(self.chunk(context))

    @lru_cache(maxsize=128)
    def _get_sentence_boundaries(self, text: str) -> List[int]:
        """
        Get sentence boundary positions with caching for performance.

        Args:
            text: Text to analyze

        Returns:
            List of sentence boundary positions
        """
        # Simple sentence boundary detection
        pattern = r"[.!?]+\s+"
        boundaries = [0]

        for match in re.finditer(pattern, text):
            boundaries.append(match.end())

        boundaries.append(len(text))
        return boundaries

    def _create_overlapping_chunks(
        self, text: str, boundaries: List[int]
    ) -> Generator[str, None, None]:
        """
        Create overlapping text chunks efficiently.

        Args:
            text: Text to chunk
            boundaries: Sentence boundary positions

        Yields:
            Text chunks with overlap
        """
        if not text or not boundaries:
            return

        max_size = self.config.max_chunk_size
        overlap = self.config.chunk_overlap
        min_size = self.config.min_chunk_size

        start_idx = 0

        while start_idx < len(boundaries) - 1:
            chunk_end = start_idx
            chunk_size = 0

            # Build chunk up to max size
            while (
                chunk_end < len(boundaries) - 1
                and chunk_size + (boundaries[chunk_end + 1] - boundaries[start_idx]) <= max_size
            ):
                chunk_end += 1
                chunk_size = boundaries[chunk_end] - boundaries[start_idx]

            # Extract chunk text
            chunk_text = text[boundaries[start_idx] : boundaries[chunk_end]].strip()

            if len(chunk_text) >= min_size:
                yield chunk_text

            # Calculate next start position with overlap
            overlap_size = 0
            next_start = chunk_end

            # Find overlap position
            while next_start > start_idx and overlap_size < overlap:
                next_start -= 1
                overlap_size = boundaries[chunk_end] - boundaries[next_start]

            start_idx = max(next_start, start_idx + 1)


class StructuredFileChunker(BaseChunker):
    """
    Memory-efficient chunker for structured documents (CSV, XLSX, JSONL).

    Uses streaming and batching to handle large files without loading
    everything into memory at once.
    """

    def chunk(self, context: RawContextProperties) -> Iterator[Chunk]:
        """
        Chunk structured file content efficiently.

        Args:
            context: Context containing file path or content

        Yields:
            Chunks representing portions of the structured data
        """
        if not context.content_path:
            logger.warning("No content path provided for structured file chunking")
            return

        file_path = Path(context.content_path)
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return

        file_extension = file_path.suffix.lower()

        try:
            if file_extension == ".csv":
                yield from self._chunk_csv_streaming(file_path, context)
            elif file_extension in [".xlsx", ".xls"]:
                yield from self._chunk_excel_streaming(file_path, context)
            elif file_extension == ".jsonl":
                yield from self._chunk_jsonl_streaming(file_path, context)
            else:
                logger.warning(f"Unsupported file type: {file_extension}")

        except Exception as e:
            logger.exception(f"Error chunking structured file {file_path}: {e}")

    def _chunk_csv_streaming(
        self, file_path: Path, context: RawContextProperties
    ) -> Iterator[Chunk]:
        """Stream CSV file in chunks"""
        try:
            chunk_size = self.config.batch_size
            chunk_idx = 0

            # Read CSV in chunks
            for df_chunk in pd.read_csv(file_path, chunksize=chunk_size):
                if df_chunk.empty:
                    continue

                # Convert to text representation with headers
                text_content = df_chunk.to_string(index=False)

                # Create metadata
                metadata = {
                    "file_type": "csv",
                    "chunk_rows": len(df_chunk),
                    "columns": list(df_chunk.columns),
                    "file_path": str(file_path),
                }

                yield Chunk(
                    text=text_content,
                    chunk_index=chunk_idx,
                    source_document_id=context.object_id,
                    title=f"CSV Chunk {chunk_idx + 1}",
                    summary=f"CSV data with {len(df_chunk)} rows and {len(df_chunk.columns)} columns",
                    semantic_type="structured_data",
                    keywords=list(df_chunk.columns),  # Column names as keywords
                    metadata=metadata,
                )

                chunk_idx += 1

        except Exception as e:
            logger.exception(f"Error streaming CSV file {file_path}: {e}")

    def _chunk_excel_streaming(
        self, file_path: Path, context: RawContextProperties
    ) -> Iterator[Chunk]:
        """Stream Excel file in chunks"""
        try:
            # Read all sheets
            excel_file = pd.ExcelFile(file_path)
            chunk_idx = 0

            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(excel_file, sheet_name=sheet_name)

                if df.empty:
                    continue

                # Split large sheets into smaller chunks
                chunk_size = self.config.batch_size
                for start_idx in range(0, len(df), chunk_size):
                    end_idx = min(start_idx + chunk_size, len(df))
                    df_chunk = df.iloc[start_idx:end_idx]

                    # Convert to text with headers
                    text_content = df_chunk.to_string(index=False)

                    metadata = {
                        "file_type": "excel",
                        "sheet_name": sheet_name,
                        "chunk_rows": len(df_chunk),
                        "columns": list(df_chunk.columns),
                        "row_range": (start_idx, end_idx - 1),
                        "file_path": str(file_path),
                    }

                    yield Chunk(
                        text=text_content,
                        chunk_index=chunk_idx,
                        source_document_id=context.object_id,
                        title=f"Excel {sheet_name} Chunk {chunk_idx + 1}",
                        summary=f"Excel sheet '{sheet_name}' rows {start_idx}-{end_idx-1}",
                        semantic_type="structured_data",
                        keywords=list(df_chunk.columns),  # Column names as keywords
                        metadata=metadata,
                    )

                    chunk_idx += 1

        except Exception as e:
            logger.exception(f"Error streaming Excel file {file_path}: {e}")

    def _chunk_jsonl_streaming(
        self, file_path: Path, context: RawContextProperties
    ) -> Iterator[Chunk]:
        """Stream JSONL file in chunks"""
        try:
            chunk_idx = 0
            chunk_size = self.config.batch_size
            lines_buffer = []

            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    lines_buffer.append(line)

                    if len(lines_buffer) >= chunk_size:
                        # Process accumulated lines
                        text_content = "\n".join(lines_buffer)

                        metadata = {
                            "file_type": "jsonl",
                            "lines_count": len(lines_buffer),
                            "file_path": str(file_path),
                        }

                        yield Chunk(
                            text=text_content,
                            chunk_index=chunk_idx,
                            source_document_id=context.object_id,
                            title=f"JSONL Chunk {chunk_idx + 1}",
                            summary=f"JSONL data with {len(lines_buffer)} lines",
                            semantic_type="structured_data",
                            metadata=metadata,
                        )

                        chunk_idx += 1
                        lines_buffer = []

                # Process remaining lines
                if lines_buffer:
                    text_content = "\n".join(lines_buffer)

                    metadata = {
                        "file_type": "jsonl",
                        "lines_count": len(lines_buffer),
                        "file_path": str(file_path),
                    }

                    yield Chunk(
                        text=text_content,
                        chunk_index=chunk_idx,
                        source_document_id=context.object_id,
                        title=f"JSONL Chunk {chunk_idx + 1}",
                        summary=f"JSONL data with {len(lines_buffer)} lines",
                        semantic_type="structured_data",
                        metadata=metadata,
                    )

        except Exception as e:
            logger.exception(f"Error streaming JSONL file {file_path}: {e}")


class FAQChunker(BaseChunker):
    """
    Specialized chunker for FAQ Excel files.
    Treats each Q&A pair as a separate chunk.
    """

    def chunk(self, context: RawContextProperties) -> Iterator[Chunk]:
        """
        Chunk FAQ Excel content.

        Args:
            context: Context containing FAQ file path

        Yields:
            Chunks representing Q&A pairs
        """
        if not context.content_path:
            logger.warning("No content path provided for FAQ chunking")
            return

        file_path = Path(context.content_path)
        if not file_path.exists():
            logger.error(f"FAQ file not found: {file_path}")
            return

        try:
            # Read Excel file
            df = pd.read_excel(file_path)

            # Identify question and answer columns
            question_col = None
            answer_col = None

            for col in df.columns:
                col_lower = col.lower()
                if "question" in col_lower or "q" in col_lower or "question" in col_lower:
                    question_col = col
                elif (
                    "answer" in col_lower
                    or "a" in col_lower
                    or "answer" in col_lower
                    or "reply" in col_lower
                ):
                    answer_col = col

            if not question_col or not answer_col:
                logger.warning(f"Could not identify question/answer columns in {file_path}")
                # Use first two columns as fallback
                if len(df.columns) >= 2:
                    question_col, answer_col = df.columns[0], df.columns[1]
                else:
                    return

            chunk_idx = 0
            for index, row in df.iterrows():
                question = str(row[question_col]).strip()
                answer = str(row[answer_col]).strip()

                if not question or question.lower() in ["nan", "none", ""]:
                    continue

                # Create chunk text
                text_content = f"Q: {question}\nA: {answer}"

                metadata = {
                    "file_type": "faq_excel",
                    "row_index": index,
                    "question_column": question_col,
                    "answer_column": answer_col,
                    "file_path": str(file_path),
                }

                yield Chunk(
                    text=text_content,
                    chunk_index=chunk_idx,
                    source_document_id=context.object_id,
                    title=f"FAQ: {question[:50]}{'...' if len(question) > 50 else ''}",
                    summary=f"Question: {question}",
                    semantic_type="faq",
                    keywords=[word.strip() for word in question.split() if len(word.strip()) > 2][
                        :5
                    ],  # First 5 keywords
                    metadata=metadata,
                )

                chunk_idx += 1

        except Exception as e:
            logger.exception(f"Error chunking FAQ file {file_path}: {e}")
