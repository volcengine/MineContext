#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Screenshot processor
"""
import asyncio
import base64
import datetime
import heapq
import json
import os
import queue
import threading
import time
from collections import deque
from typing import Any, Dict, List, Optional, Tuple

from opencontext.context_processing.processor.base_processor import BaseContextProcessor
from opencontext.context_processing.processor.entity_processor import (
    refresh_entities,
    validate_and_clean_entities,
)
from opencontext.llm.global_embedding_client import do_vectorize_async
from opencontext.llm.global_vlm_client import generate_with_messages_async
from opencontext.models.context import *
from opencontext.models.enums import get_context_type_descriptions_for_extraction
from opencontext.monitoring.monitor import record_processing_error
from opencontext.storage.global_storage import get_storage
from opencontext.tools.tool_definitions import ALL_TOOL_DEFINITIONS
from opencontext.utils.image import calculate_phash, resize_image
from opencontext.utils.json_parser import parse_json_from_response
from opencontext.utils.logging_utils import get_logger
from opencontext.config.global_config import get_prompt_group
from opencontext.monitoring import (
    increment_data_count,
    increment_recording_stat,
    record_processing_metrics,
)

logger = get_logger(__name__)


class ScreenshotProcessor(BaseContextProcessor):
    """
    Processor for processing and analyzing screenshots to extract context information.
    It supports real-time deduplication, context-aware information extraction and periodic memory compression.
    This processor uses a background thread model, placing processing tasks in a queue and executing them in the background.
    """

    def __init__(self):
        """
        Initialize ScreenshotProcessor.
        """
        # Get from global configuration
        from opencontext.config.global_config import get_config, get_prompt_manager

        config = get_config("processing.screenshot_processor") or {}
        super().__init__(config)


        self._similarity_hash_threshold = self.config.get("similarity_hash_threshold", 2)
        self._batch_size = self.config.get("batch_size", 10)
        self._batch_timeout = self.config.get("batch_timeout", 20)  # seconds
        self._max_raw_properties = self.config.get("max_raw_properties", 5)
        self._max_image_size = self.config.get("max_image_size", 0)
        self._resize_quality = self.config.get("resize_quality", 95)
        self._enabled_delete = self.config.get("enabled_delete", False)

        self._stop_event = threading.Event()

        # Pipeline related
        self._input_queue = queue.Queue(maxsize=self._batch_size * 3)
        self._processing_task = threading.Thread(target=self._run_processing_loop, daemon=True)
        self._processing_task.start()

        # State cache
        self._processed_cache = (
            {}
        )
        self._current_screenshot = deque(maxlen=self._batch_size * 2)

    def shutdown(self, graceful: bool = False):
        """Gracefully shut down background processing tasks."""
        logger.info("Shutting down ScreenshotProcessor...")
        self._stop_event.set()
        # Put a sentinel value in the queue to unblock the blocked get()
        self._input_queue.put(None)
        self._processing_task.join(timeout=5)
        if self._processing_task.is_alive():
            logger.warning("ScreenshotProcessor background task failed to stop in time.")
        logger.info("ScreenshotProcessor has been shut down.")

    def get_name(self) -> str:
        """Return the processor name."""
        return "screenshot_processor"

    def get_description(self) -> str:
        """Return the processor description."""
        return "Analyze screenshot streams, deduplicate images, and asynchronously extract context information."

    def can_process(self, context: RawContextProperties) -> bool:
        """
        Check if this processor can handle the given context.
        This processor only processes screenshot contexts.
        """
        return (
            isinstance(context, RawContextProperties) and context.source == ContextSource.SCREENSHOT
        )

    def _is_duplicate(self, new_context: RawContextProperties) -> bool:
        """
        Real-time deduplication of incoming screenshots after image compression.

        Args:
            new_context (RawContextProperties): New screenshot context.
            cache (list): The cache to check for duplicates.

        Returns:
            bool: Returns True if it's a new image, False if it's a duplicate image.
        """
        new_phash = calculate_phash(new_context.content_path)
        if new_phash is None:
            raise ValueError("Failed to calculate screenshot pHash")

        # To avoid modification during iteration
        for item in list(self._current_screenshot):
            diff = bin(int(str(new_phash), 16) ^ int(str(item["phash"]), 16)).count("1")
            if diff <= self._similarity_hash_threshold:
                # Find duplicate, move it to end of list (consider as most recently used)
                self._current_screenshot.remove(item)
                self._current_screenshot.append(item)

                if self._enabled_delete:
                    try:
                        os.remove(new_context.content_path)
                    except Exception as e:
                        logger.error(f"Failed to delete duplicate screenshot file: {e}")
                return True

        # If no duplicate found, it's a new image
        self._current_screenshot.append({"phash": new_phash, "id": new_context.object_id})

        return False

    def process(self, context: RawContextProperties) -> bool:
        """
        Process a single screenshot context.
        This method handles deduplication and adds new screenshots to temporary cache for batch processing.
        When cache reaches batch size, triggers information extraction.
        """
        if not self.can_process(context):
            return False
        try:
            if self._max_image_size > 0:
                resize_image(context.content_path, self._max_image_size, self._resize_quality)
            if not self._is_duplicate(context):
                self._input_queue.put(context, timeout=2)
                # Record screenshot path for UI display
                from opencontext.monitoring import record_screenshot_path

                if context.content_path:
                    record_screenshot_path(context.content_path)
        except Exception as e:
            logger.exception(f"Error processing screenshot {context.content_path}: {e}")
            return False
        return True

    def _run_processing_loop(self):
        from opencontext.monitoring import (
            increment_data_count,
            increment_recording_stat,
            record_processing_metrics,
        )
        """Background processing loop for handling screenshots in input queue."""
        unprocessed_contexts = []
        last_process_time = int(time.time())
        while not self._stop_event.is_set():
            try:
                # Wait for new items or timeout
                raw_context = self._input_queue.get(timeout=self._batch_timeout)
                if raw_context is None:  # sentinel value
                    logger.info("Received sentinel value, exiting processing loop")
                    break
                # Process deduplication
                unprocessed_contexts.append(raw_context)
                if (int(time.time()) - last_process_time) < self._batch_timeout * 2 and len(
                    unprocessed_contexts
                ) < self._batch_size:
                    # logger.info(f"Screenshots in cache: {len(unprocessed_contexts)}")
                    continue
            except queue.Empty:
                # logger.info("Queue empty, waiting for new data")
                continue
            except Exception as e:
                logger.error(f"Unexpected error in processing loop: {e}")
                time.sleep(1)
            start_time = time.time()
            increment_data_count("screenshot", count=len(unprocessed_contexts))
            try:
                processed_contexts =  asyncio.run(self.batch_process(unprocessed_contexts))
                if processed_contexts:
                    get_storage().batch_upsert_processed_context(processed_contexts)
            except Exception as e:
                error_msg = f"Failed during concurrent VLM processing: {e}"
                logger.error(error_msg)
                record_processing_error(
                    error_msg, processor_name=self.get_name(), context_count=len(unprocessed_contexts)
                )
                increment_recording_stat("failed", len(unprocessed_contexts))
                continue
            try:
                duration_ms = int((time.time() - start_time) * 1000)
                record_processing_metrics(
                    processor_name=self.get_name(),
                    operation="screenshot_process",
                    duration_ms=duration_ms,
                    context_count=len(processed_contexts),
                )

                # Record context count by type
                for context in processed_contexts:
                    increment_data_count("context", count=1, context_type=context.extracted_data.context_type.value)

                # Increment processed screenshots count
                increment_recording_stat("processed", len(processed_contexts))

            except ImportError:
                pass
            unprocessed_contexts.clear()
            last_process_time = int(time.time())

    async def _process_vlm_single(self, raw_context: RawContextProperties) -> List[ProcessedContext]:
        """
        Process a single screenshot with VLM
        """
        prompt_group = get_prompt_group(
            "processing.extraction.screenshot_analyze"
        )
        system_prompt = prompt_group.get("system")
        user_prompt_template = prompt_group.get("user")
        if not system_prompt or not user_prompt_template:
            logger.error("Failed to get complete prompt for screenshot_analyze.")
            raise ValueError("Missing prompt configuration for screenshot_analyze")

        # Prepare image data
        image_path = raw_context.content_path
        if not image_path or not os.path.exists(image_path):
            logger.error(f"Screenshot path is invalid or does not exist: {image_path}")
            raise ValueError(f"Screenshot path is invalid or does not exist: {image_path}")

        base64_image = self._encode_image_to_base64(image_path)
        if not base64_image:
            logger.warning(f"Failed to encode image: {image_path}")
            raise ValueError(f"Failed to encode image: {image_path}")

        content = [
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{base64_image}",
                },
            }
        ]

        time_now = datetime.datetime.now()
        user_prompt = user_prompt_template.format(
            current_date=time_now.isoformat(),
            current_timestamp=int(time_now.timestamp()),
            current_timezone=time_now.tzname(),
        )
        content.insert(0, {"type": "text", "text": user_prompt})
        system_prompt = system_prompt.format(
            context_type_descriptions=get_context_type_descriptions_for_extraction()
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content},
        ]

        raw_llm_response = ''
        try:
            raw_llm_response = await generate_with_messages_async(messages)
        except Exception as e:
            logger.error(f"Failed to get VLM response. Error: {e}")
            raise ValueError(f"Failed to get VLM response. Error: {e}")

        raw_resp = parse_json_from_response(raw_llm_response)
        if not raw_resp:
            logger.error(f"Empty VLM response.")
            raise ValueError(f"Empty VLM response.")
        
        items = raw_resp.get("items", [])
        processed_items = []
        for item in items:
            processed_items.append(self._create_processed_context(item, raw_context))
        return processed_items

    async def _merge_contexts(self, processed_items: List[ProcessedContext]) -> List[ProcessedContext]:
        """
        Merge newly processed items with cached items based on context_type semantics.
        """
        if not processed_items:
            return []

        # Group by context_type
        items_by_type = {}
        for item in processed_items:
            context_type = item.extracted_data.context_type
            items_by_type.setdefault(context_type, []).append(item)

        tasks = []
        for context_type, new_items in items_by_type.items():
            cached_items = list(self._processed_cache.get(context_type.value, {}).values())
            tasks.append(self._merge_items_with_llm(context_type, new_items, cached_items))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_newly_created = []
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Merge task {idx} failed with error: {result} for context type: {context_type.value}")
                continue
            if result:
                context_type = result.get("context_type")
                all_newly_created.extend(result.get("processed_contexts", []))
                self._processed_cache[context_type] = result.get("new_ctxs", {})
                for item_id in result.get("need_to_del_ids", []):
                    get_storage().delete_processed_context(item_id, context_type)
        return all_newly_created

    async def _merge_items_with_llm(self, context_type: ContextType, new_items: List[ProcessedContext], cached_items: List[ProcessedContext]) -> Dict[str, Any]:
        """
        Call LLM to merge items and directly return ProcessedContext objects.
        Handles both merged (multiple items -> one) and new (independent) items.
        """
        prompt_group = get_prompt_group("merging.screenshot_batch_merging")
        all_items_map = {item.id: item for item in new_items + cached_items}
        items_json = json.dumps([self._item_to_dict(item) for item in new_items + cached_items], ensure_ascii=False, indent=2)

        messages = [
            {"role": "system", "content": prompt_group["system"]},
            {"role": "user", "content": prompt_group["user"].format(
                context_type=context_type.value,
                items_json=items_json
            )},
        ]
        response = await generate_with_messages_async(messages)


        if not response:
            raise ValueError(f"Empty LLM response when merge items for context type: {context_type.value}")

        response_data = parse_json_from_response(response)
        if not isinstance(response_data, dict) or "items" not in response_data:
            logger.error(f"merge_items_with_llm, Invalid response format: {response_data}")
            raise ValueError(f"Invalid response format when merge items for context type: {context_type.value}")

        # Process results and build ProcessedContext objects
        result_contexts = []
        now = datetime.datetime.now()
        if context_type.value not in self._processed_cache:
            self._processed_cache[context_type.value] = {}
        need_to_del_ids = []
        final_context = None
        new_ctxs = {}
        entity_refresh_items = []
        for result in response_data.get("items", []):
            merge_type = result.get("merge_type")
            data = result.get("data", {})

            if merge_type == "merged":
                merged_ids = result.get("merged_ids", [])
                if not merged_ids:
                    logger.error(f"merged type but no merged_ids, skipping")
                    continue
                items_to_merge = [all_items_map[id] for id in merged_ids if id in all_items_map]
                if not items_to_merge:
                    logger.error(f"No valid items for merged_ids: {merged_ids}")
                    continue

                min_create_time = min((i.properties.create_time for i in items_to_merge if i.properties.create_time), default=now)
                event_time = self._parse_event_time_str(
                    data.get("event_time"),
                    max((i.properties.event_time for i in items_to_merge if i.properties.event_time), default=now)
                )

                all_raw_props = []
                for item in items_to_merge:
                    all_raw_props.extend(item.properties.raw_properties)

                merged_ctx = ProcessedContext(
                    properties=ContextProperties(
                        raw_properties=all_raw_props,
                        create_time=min_create_time,
                        update_time=now,
                        event_time=event_time,
                        enable_merge=True,
                        is_happend=event_time <= now if event_time else False,
                        duration_count=sum(i.properties.duration_count for i in items_to_merge),
                        merge_count=sum(i.properties.merge_count for i in items_to_merge) + 1,
                    ),
                    extracted_data=ExtractedData(
                        title=data.get("title", ""),
                        summary=data.get("summary", ""),
                        keywords=sorted(set(data.get("keywords", []))),
                        entities=[],  # Will be populated below
                        context_type=context_type,
                        importance=self._safe_int(data.get("importance")),
                        confidence=self._safe_int(data.get("confidence")),
                    ),
                    vectorize=Vectorize(
                        content_format=ContentFormat.TEXT,
                        text=f"{data.get('title', '')} {data.get('summary', '')}",
                    ),
                )

                final_context = merged_ctx
                need_to_del_ids.extend([item.id for item in items_to_merge if item.id in self._processed_cache.get(context_type.value, {})])
                logger.debug(f"Merged {len(merged_ids)} items for context type: {context_type.value}")
            elif merge_type == "new":
                # Independent new item
                merged_ids = result.get("merged_ids", [])
                if not merged_ids or merged_ids[0] not in all_items_map:
                    logger.error(f"new type but no merged_ids or merged_ids[0] not in all_items_map, skipping")
                    continue
                if merged_ids[0] in self._processed_cache.get(context_type.value, {}):
                    continue
                final_context = all_items_map[merged_ids[0]]
            new_ctxs[final_context.id] = final_context
            entity_refresh_items.append(final_context)

        # Second pass: parallel refresh entities
        entity_tasks = [
            self._parse_single_context(item, data.get("entities", []))
            for item in entity_refresh_items
        ]
        # Execute all entity refresh tasks in parallel
        entities_results = await asyncio.gather(*entity_tasks, return_exceptions=True)
        for entities_result in entities_results:
            if isinstance(entities_result, Exception):
                logger.error(f"Entity refresh failed for context {item.id}: {entities_result}")
            else:
                result_contexts.append(entities_result)

        return {"processed_contexts": result_contexts, "need_to_del_ids": need_to_del_ids, "new_ctxs": new_ctxs, "context_type": context_type.value}

    async def _parse_single_context(self, item: ProcessedContext, entities: List[Dict[str, Any]]) -> ProcessedContext:
        """Parse a single context item."""
        entities_info = validate_and_clean_entities(entities)
        vectorize_task = do_vectorize_async(item.vectorize)
        entities_task = refresh_entities(entities_info, item.vectorize.text)
        _, entities_results = await asyncio.gather(vectorize_task, entities_task)
        item.extracted_data.entities = entities_results
        return item

    def _parse_event_time_str(self, time_str: Optional[str], default: datetime.datetime) -> datetime.datetime:
        """Parse ISO time string, return default if invalid."""
        if not time_str or time_str == "null":
            return default
        try:
            if any(
                invalid_char in time_str
                for invalid_char in ["xxxx", "XXXX", "TZ:TZ", "TZ", "????"]
            ):
                event_time = default
            elif time_str.endswith("Z"):
                time_str = time_str[:-1] + "+00:00"
                event_time = datetime.datetime.fromisoformat(time_str)
                return event_time
            return default
        except (ValueError, TypeError):
            return default

    def _safe_int(self, value, default=0) -> int:
        """Safely convert to int."""
        if value is None or value == "" or value == "null":
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    def _item_to_dict(self, item: ProcessedContext) -> Dict[str, Any]:
        """Convert a ProcessedContext item to a dictionary for LLM."""
        return {
            **item.extracted_data.to_dict(),
            "id": item.id,
            "event_time": item.properties.event_time.isoformat()
            if item.properties.event_time
            else None,
        }

    async def batch_process(self, raw_contexts: List[RawContextProperties]) -> List[ProcessedContext]:
        """
        Batch process screenshots using Vision LLM with concurrent batch processing
        """

        logger.info(f"Processing {len(raw_contexts)} screenshots concurrently")

        # Step 1: Process all VLM tasks concurrently
        vlm_results = await asyncio.gather(
            *[self._process_vlm_single(raw_context) for raw_context in raw_contexts],
            return_exceptions=True
        )

        all_vlm_items = []
        for idx, result in enumerate(vlm_results):
            if isinstance(result, Exception):
                logger.error(f"Screenshot {idx} failed with error: {result}")
                increment_recording_stat("failed", 1)
                record_processing_error(str(result), processor_name=self.get_name(), context_count=1)
                continue
            if result:
                # for item in result:
                #     print(f"result.extracted_data.context_type: {item.extracted_data.context_type} result: {item.vectorize.text}")
                #     print("-"*80)
                all_vlm_items.extend(result)

        if not all_vlm_items:
            return []

        logger.info(f"VLM parsing completed, got {len(all_vlm_items)} items")

        # Step 2: Merge contexts concurrently
        newly_processed_contexts = await self._merge_contexts(all_vlm_items)
        return newly_processed_contexts

    def _create_processed_context(self, analysis: Dict[str, Any], raw_context: RawContextProperties = None) -> ProcessedContext:
        now = datetime.datetime.now()
        if not analysis:
            logger.warning(f"Skipping incomplete item: {analysis}")
            return None
        context_type = None
        try:
            context_type_str = analysis.get("context_type", "semantic_context")
            # Use the robust context type helper
            from opencontext.models.enums import get_context_type_for_analysis
            context_type = get_context_type_for_analysis(context_type_str)
        except Exception as e:
            logger.warning(f"Error processing context_type: {e}, using default activity_context.")
            from opencontext.models.enums import ContextType
            context_type = ContextType.ACTIVITY_CONTEXT

        event_time = self._parse_event_time_str(analysis.get("event_time"), now)

        # Entity extraction moved to merge phase
        entities = []
        raw_keywords = analysis.get("keywords", [])
        extracted_data = ExtractedData(
            title=analysis.get("title", ""),
            summary=analysis.get("summary", ""),
            keywords=sorted(list(set(raw_keywords))),
            entities=entities,
            context_type=context_type,
            importance=self._safe_int(analysis.get("importance"), 0),
            confidence=self._safe_int(analysis.get("confidence"), 0),
        )

        new_context = ProcessedContext(
            properties=ContextProperties(
                raw_properties=[raw_context] if raw_context else [],
                source=ContextSource.SCREENSHOT,
                create_time=raw_context.create_time if raw_context else now,
                update_time=now,
                event_time=event_time,
                enable_merge=True,
                is_happend=event_time <= now,
            ),
            extracted_data=extracted_data,
            vectorize=Vectorize(
                content_format=ContentFormat.TEXT,
                text=f"{extracted_data.title} {extracted_data.summary}",
            ),
        )
        return new_context

    def _encode_image_to_base64(self, image_path: str) -> Optional[str]:
        """Encode image file to base64 string."""
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode("utf-8")
        except Exception as e:
            logger.error(f"Error encoding image {image_path} to base64: {e}")
            return None
