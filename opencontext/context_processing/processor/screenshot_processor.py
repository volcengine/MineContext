#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Screenshot processor
"""
import asyncio
import queue
import threading
from typing import Any, Dict, List, Optional, Tuple
import os, datetime
from collections import deque
import base64
import time


from opencontext.context_processing.processor.base_processor import BaseContextProcessor
from opencontext.context_processing.processor.entity_processor import refresh_entities, validate_and_clean_entities
from opencontext.models.context import *
from opencontext.utils.json_parser import parse_json_from_response
from opencontext.llm.global_vlm_client import generate_with_messages_async
from opencontext.llm.global_embedding_client import do_vectorize
from opencontext.storage.global_storage import get_storage
from opencontext.utils.logging_utils import get_logger
from opencontext.utils.image import resize_image, calculate_phash
from opencontext.tools.tool_definitions import  ALL_TOOL_DEFINITIONS
import heapq

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
        config = get_config('processing.screenshot_processor') or {}
        super().__init__(config)
        
        self.prompt_manager = get_prompt_manager()
        
        self._similarity_hash_threshold = self.config.get("similarity_hash_threshold", 2)
        self._batch_size = self.config.get("batch_size", 10)
        self._batch_timeout = self.config.get("batch_timeout", 20) # seconds
        self._max_raw_properties = self.config.get("max_raw_properties", 5)
        self._max_image_size = self.config.get("max_image_size", 0)
        self._resize_quality = self.config.get("resize_quality", 95)
        self._enabled_delete = self.config.get("enabled_delete", False)
        
        self._stop_event = threading.Event()

        # Pipeline related
        self._input_queue = queue.Queue(maxsize=self._batch_size*2)
        self._processing_task = threading.Thread(target=self._run_processing_loop, daemon=True)
        self._processing_task.start()
        
        # State cache
        self._processed_cache = {} # Store processed contexts for MERGE operations, key: id, value: ProcessedContext
        self._current_screenshot = deque(maxlen=self._batch_size*2)
    
    @property
    def storage(self):
        """Get storage from global singleton"""
        return get_storage()

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
        return isinstance(context, RawContextProperties) and context.source == ContextSource.SCREENSHOT

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
            diff = bin(int(str(new_phash), 16) ^ int(str(item['phash']), 16)).count('1')
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
        self._current_screenshot.append({'phash': new_phash, 'id': new_context.object_id})
            
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
                self._input_queue.put(context) 
        except Exception as e:
            logger.exception(f"Error processing screenshot {context.content_path}: {e}")
            return False
        return True

    def _run_processing_loop(self):
        """Background processing loop for handling screenshots in input queue."""
        unprocessed_contexts = []
        last_process_time = int(time.time())
        while not self._stop_event.is_set():
            try:
                # Wait for new items or timeout
                raw_context = self._input_queue.get(timeout=self._batch_timeout)
                if raw_context is None: # sentinel value
                    logger.info("Received sentinel value, exiting processing loop")
                    break
                # Process deduplication
                unprocessed_contexts.append(raw_context)
                if (int(time.time()) - last_process_time) < self._batch_timeout * 2 and len(unprocessed_contexts) < self._batch_size:
                    # logger.info(f"Screenshots in cache: {len(unprocessed_contexts)}")
                    continue
            except queue.Empty:
                # logger.info("Queue empty, waiting for new data")
                continue
            except Exception as e:
                logger.error(f"Unexpected error in processing loop: {e}")
                time.sleep(1)
            time1 = int(time.time())
            try:
                # Create new event loop to run async methods
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(self.batch_process(unprocessed_contexts))
                finally:
                    loop.close()
            except Exception as e:
                logger.error(f"Unexpected error in batch_process: {e}")
                continue
            time2 = int(time.time())
            logger.info(f"processed {len(unprocessed_contexts)} cost: {time2 - time1} seconds")
            unprocessed_contexts.clear()
            last_process_time = int(time.time())

    async def batch_process(self, raw_contexts: List[RawContextProperties]) -> bool:
        """
        Batch process screenshots using Vision LLM
        """
        start_time = time.time()
        
        prompt_group = self.prompt_manager.get_prompt_group("processing.extraction.screenshot_contextual_batch")
        system_prompt = prompt_group.get("system")
        user_prompt_template = prompt_group.get("user")

        if not system_prompt or not user_prompt_template:
            logger.error("Failed to get complete prompt for screenshot_contextual_batch.")
            return False

        # Prepare image data
        content = []
        for i in range(len(raw_contexts)):
            image_path = raw_contexts[i].content_path
            if not image_path or not os.path.exists(image_path):
                logger.error(f"Screenshot path is invalid or does not exist: {image_path}")
                continue
            base64_image = self._encode_image_to_base64(image_path)
            if base64_image:
                content.append(({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{base64_image}",
                    }
                }))

        if not content:
            logger.warning("No valid images for processing.")
            return False

        # Prepare historical context
        history_contexts = list(self._processed_cache.values())
        history_contexts.reverse()
        history_str = "\n".join([f"- ID: {h.id}\n  analysis: {h.extracted_data.to_dict()}" for h in history_contexts]) if history_contexts else ""

        time_now = datetime.datetime.now().astimezone()
        user_prompt = user_prompt_template.format(
            current_date=time_now.isoformat(),
            current_timestamp = int(time_now.timestamp()),
            current_timezone=time_now.tzname(),
            history=history_str,
            total_screenshots=len(raw_contexts),
        )
        content.insert(0, {"type": "text", "text": user_prompt})
        system_prompt = system_prompt.format(
            context_type_descriptions=self.prompt_manager.get_context_type_descriptions_for_extraction()
        )
        # logger.info(f"system_prompt: {system_prompt}")
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content}
        ]
        try:
            raw_llm_response = await generate_with_messages_async(messages, tools=ALL_TOOL_DEFINITIONS)
        except Exception as e:
            logger.error(f"Failed to get raw LLM response for batch of screenshots. Error: {e}")
            return False

        if not raw_llm_response:
            logger.error(f"Empty LLM response for batch of {len(raw_contexts)} screenshots. Please check LLM configuration and API status.")
            return False

        raw_resp = parse_json_from_response(raw_llm_response)

        if not raw_resp:
            logger.error(f"Failed to parse JSON from Vision LLM response. Raw response: {raw_llm_response}")
            return False

        newly_processed_contexts, removed_context_ids = await self._create_processed_contexts(raw_resp, raw_contexts)
        
        self._processed_cache.clear()
        for context in newly_processed_contexts:
            self._processed_cache[context.id] = context
        logger.debug(f"Written {len(newly_processed_contexts)} contexts, removed {len(removed_context_ids)} contexts")
        self.storage.batch_upsert_processed_context(newly_processed_contexts)
        # self.storage.delete(removed_context_ids)
        
        # Record successful processing metrics
        try:
            from opencontext.monitoring import record_processing_metrics
            duration_ms = int((time.time() - start_time) * 1000)
            record_processing_metrics(
                processor_name=self.get_name(),
                operation="batch_process",
                duration_ms=duration_ms,
                context_count=len(newly_processed_contexts)
            )
        except ImportError:
            pass
        return True

    async def _create_processed_contexts(self, raw_resp: Any, raw_contexts: List[RawContextProperties]) -> Tuple[List[ProcessedContext], List[str]]:
        """
        Create or merge processed context objects based on LLM extracted data.
        This method follows rules defined in `screenshot_contextual_batch` prompt.
        """
        # Handle when LLM returns a list instead of dict
        if isinstance(raw_resp, list) and raw_resp:
            raw_resp = raw_resp[0]
        
        if not isinstance(raw_resp, dict) or 'items' not in raw_resp or not isinstance(raw_resp.get('items'), list):
            logger.warning(f"LLM returned unprocessable data format: {raw_resp}")
            return [], []
        # logger.info(f"Data format returned from LLM: {raw_resp}")
        newly_processed_contexts = []
        removed_context_ids = set()
        items_to_process = raw_resp.get('items', [])
        now = datetime.datetime.now().astimezone()

        context_hash_map = {}
        for item in self._current_screenshot:
            context_hash_map[item['id']] = item['phash']
        for item in items_to_process:
            decision = item.get('decision')
            analysis = item.get('analysis')
            history_id = item.get('history_id')
            screen_ids = item.get('screen_ids', [])
            if not decision or not analysis:
                logger.warning(f"Skipping incomplete item: {item}")
                continue
            context_type = None
            try:
                context_type_str = analysis.get("context_type", "semantic_context")
                # Use the robust context type helper
                from opencontext.models.enums import get_context_type_for_analysis
                context_type = get_context_type_for_analysis(context_type_str)
            except Exception as e:
                logger.warning(f"Error processing context_type: {e}, using default semantic_context.")
                from opencontext.models.enums import ContextType
                context_type = ContextType.SEMANTIC_CONTEXT
            # Safe integer conversion helper
            def safe_int(value, default=0):
                if value is None or value == '' or value == 'null':
                    return default
                try:
                    return int(value)
                except (ValueError, TypeError):
                    return default

            event_time = None
            if analysis.get("event_time", "null") != "null" and analysis.get("event_time") is not None:
                event_time_str = analysis.get("event_time")

                if any(invalid_char in event_time_str for invalid_char in ['xxxx', 'XXXX', 'TZ:TZ', 'TZ', '????']):
                    event_time = now
                else:
                    if event_time_str.endswith('Z'):
                        event_time_str = event_time_str[:-1] + '+00:00'
                    
                    try:
                        event_time = datetime.datetime.fromisoformat(event_time_str)
                        if event_time.tzinfo is None:
                            event_time = event_time.astimezone()
                    except ValueError as e:
                        logger.warning(f"Cannot parse event time '{event_time_str}': {e}, using current time")
                        event_time = now
            else:
                event_time = now

            raw_entities = analysis.get("entities", [])
            entities_info = validate_and_clean_entities(raw_entities)
            context_text = f"{analysis.get('title', '')} {analysis.get('summary', '')}"
            entities = refresh_entities(
                entities_info,
                context_text
            )
            raw_keywords = analysis.get("keywords", [])
            extracted_data=ExtractedData(
                title=analysis.get("title", ""),
                summary=analysis.get("summary", ""),
                keywords=sorted(list(set(raw_keywords))),
                entities=entities,
                context_type=context_type,
                importance=safe_int(analysis.get("importance"), 0),
                confidence=safe_int(analysis.get("confidence"), 0),
            )

            raw_context_properties = []
            valid_screen_ids = []
            for index in screen_ids:
                idx = int(index) - 1
                if not isinstance(idx, int) or idx < 0 or idx >= len(raw_contexts):
                    logger.warning(f"Invalid screenshot index: {index}, valid range is 1-{len(raw_contexts)}")
                    continue
                raw_context_properties.append(raw_contexts[idx])
                valid_screen_ids.append(index)
            
            if not raw_context_properties:
                logger.error(f"All screenshot indices invalid, skipping item: {screen_ids}")
                continue
            new_context = ProcessedContext(
                properties=ContextProperties(
                    raw_properties=raw_context_properties,
                    source=ContextSource.SCREENSHOT,
                    create_time=now,
                    update_time=now,
                    event_time=event_time,
                    enable_merge=True, 
                    is_happend=event_time <= now,
                ),
                extracted_data=extracted_data,
                vectorize=Vectorize(content_format=ContentFormat.TEXT, text=f"{extracted_data.title} {extracted_data.summary}")
            )
            all_raw_properties = {}
            all_raw_properties.update({raw_property.object_id: raw_property for raw_property in new_context.properties.raw_properties})
            if decision == 'MERGE' and history_id and history_id in self._processed_cache:
                history_context = self._processed_cache.pop(history_id)
                all_raw_properties.update({raw_property.object_id: raw_property for raw_property in history_context.properties.raw_properties})
                new_context.properties.duration_count += history_context.properties.duration_count
                new_context.properties.create_time = history_context.properties.create_time # Inherit creation time
                removed_context_ids.add(history_id)
            # elif decision == 'MERGE' and history_id not in self._processed_cache:
            #     logger.info(f"上下文 {history_id} 不存在，无法合并到新上下文 {new_context.id}。")
            for raw_property in all_raw_properties.values():
                if raw_property.object_id not in context_hash_map:
                    temp_hash = calculate_phash(raw_property.content_path)
                    if temp_hash is not None:
                        context_hash_map[raw_property.object_id] = temp_hash
            # Distribute images
            priority_queue = []
            object_ids = list(all_raw_properties.keys())
            for i in range(len(object_ids)):
                min_dist = float('inf')
                for j in range(len(object_ids)):
                    if i == j:
                        continue
                    if object_ids[i] not in context_hash_map or object_ids[j] not in context_hash_map:
                        continue
                    hash1 = context_hash_map[object_ids[i]]
                    hash2 = context_hash_map[object_ids[j]]
                    dist = bin(int(str(hash1), 16) ^ int(str(hash2), 16)).count('1')
                    if dist < min_dist:
                        min_dist = dist
                heapq.heappush(priority_queue, (-min_dist, object_ids[i]))
            new_raw_properties = []
            while len(priority_queue) > 0 and len(new_raw_properties) < self._max_raw_properties:
                _, object_id = heapq.heappop(priority_queue)
                if object_id in all_raw_properties:
                    new_raw_properties.append(all_raw_properties[object_id])
 
            new_context.properties.raw_properties = new_raw_properties
            do_vectorize(new_context.vectorize)
            newly_processed_contexts.append(new_context)
        return newly_processed_contexts, list(removed_context_ids)

    def _encode_image_to_base64(self, image_path: str) -> Optional[str]:
        """Encode image file to base64 string."""
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            logger.error(f"Error encoding image {image_path} to base64: {e}")
            return None