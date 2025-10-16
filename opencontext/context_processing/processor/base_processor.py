#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Base context processor abstract class.
Provides common functionality and interface for all processors.
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional

from opencontext.config import GlobalConfig
from opencontext.interfaces.processor_interface import IContextProcessor
from opencontext.models.context import ProcessedContext, RawContextProperties
from opencontext.utils.logging_utils import get_logger

logger = get_logger(__name__)


class BaseContextProcessor(IContextProcessor, ABC):
    """
    Abstract base class for context processors.

    Provides common functionality and interface that all processors should implement.
    Includes statistics tracking, configuration management, and callback handling.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the base processor.

        Args:
            config: Configuration dictionary for the processor (if not provided, will be loaded from global config)
        """
        # If no config is passed, use an empty dictionary (subclasses should get it from the global config themselves)
        self.config = config or {}
        self._is_initialized = False
        self._callback: Optional[Callable[[List[ProcessedContext]], None]] = None
        self._processing_stats = {
            "processed_count": 0,
            "contexts_generated_count": 0,
            "error_count": 0,
        }

    def get_name(self) -> str:
        """Get the processor name (class name by default)."""
        return self.__class__.__name__

    @abstractmethod
    def get_description(self) -> str:
        """Get the processor description. Must be implemented by subclasses."""
        pass

    def get_version(self) -> str:
        """Get the processor version."""
        return "1.0.0"

    @property
    def is_initialized(self) -> bool:
        """Check if the processor has been initialized."""
        return self._is_initialized

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Initialize the processor with configuration.

        Args:
            config: Configuration dictionary to update current config

        Returns:
            True if initialization was successful, False otherwise
        """
        try:
            if config:
                if self.validate_config(config):
                    self.config.update(config)
                else:
                    logger.error(f"Invalid configuration for processor {self.get_name()}")
                    return False

            self._is_initialized = True
            logger.info(f"Processor {self.get_name()} initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize processor {self.get_name()}: {e}")
            return False

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate the provided configuration.

        Default implementation accepts any configuration.
        Subclasses should override this for specific validation.

        Args:
            config: Configuration dictionary to validate

        Returns:
            True if configuration is valid, False otherwise
        """
        return True

    @abstractmethod
    def can_process(self, context: Any) -> bool:
        """
        Check if this processor can handle the given context.

        Args:
            context: Context data to check

        Returns:
            True if the processor can handle this context, False otherwise
        """
        pass

    @abstractmethod
    def process(self, context: Any) -> List[ProcessedContext]:
        """
        Process a single context and return processed results.

        Args:
            context: Context data to process

        Returns:
            List of processed contexts
        """
        pass

    def batch_process(self, contexts: List[Any]) -> Dict[str, List[ProcessedContext]]:
        """
        Process multiple contexts in batch and group results by object ID.

        Args:
            contexts: List of contexts to process

        Returns:
            Dictionary mapping object IDs to lists of processed contexts
        """
        processed_by_object_id: Dict[str, List[ProcessedContext]] = {}

        for context in contexts:
            try:
                if not self.can_process(context):
                    continue

                processed_contexts = self.process(context)
                if not processed_contexts:
                    continue

                # Group results by object ID
                object_id = self._extract_object_id(context, processed_contexts)
                if object_id not in processed_by_object_id:
                    processed_by_object_id[object_id] = []
                processed_by_object_id[object_id].extend(processed_contexts)

                self._processing_stats["processed_count"] += 1
                self._processing_stats["contexts_generated_count"] += len(processed_contexts)

            except Exception as e:
                self._processing_stats["error_count"] += 1
                logger.error(f"Error processing context in {self.get_name()}: {e}")

        return processed_by_object_id

    def _extract_object_id(self, context: Any, processed_contexts: List[ProcessedContext]) -> str:
        """
        Extract object ID from context or processed contexts.

        Args:
            context: Original context
            processed_contexts: List of processed contexts

        Returns:
            Object ID string
        """
        if isinstance(context, RawContextProperties):
            return context.object_id
        elif processed_contexts:
            # Fallback to using the first processed context's ID
            return processed_contexts[0].id
        else:
            # Last resort: use string representation
            return str(id(context))

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get processing statistics for this processor.

        Returns:
            Dictionary containing processing statistics
        """
        return self._processing_stats.copy()

    def reset_statistics(self) -> bool:
        """
        Reset processing statistics to zero.

        Returns:
            True if reset was successful
        """
        try:
            self._processing_stats = {
                "processed_count": 0,
                "contexts_generated_count": 0,
                "error_count": 0,
            }
            return True
        except Exception as e:
            logger.error(f"Failed to reset statistics for {self.get_name()}: {e}")
            return False

    def set_callback(self, callback: Optional[Callable[[List[ProcessedContext]], None]]) -> bool:
        """
        Set callback function to be called when processing is complete.

        Args:
            callback: Function that accepts a list of ProcessedContext objects

        Returns:
            True if callback was set successfully
        """
        try:
            self._callback = callback
            return True
        except Exception as e:
            logger.error(f"Failed to set callback for {self.get_name()}: {e}")
            return False

    def _invoke_callback(self, processed_contexts: List[ProcessedContext]) -> None:
        """
        Invoke the callback function if it's set.

        Args:
            processed_contexts: List of processed contexts to pass to callback
        """
        if self._callback and processed_contexts:
            try:
                self._callback(processed_contexts)
            except Exception as e:
                logger.error(f"Error invoking callback in {self.get_name()}: {e}")

    def shutdown(self) -> bool:
        """
        Shutdown the processor and clean up resources.

        Returns:
            True if shutdown was successful
        """
        try:
            self._is_initialized = False
            self._callback = None
            logger.info(f"Processor {self.get_name()} shut down successfully")
            return True
        except Exception as e:
            logger.error(f"Error shutting down processor {self.get_name()}: {e}")
            return False
