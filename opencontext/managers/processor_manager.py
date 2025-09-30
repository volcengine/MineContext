#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0


"""
Context processing manager for managing and coordinating context processing components
"""
import concurrent.futures
from typing import Any, Dict, List, Optional, Callable
from threading import Lock, Timer

from loguru import logger

from opencontext.interfaces import IContextProcessor
from opencontext.models import RawContextProperties, ProcessedContext, ContentFormat, ContextSource


class ContextProcessorManager:
    """
    Context processing manager
    
    Manages and coordinates multiple context processing components, providing unified interface for context processing
    """
    
    def __init__(self, max_workers: int = 5):
        """Initialize context processing manager"""
        self._processors: Dict[str, IContextProcessor] = {}
        self._callback: Optional[Callable[[List[Any]], None]] = None
        self._merger: Optional[IContextProcessor] = None
        self._statistics: Dict[str, Any] = {
            "total_processed_inputs": 0,
            "total_contexts_generated": 0,
            "processors": {},
            "errors": 0,
        }
        self._routing_table: Dict[ContextSource, List[str]] = {}
        self._default_chain_by_format: Dict[ContentFormat, List[str]] = {}
        self._define_routing()
        self._lock = Lock()
        self._max_workers = max_workers
        self._compression_timer: Optional[Timer] = None
        self._compression_interval: int = 1800  # default 1 hour

    def start_periodic_compression(self):
        """Start periodic memory compression"""
        self._compression_interval = self._compression_interval
        if self._compression_timer:
            self._compression_timer.cancel()

        # first execution in non-blocking mode
        self._compression_timer = Timer(1, self._run_periodic_compression)
        self._compression_timer.daemon = True
        self._compression_timer.start()

        logger.info(f"Started periodic memory compression, interval: {self._compression_interval} seconds")

    def _run_periodic_compression(self):
        """Execute and reschedule next compression"""
        if self._merger and hasattr(self._merger, 'periodic_memory_compression'):
            try:
                logger.info("Starting periodic memory compression...")
                self._merger.periodic_memory_compression(self._compression_interval)
                logger.info("Periodic memory compression completed.")
            except Exception as e:
                logger.error(f"Periodic memory compression failed: {e}", exc_info=True)
        else:
            logger.warning("Merger processor not found or does not support periodic_memory_compression, skipping periodic compression.")

        # reschedule next execution
        self._compression_timer = Timer(self._compression_interval, self._run_periodic_compression)
        self._compression_timer.daemon = True
        self._compression_timer.start()

    def stop_periodic_compression(self):
        """Stop periodic memory compression"""
        if self._compression_timer:
            self._compression_timer.cancel()
            self._compression_timer = None
            logger.info("Periodic memory compression stopped.")

    def _define_routing(self):
        """
        Define processing chain routing rules in code
        Users can modify here to customize routing
        """
        self._routing_table = {
            ContextSource.SCREENSHOT: "screenshot_processor",
            ContextSource.FILE: "document_processor",
            ContextSource.VAULT: "document_processor",
        }
        self._default_chain_by_format = {}
    
    def register_processor(self, processor: IContextProcessor) -> bool:
        """
        Register processing component
        
        Args:
            processor (IContextProcessor): Processing component instance
            
        Returns:
            bool: Whether registration succeeded
        """
        processor_name = processor.get_name()
        
        if processor_name in self._processors:
            logger.warning(f"Processing component '{processor_name}' already registered, will be overwritten")
        
        self._processors[processor_name] = processor
        self._statistics["processors"][processor_name] = processor.get_statistics()
        
        logger.info(f"Processing component '{processor_name}' registered successfully")
        return True
    
    def set_merger(self, merger: IContextProcessor) -> None:
        """
        Set merger component
        
        Args:
            merger (IContextProcessor): Merger component instance
        """
        self._merger = merger
        logger.info(f"Merger component '{merger.get_name()}' has been set")

    def get_processor(self, processor_name: str) -> Optional[IContextProcessor]:
        return self._processors.get(processor_name)

    def get_all_processors(self) -> Dict[str, IContextProcessor]:
        return self._processors.copy()

    def set_callback(self, callback: Callable[[List[Any]], None]) -> None:
        self._callback = callback

    def process(self, initial_input: RawContextProperties):
        """
        Process single input through processing chain
        """
        # 1. Dynamically select preprocessing chain based on input type (excluding merger and embedding)
        processor_name = self._routing_table.get(initial_input.source)
        if not processor_name:
            processor_name = self._default_chain_by_format.get(initial_input.content_format, [])

        if not processor_name:
            logger.error(f"No processing component defined for source_type='{initial_input.source}' or content_format='{initial_input.content_format}', no processing will be performed")
            return False

        # logger.debug(f"Selected preprocessing component for input {initial_input.object_id} (source: {initial_input.source}): {processor_name}")
        
        processor = self._processors.get(processor_name)
        if not processor or not processor.can_process(initial_input):
            logger.error(f"Processor '{processor_name}' in processing chain not registered or does not support processing input type {initial_input.source}")
            return False

        try:
            return processor.process(initial_input)
        except Exception as e:
            logger.exception(f"Processing component '{processor_name}' encountered exception while processing data: {e}")
        return false

    def batch_process(
        self, initial_inputs: List[RawContextProperties]
    ) -> Dict[str, List[ProcessedContext]]:
        """Batch process raw context data"""
        results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            future_to_input = {executor.submit(self.process, initial_input): initial_input for initial_input in initial_inputs}
            for future in concurrent.futures.as_completed(future_to_input):
                initial_input = future_to_input[future]
                try:
                    result = future.result()
                    results[initial_input.object_id] = result
                except Exception as exc:
                    logger.exception(f"'{initial_input.object_id}' generated an exception: {exc}")
                    results[initial_input.object_id] = []
        return results

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics for all processors and managers
        """
        with self._lock:
            # Update latest processor statistics
            for name, processor in self._processors.items():
                self._statistics["processors"][name] = processor.get_statistics()
            return self._statistics.copy()

    def shutdown(self, graceful: bool = False) -> None:
        """
        Close manager and all processors
        """
        logger.info("Shutting down context processing manager...")
        for processor in self._processors.values():
            processor.shutdown()
        self.stop_periodic_compression()
        logger.info("Context processing manager has been shut down")

    def reset_statistics(self) -> None:
        """
        Reset statistics for manager and all processors
        """
        with self._lock:
            for processor in self._processors.values():
                processor.reset_statistics()
            
            self._statistics["total_processed_inputs"] = 0
            self._statistics["total_contexts_generated"] = 0
            self._statistics["errors"] = 0
            logger.info("All statistics have been reset")
