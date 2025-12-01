#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Document Processor
"""

import asyncio
import datetime
import os
import queue
import threading
import time
from pathlib import Path
from typing import List

from PIL import Image

from opencontext.context_processing.chunker import (
    ChunkingConfig,
    DocumentTextChunker,
    FAQChunker,
    StructuredFileChunker,
)
from opencontext.context_processing.processor.base_processor import BaseContextProcessor
from opencontext.context_processing.processor.document_converter import DocumentConverter, PageInfo
from opencontext.llm.global_vlm_client import generate_with_messages_async
from opencontext.models.context import *
from opencontext.models.enums import *
from opencontext.monitoring.monitor import record_processing_error
from opencontext.storage.global_storage import get_storage
from opencontext.utils.logging_utils import get_logger

logger = get_logger(__name__)


class DocumentProcessor(BaseContextProcessor):
    """
    Document Processor
    """

    def __init__(self):
        from opencontext.config.global_config import get_config

        config = get_config("processing.document_processor") or {}
        super().__init__(config)

        # Configuration parameters
        self._batch_size = self.config.get("batch_size", 5)
        self._batch_timeout = self.config.get("batch_timeout", 30)

        # Get document processing config
        doc_processing_config = get_config("document_processing") or {}
        self._enabled = doc_processing_config.get("enabled", True)
        self._dpi = doc_processing_config.get("dpi", 200)
        self._vlm_batch_size = doc_processing_config.get("batch_size", 3)
        self._text_threshold = doc_processing_config.get("text_threshold_per_page", 50)

        # Thread control
        self._stop_event = threading.Event()

        # Queue and background thread
        self._input_queue = queue.Queue(maxsize=self._batch_size * 2)
        self._processing_task = threading.Thread(target=self._run_processing_loop, daemon=True)
        self._processing_task.start()
        # Document converter
        self._document_converter = DocumentConverter(dpi=self._dpi)

        # Structured document chunker
        self._structured_chunker = StructuredFileChunker()
        self._faq_chunker = FAQChunker()
        self._document_chunker = DocumentTextChunker(
            config=ChunkingConfig(
                max_chunk_size=1000,
                min_chunk_size=100,
                chunk_overlap=100,
            )
        )

        logger.info("DocumentProcessor initialized ")

    def shutdown(self, _graceful: bool = False):
        """Gracefully shutdown background processing task"""
        self._stop_event.set()
        self._input_queue.put(None)
        self._processing_task.join(timeout=10)
        if self._processing_task.is_alive():
            logger.warning("UnifiedDocumentProcessor background task failed to stop in time.")
        logger.info("UnifiedDocumentProcessor has been shut down.")

    def get_name(self) -> str:
        return "document_processor"

    def get_description(self) -> str:
        return (
            "Unified document processor: structured (CSV/XLSX), text, and visual (PDF/DOCX/images)"
        )

    @staticmethod
    def get_supported_formats() -> List[str]:
        return [
            ".pdf",
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".bmp",
            ".webp",
            ".docx",
            ".doc",
            ".pptx",
            ".ppt",
            ".xlsx",
            ".xls",
            ".csv",
            ".jsonl",
            ".md",
            ".txt",
        ]

    def _get_file_type(self, file_path: str) -> FileType:
        """Get file type"""
        if "faq" in file_path.lower() and file_path.endswith(".xlsx"):
            return FileType.FAQ_XLSX

        suffix = Path(file_path).suffix.lower().lstrip(".")
        try:
            return FileType(suffix)
        except ValueError:
            logger.warning(f"Unknown file type for suffix '{suffix}' in path {file_path}")
            return None

    def _is_structured_document(self, context: RawContextProperties) -> bool:
        file_type = self._get_file_type(context.content_path)
        return file_type in STRUCTURED_FILE_TYPES

    def _is_text_content(self, context: RawContextProperties) -> bool:
        return context.source == ContextSource.INPUT

    def _is_visual_document(self, context: RawContextProperties) -> bool:
        if context.source != ContextSource.LOCAL_FILE:
            return False
        file_ext = Path(context.content_path).suffix.lower()
        visual_formats = {
            ".pdf",
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".bmp",
            ".webp",
            ".docx",
            ".doc",
            ".pptx",
            ".ppt",
            ".md",
        }
        return file_ext in visual_formats

    def can_process(self, context: RawContextProperties) -> bool:
        """Check if can process this context"""
        if not self._enabled or not isinstance(context, RawContextProperties):
            return False
        if self._is_text_content(context):
            return True
        if context.source == ContextSource.LOCAL_FILE:
            if not context.content_path or not Path(context.content_path).exists():
                logger.warning(f"File not found: {context.content_path}")
                return False
            file_ext = Path(context.content_path).suffix.lower()
            return file_ext in self.get_supported_formats()
        return False

    def process(self, context: RawContextProperties) -> bool:
        """Process single document context (add to queue)"""
        if not self.can_process(context):
            return False
        try:
            self._input_queue.put(context)
            return True
        except Exception as e:
            logger.exception(f"Error queuing document {context.object_id}: {e}")
            return False

    def _run_processing_loop(self):
        """Background processing loop (consume documents from queue)"""
        while not self._stop_event.is_set():
            unprocessed_context = None
            try:
                raw_context = self._input_queue.get(timeout=self._batch_timeout)
                unprocessed_context = raw_context
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Unexpected error in processing loop: {e}")
                time.sleep(3)
                continue

            if unprocessed_context:
                time_start = int(time.time())
                try:
                    processed_contexts = self.real_process(unprocessed_context)
                    if processed_contexts:
                        get_storage().batch_upsert_processed_context(processed_contexts)
                except Exception as e:
                    logger.exception(f"Unexpected error in real_process: {e}")

                time_end = int(time.time())
                logger.info(f"Processed 1 document in {time_end - time_start} seconds")

    def real_process(self, raw_context: RawContextProperties) -> List[ProcessedContext]:
        """处理文档"""
        start_time = time.time()
        try:
            all_processed_contexts = []
            if self._is_structured_document(raw_context):
                contexts = self._process_structured_document(raw_context)
            elif self._is_text_content(raw_context):
                contexts = self._process_text_content(raw_context)
            else:
                contexts = self._process_visual_document(raw_context)
            all_processed_contexts.extend(contexts)
            logger.info(
                f"Successfully processed document {raw_context.object_id}: {len(contexts)} contexts created"
            )
            self._record_metrics(start_time, len(all_processed_contexts))
            return all_processed_contexts

        except Exception as e:
            error_msg = f"Failed to batch process documents. Error: {e}"
            logger.exception(error_msg)
            record_processing_error(error_msg, processor_name=self.get_name(), context_count=1)
            return False

    def _process_structured_document(
        self, raw_context: RawContextProperties
    ) -> List[ProcessedContext]:
        """Process structured documents (CSV/XLSX/JSONL)"""
        file_type = self._get_file_type(raw_context.content_path)
        if file_type == FileType.FAQ_XLSX:
            chunker = self._faq_chunker
        elif file_type in STRUCTURED_FILE_TYPES:
            chunker = self._structured_chunker
        else:
            logger.warning(f"Unsupported structured file type: {file_type}")
            return []
        chunks = list(chunker.chunk(raw_context))
        return self._create_contexts_from_chunks(raw_context, chunks)

    def _create_contexts_from_chunks(
        self, raw_context: RawContextProperties, chunks: List[Chunk]
    ) -> List[ProcessedContext]:
        """Create ProcessedContext from Chunk list"""
        contexts = []
        now = datetime.datetime.now()
        # TODO: semantic additional
        knowledge_metadata = KnowledgeContextMetadata(
            knowledge_source=raw_context.source,
            knowledge_file_path=raw_context.content_path,
            knowledge_raw_id=raw_context.object_id,
            # knowledge_title=raw_context.title,
        )
        for chunk in chunks:
            ctx = ProcessedContext(
                properties=ContextProperties(
                    raw_properties=[raw_context],
                    create_time=now,
                    update_time=now,
                    event_time=now,
                    enable_merge=False,
                    raw_type=raw_context.content_type,
                    raw_id=raw_context.object_id,
                ),
                extracted_data=ExtractedData(
                    title="",
                    summary=chunk.text,
                    keywords=chunk.keywords if chunk.keywords else [],
                    entities=chunk.entities if chunk.entities else [],
                    context_type=ContextType.KNOWLEDGE_CONTEXT,
                ),
                vectorize=Vectorize(
                    content_format=ContentFormat.TEXT,
                    text=chunk.text,
                ),
                metadata=knowledge_metadata.model_dump(exclude_none=True),
            )
            contexts.append(ctx)

        return contexts

    def _process_text_content(self, raw_context: RawContextProperties) -> List[ProcessedContext]:
        """Process TEXT type (vaults text content)"""
        if not raw_context.content_text:
            return []
        chunks = self._document_chunker.chunk_text(
            texts=[raw_context.content_text],
        )
        return self._create_contexts_from_chunks(raw_context, chunks)

    def _process_visual_document(self, raw_context: RawContextProperties) -> List[ProcessedContext]:
        """
        Process visual documents (PDF/DOCX/images) - page-by-page intelligent detection

        Strategy (page_level_detection=True):
        1. PDF/DOCX: Analyze page by page, use VLM for pages with charts, extract text directly for pure text pages
        2. Images/PPT: Direct VLM (inherently visual content)
        """
        file_path = raw_context.content_path
        file_ext = Path(file_path).suffix.lower()

        # Image files and PPT files: Direct VLM
        if file_ext in [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".pptx", ".ppt"]:
            file_path = raw_context.content_path
            images = self._document_converter.convert_to_images(file_path)
            text_parts = self._analyze_document_with_vlm(images)
            chunks = self._document_chunker.chunk_text(
                texts=text_parts,
            )
            return self._create_contexts_from_chunks(raw_context, chunks)

        # PDF/DOCX: Choose strategy based on config
        if file_ext in [".pdf", ".docx", ".doc", ".md", ".txt"]:
            return self._process_document_page_by_page(raw_context, file_path, file_ext)

        raise ValueError(f"Unsupported file type for page-by-page: {file_ext}")

    def _process_document_page_by_page(
        self, raw_context: RawContextProperties, file_path: str, file_ext: str
    ) -> List[ProcessedContext]:
        """
        Process document page-by-page (core logic)

        1. Analyze each page to determine if VLM is needed
        2. Text pages: Direct text extraction + chunking
        3. Visual pages: VLM parsing
        4. Merge all results
        """
        logger.info(f"Processing document page-by-page: {file_path}")

        # 1. Analyze pages
        if file_ext == ".pdf":
            page_infos = self._document_converter.analyze_pdf_pages(file_path, self._text_threshold)
        elif file_ext in [".docx", ".doc"]:
            page_infos = self._document_converter.analyze_docx_pages(file_path)
        elif file_ext == ".md":
            page_infos = self._document_converter.analyze_markdown_pages(file_path)
        elif file_ext == ".txt":
            return self._process_txt_file(raw_context, file_path)
        else:
            raise ValueError(f"Unsupported file type for page-by-page: {file_ext}")

        # 2. Classify pages
        text_pages = [p for p in page_infos if not p.has_visual_elements]
        vlm_pages = [p for p in page_infos if p.has_visual_elements]

        logger.info(
            f"Document analysis: {len(text_pages)} text pages, {len(vlm_pages)} visual pages"
        )

        # 3. Process visual pages (extract text)
        vlm_texts = {}  # dict: page_number -> extracted_text
        if vlm_pages:
            vlm_text_list = self._extract_vlm_pages(file_path, vlm_pages)
            # Associate extracted text with page numbers
            for page_info, text in zip(vlm_pages, vlm_text_list):
                vlm_texts[page_info.page_number] = text

        # 4. Merge all pages in original order
        all_page_infos = []
        for page_info in page_infos:
            if page_info.page_number in vlm_texts:
                # VLM-processed page, use extracted text
                new_page_info = PageInfo(
                    page_number=page_info.page_number,
                    text=vlm_texts[page_info.page_number],
                    has_visual_elements=False,  # Already extracted as text, no longer needs VLM
                    doc_images=[],
                )
                all_page_infos.append(new_page_info)
            else:
                # Pure text page, use original text
                all_page_infos.append(page_info)

        # 5. Process all pages (using merged all_page_infos)
        text_list = [p.text for p in all_page_infos if p.text.strip()]
        chunks = self._document_chunker.chunk_text(
            texts=text_list,
        )
        all_contexts = self._create_contexts_from_chunks(raw_context, chunks)
        return all_contexts

    def _extract_vlm_pages(self, file_path: str, page_infos: List[PageInfo]) -> List[str]:
        """Extract text from visual pages using VLM, returns extracted text list (in page order)"""
        file_ext = Path(file_path).suffix.lower()

        if file_ext in [".docx", ".doc", ".md"]:
            return self._process_vlm_pages_with_doc_images(page_infos)

        # For PDF and other formats, convert pages to images
        # Convert document to images
        all_images = self._document_converter.convert_to_images(file_path)

        # Only process pages that need VLM
        vlm_images = [all_images[p.page_number - 1] for p in page_infos]
        vlm_page_numbers = [p.page_number for p in page_infos]

        # VLM analysis
        page_results = []
        for i in range(0, len(vlm_images), self._vlm_batch_size):
            batch = vlm_images[i : i + self._vlm_batch_size]
            batch_page_nums = vlm_page_numbers[i : i + self._vlm_batch_size]

            tasks = [
                self._analyze_image_with_vlm(img, page_num)
                for img, page_num in zip(batch, batch_page_nums)
            ]

            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            batch_results = loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))

            for idx, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    error_msg = f"Error processing page {batch_page_nums[idx]}: {result}"
                    logger.error(error_msg)
                    raise RuntimeError(error_msg) from result
                else:
                    page_results.append(result)

        # Collect result texts (as list)
        text_list = [
            result.get("text", "").strip()
            for result in page_results
            if result.get("text", "").strip()
        ]

        return text_list

    def _process_vlm_pages_with_doc_images(self, page_infos: List[PageInfo]) -> List[str]:
        """
        Process DOCX pages using embedded images (instead of converting entire page to image), returns extracted text list
        """
        # Collect all embedded images
        all_doc_images = []
        image_page_mapping = []  # Record page number for each image

        for page_info in page_infos:
            for img in page_info.doc_images:
                all_doc_images.append(img)
                image_page_mapping.append(page_info.page_number)

        # VLM analysis of all images
        image_results = []
        if all_doc_images:
            logger.info(f"Processing {len(all_doc_images)} embedded images from DOCX with VLM")

            for i in range(0, len(all_doc_images), self._vlm_batch_size):
                batch_images = all_doc_images[i : i + self._vlm_batch_size]
                batch_page_nums = image_page_mapping[i : i + self._vlm_batch_size]

                tasks = [
                    self._analyze_image_with_vlm(img, page_num)
                    for img, page_num in zip(batch_images, batch_page_nums)
                ]

                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                batch_results = loop.run_until_complete(
                    asyncio.gather(*tasks, return_exceptions=True)
                )

                for idx, result in enumerate(batch_results):
                    if isinstance(result, Exception):
                        logger.warning(f"Error processing embedded image {i+idx+1}: {result}")
                        continue
                    else:
                        image_results.append(result)

        # Merge image analysis results and original text (save as list)
        all_page_texts = []

        for page_info in page_infos:
            page_text_parts = []

            # Add page original text
            if page_info.text.strip():
                page_text_parts.append(page_info.text.strip())

            # Add image analysis results for this page
            page_image_results = [
                r for r in image_results if r.get("page_number") == page_info.page_number
            ]
            for img_result in page_image_results:
                img_text = img_result.get("text", "").strip()
                if img_text:
                    page_text_parts.append(img_text)

            if page_text_parts:
                all_page_texts.append("\n".join(page_text_parts))

        # Return text list instead of directly creating contexts
        return all_page_texts

    def _analyze_document_with_vlm(self, images: List[Image.Image]) -> List[str]:
        """Batch analyze document images using VLM, returns text list"""
        tasks = [self._analyze_image_with_vlm(img, i + 1) for i, img in enumerate(images)]

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        page_results = loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))

        text_parts = []
        for idx, result in enumerate(page_results):
            if isinstance(result, Exception):
                logger.error(f"Error processing image {idx + 1}: {result}")
                raise RuntimeError(f"Error processing image {idx + 1}") from result
            else:
                text = result.get("text", "").strip()
                if text:
                    text_parts.append(text)

        return text_parts

    async def _analyze_image_with_vlm(self, image: Image.Image, page_number: int = 1) -> dict:
        """Analyze single image using VLM (generic method)"""
        import base64
        import io

        from opencontext.config.global_config import get_prompt_group

        prompt_group = get_prompt_group("document_processing.vlm_analysis")
        system_prompt = prompt_group["system"]
        user_prompt = prompt_group["user"]

        # Convert PIL Image to base64
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        base64_image = base64.b64encode(buffered.getvalue()).decode("utf-8")

        # Build content, including text and image
        content = [
            {"type": "text", "text": user_prompt},
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{base64_image}",
                },
            },
        ]

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content},
        ]

        response = await generate_with_messages_async(messages=messages)
        # VLM directly returns plain text, no JSON parsing needed
        return {
            "text": response.strip(),
            "page_number": page_number,
        }

    def _process_txt_file(
        self, raw_context: RawContextProperties, file_path: str
    ) -> List[ProcessedContext]:
        """
        Process plain text file (.txt)

        Strategy:
        1. Read text content (UTF-8)
        2. Use text chunker for processing
        3. No VLM needed (plain text)
        """
        logger.info(f"Processing TXT file: {file_path}")
        try:
            # Read file content
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            if not content.strip():
                logger.warning(f"Empty TXT file: {file_path}")
                return []

            # Use text chunker for processing
            chunks = self._document_chunker.chunk_text(texts=[content])

            return self._create_contexts_from_chunks(raw_context, chunks)

        except Exception as e:
            logger.exception(f"Error processing TXT file: {e}")
            raise

    def _record_metrics(self, start_time: float, context_count: int):
        """Record performance metrics"""
        try:
            from opencontext.monitoring import record_processing_metrics

            duration_ms = int((time.time() - start_time) * 1000)
            record_processing_metrics(
                processor_name=self.get_name(),
                operation="document_process",
                duration_ms=duration_ms,
                context_count=context_count,
            )
        except ImportError:
            pass
