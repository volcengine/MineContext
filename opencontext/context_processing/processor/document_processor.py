#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0


"""
Document processor - Responsible for processing document-type data
"""
from typing import Any, Dict, List, Optional
from pathlib import Path

import threading, queue, time
from opencontext.context_processing.processor.base_processor import BaseContextProcessor
from opencontext.storage.global_storage import get_storage
from opencontext.models.context import (ProcessedContext,
                                        RawContextProperties, Chunk, ExtractedData, ContextProperties, Vectorize)
from opencontext.models.enums import ContentFormat, ContextSource, ContextType, FileType, STRUCTURED_FILE_TYPES
from opencontext.utils.logging_utils import get_logger
from opencontext.context_processing.chunker.chunkers import (
    BaseChunker, StructuredFileChunker, FAQChunker
)
from opencontext.context_processing.chunker.llm_document_chunker import LLMDocumentChunker


logger = get_logger(__name__)


class DocumentProcessor(BaseContextProcessor):
    """
    Document processor that selects appropriate chunking strategies based on content type to chunk documents (files, URLs) and long text.
    This processor uses a background thread model, placing processing tasks in a queue and executing them in the background.
    """
    def __init__(self):
        # Get config and prompt_manager from global configuration
        from opencontext.config.global_config import get_config, get_prompt_manager
        config = get_config('processing.document_processor') or {}
        super().__init__(config)
        
        self.prompt_manager = get_prompt_manager()
        self.batch_size = self.config.get("batch_size", 10)
        self.batch_timeout = self.config.get("batch_timeout", 5) # seconds
        self._stop_event = threading.Event()
        
        # LLM chunker configuration
        self.use_llm_chunker = self.config.get("use_llm_chunker", False)
        self.llm_chunker = None
        self.llm_supported_types = {'.pdf', '.md', '.markdown', '.txt', '.rst', '.html', '.htm', '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}
        if self.use_llm_chunker:
            self.llm_chunker = LLMDocumentChunker()

        structured_chunker = StructuredFileChunker()
        self.chunker_mapping = {
            # FileType keys for structured file-based chunking
            FileType.FAQ_XLSX: FAQChunker(),
            FileType.XLSX: structured_chunker,
            FileType.CSV: structured_chunker,
            FileType.JSONL: structured_chunker,
            FileType.PARQUET: structured_chunker,
        }

        # Pipeline related
        self._input_queue = queue.Queue(maxsize=self.batch_size*2)
        self._processing_task = threading.Thread(target=self._run_processing_loop, daemon=True)
        self._processing_task.start()
    
    @property
    def storage(self):
        """Get storage from global singleton"""
        return get_storage()

    def shutdown(self, graceful: bool = False):
        """Gracefully shut down background processing tasks."""
        logger.info("Shutting down DocumentProcessor...")
        self._stop_event.set()
        # Put a sentinel value in the queue to unblock the blocked get()
        try:
            self._input_queue.put(None, block=False)
        except queue.Full:
            pass
        self._processing_task.join(timeout=5)
        if self._processing_task.is_alive():
            logger.warning("DocumentProcessor background task failed to stop in time.")
        logger.info("DocumentProcessor has been shut down.")

    def get_name(self) -> str:
        return "document_processor"

    def get_description(self) -> str:
        return "Select chunking strategy based on content type to process documents and long text."

    def get_version(self) -> str:
        return "0.2.0"

    def _get_file_type(self, file_path: str) -> Optional[FileType]:
        if "faq" in file_path.lower() and file_path.endswith(".xlsx"):
            return FileType.FAQ_XLSX
        
        suffix = Path(file_path).suffix.lower().lstrip('.')
        try:
            return FileType(suffix)
        except ValueError:
            logger.warning(f"Unknown file type for suffix '{suffix}' in path {file_path}")
            return None

    def can_process(self, context: Any) -> bool:
        """Check if the specified format context data can be processed"""
        if not isinstance(context, RawContextProperties):
            return False
        
        # Support TEXT type content (from vaults documents) - processed using LLM chunker
        if context.source == ContextSource.TEXT:
            return self.llm_chunker is not None or context.content_format == ContentFormat.TEXT
        
        if context.source == ContextSource.FILE:
            if not context.content_path or not Path(context.content_path).exists():
                return False
            file_type = self._get_file_type(context.content_path)
            
            # Structured document type check
            if file_type and file_type in STRUCTURED_FILE_TYPES:
                return file_type in self.chunker_mapping
            
            # Unstructured document check for LLM chunker support
            if self.llm_chunker:
                file_ext = Path(context.content_path).suffix.lower()
                return file_ext in self.llm_supported_types
            
            # Other known file types
            return file_type in self.chunker_mapping

        return False

    def _get_chunker(self, context_data: RawContextProperties) -> Optional[BaseChunker]:
        """Get the corresponding chunker based on the content format of the context"""
        # Support TEXT type content (from vaults documents)
        if context_data.source == ContextSource.TEXT:
            # Prioritize using LLM chunker for vaults documents
            if self.llm_chunker and context_data.content_text:
                logger.info(f"Using LLM chunker for vaults document {context_data.object_id}")
                return self.llm_chunker
            # If no LLM chunker, cannot process TEXT content
            logger.warning(f"No suitable chunker for TEXT content {context_data.object_id}")
            return None

        if context_data.source == ContextSource.FILE:
            content_path = context_data.content_path
            if not content_path or not Path(content_path).exists():
                logger.warning(f"File path does not exist or not provided: {content_path} for object {context_data.object_id}.")
                return None

            # First determine file type
            file_type = self._get_file_type(content_path)
            
            # Structured documents use specialized chunker first, not LLM chunker
            if file_type and file_type in STRUCTURED_FILE_TYPES:
                logger.info(f"Using structured chunker for structured document {context_data.object_id} of type {file_type}")
                return self.chunker_mapping.get(file_type)
            
            # Unstructured documents consider using LLM chunker
            if self.llm_chunker:
                file_ext = Path(content_path).suffix.lower()
                if file_ext in self.llm_supported_types:
                    logger.info(f"Using LLM chunker for unstructured document {context_data.object_id} of type {file_ext}")
                    return self.llm_chunker

            # Other file types use traditional chunker (if exists)
            if file_type:
                return self.chunker_mapping.get(file_type)
        
        return None

    def process(self, context: RawContextProperties) -> bool:
        """
        Put raw context into queue for async processing.
        """
        if not self.can_process(context):
            return False

        self._input_queue.put(context)
        logger.info(f"Added document {context.object_id} to processing queue.")
        return True

    def _run_processing_loop(self):
        """Background processing loop for processing documents in input queue."""
        while not self._stop_event.is_set():
            try:
                # Wait for new items or timeout
                raw_context = self._input_queue.get(timeout=self.batch_timeout)

                if raw_context is None: # sentinel value
                    break
                
                logger.info(f"Started processing document: {raw_context.object_id}")
                time1 = time.time()
                processed_contexts = self._process_single_document(raw_context)
                if processed_contexts:
                    self.storage.batch_upsert_processed_context(processed_contexts)
                time2 = time.time()
                logger.info(f"Processing document {raw_context.object_id} took: {time2 - time1:.2f} seconds")

            except queue.Empty:
                # Queue is empty, continue waiting
                continue
            except Exception as e:
                logger.error(f"Unexpected error in processing loop: {e}", exc_info=True)
                time.sleep(1)

    def _process_single_document(self, raw_context: RawContextProperties) -> List[ProcessedContext]:
        """Process single document, chunk it and convert to ProcessedContext object list."""
        
        # 1. Select chunker and chunk
        chunker = self._get_chunker(raw_context)
        if not chunker:
            logger.warning(f"Content format {raw_context.content_format} cannot find suitable chunker, skipping document {raw_context.object_id}")
            return []
        
        logger.info(f"Started chunking document {raw_context.object_id}...")
        chunks = chunker.chunk(raw_context)
        logger.info(f"Document {raw_context.object_id} was chunked into {len(chunks)} chunks.")

        if not chunks:
            return []

        # 2. (Optional) Embed each chunk - omitted here, can be extended in future

        # 3. (Optional) Information extraction for each chunk - omitted here, can be extended in future

        # 4. Convert chunks to ProcessedContext objects
        processed_contexts = self._create_processed_contexts_from_chunks(raw_context, chunks)
        
        return processed_contexts

    def _create_processed_contexts_from_chunks(self, raw_context: RawContextProperties, chunks: List[Chunk]) -> List[ProcessedContext]:
        """Create ProcessedContext objects from chunks."""
        processed_contexts = []
        
        # Extract vaults document information
        additional_info = raw_context.additional_info or {}
        vault_id = additional_info.get('vault_id')
        document_title = additional_info.get('title', '')
        
        for i, chunk in enumerate(chunks):
            # 1. Create ExtractedData
            extracted_data = ExtractedData(
                title=chunk.title if chunk.title else document_title,
                summary=chunk.summary if chunk.summary else chunk.text[:200] + "..." if len(chunk.text) > 200 else chunk.text,
                context_type=ContextType.SEMANTIC_CONTEXT,
                confidence=10,
                importance=5,
            )
            logger.info(f"Chunk title: {chunk.title} \n summary: {chunk.summary} \n text: {chunk.text}")

            # 2. Create ContextProperties (including document tracking info)
            context_properties = ContextProperties(
                create_time=raw_context.create_time,
                event_time=raw_context.create_time,
                update_time=raw_context.create_time,
                enable_merge=False,
                raw_properties=[raw_context],
                # Document tracking fields
                file_path=None,  # vaults documents have no file path
                raw_type='vaults',  # source type
                raw_id=str(vault_id) if vault_id else None,  # ID from vaults table
            )

            # 3. Create Vectorize
            vectorize = Vectorize(
                content_format=ContentFormat.TEXT,
                text=extracted_data.summary,  # Use summary as vectorization text
            )

            # 4. Create ProcessedContext
            processed_context = ProcessedContext(
                id=f"{raw_context.object_id}_chunk_{i}",
                properties=context_properties,
                extracted_data=extracted_data,
                vectorize=vectorize,
                embedding=[],
            )

            processed_contexts.append(processed_context)
        
        return processed_contexts