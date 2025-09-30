#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Processor component factory implementing the Factory design pattern.
Provides centralized creation and management of processor instances.
"""

import importlib
from typing import Any, Dict, List, Optional, Type, Protocol

from opencontext.config import GlobalConfig
from opencontext.utils.logging_utils import get_logger
from opencontext.interfaces import IContextProcessor
from opencontext.context_processing.merger.context_merger import ContextMerger
from opencontext.context_processing.processor.document_processor import DocumentProcessor
from opencontext.context_processing.processor.screenshot_processor import ScreenshotProcessor

logger = get_logger(__name__)


class ProcessorDependencies(Protocol):
    """Protocol defining processor dependencies for better type safety."""
    prompt_manager: Optional[Any]
    storage: Optional[Any]


class ProcessorFactory:
    """
    Factory class for creating processor instances.
    
    Implements the Factory design pattern to provide centralized processor creation
    with dependency injection and configuration management.
    
    Features:
    - Type-safe processor registration and creation
    - Automatic dependency injection based on constructor signatures
    - Configuration validation and management
    - Extensible processor type registration
    """

    def __init__(self):
        """Initialize the processor factory with built-in processor types."""
        self._processor_registry: Dict[str, Type[IContextProcessor]] = {}
        self._register_built_in_processors()

    def _register_built_in_processors(self) -> None:
        """Register all built-in processor types."""
        built_in_processors = {
            "document_processor": DocumentProcessor,
            "screenshot_processor": ScreenshotProcessor,
            "context_merger": ContextMerger,
        }
        
        for name, processor_class in built_in_processors.items():
            self.register_processor_type(name, processor_class)
        
        logger.info(f"Registered {len(built_in_processors)} built-in processor types")

    def register_processor_type(
        self, 
        type_name: str, 
        processor_class: Type[IContextProcessor]
    ) -> bool:
        """
        Register a new processor type.
        
        Args:
            type_name: Unique name for the processor type
            processor_class: Class implementing IContextProcessor
            
        Returns:
            True if registration was successful, False otherwise
        """
        if not issubclass(processor_class, IContextProcessor):
            logger.error(f"Processor class {processor_class.__name__} must implement IContextProcessor")
            return False
            
        if type_name in self._processor_registry:
            logger.warning(f"Processor type '{type_name}' already registered, overwriting")
            
        self._processor_registry[type_name] = processor_class
        logger.debug(f"Registered processor type '{type_name}' -> {processor_class.__name__}")
        return True

    def get_registered_types(self) -> List[str]:
        """
        Get all registered processor type names.
        
        Returns:
            List of registered processor type names
        """
        return list(self._processor_registry.keys())

    def is_type_registered(self, type_name: str) -> bool:
        """
        Check if a processor type is registered.
        
        Args:
            type_name: Name of the processor type to check
            
        Returns:
            True if the type is registered, False otherwise
        """
        return type_name in self._processor_registry

    def create_processor(
        self, 
        type_name: str, 
        config: Optional[Dict[str, Any]] = None,
        **dependencies
    ) -> Optional[IContextProcessor]:
        """
        Create a processor instance with automatic dependency injection.
        
        Args:
            type_name: Name of the processor type to create
            config: Configuration dictionary for the processor (deprecated, will be ignored)
            **dependencies: Named dependencies (deprecated, will be auto-filled from global config)
            
        Returns:
            Processor instance if creation was successful, None otherwise
        """
        processor_class = self._processor_registry.get(type_name)
        if not processor_class:
            logger.error(f"Processor type '{type_name}' is not registered")
            return None

        try:
            # Directly create processor instance, all processors now use parameterless constructors
            processor_instance = processor_class()
            
            if processor_instance:
                logger.info(f"Successfully created processor instance of type '{type_name}'")
                return processor_instance
            else:
                logger.error(f"Failed to create processor instance of type '{type_name}'")
                return None
                
        except Exception as e:
            logger.exception(f"Error creating processor '{type_name}': {e}")
            return None

    def create_processor_with_validation(
        self, 
        type_name: str, 
        config: Optional[Dict[str, Any]] = None,
        **dependencies
    ) -> Optional[IContextProcessor]:
        """
        Create processor with configuration validation.
        
        Args:
            type_name: Name of the processor type to create
            config: Configuration dictionary for the processor (deprecated)
            **dependencies: Named dependencies (deprecated)
            
        Returns:
            Processor instance if creation and validation were successful
        """
        processor = self.create_processor(type_name)
        if not processor:
            return None
            
        # Validate configuration if processor supports it
        if hasattr(processor, 'validate_config'):
            # Get configuration from global config for validation
            global_config = GlobalConfig.get_instance()
            processor_config = global_config.get_config(f'processing.{type_name}') or {}
            if not processor.validate_config(processor_config):
                logger.error(f"Configuration validation failed for processor '{type_name}'")
                return None
                
        return processor


# Global factory instance for backward compatibility
processor_factory = ProcessorFactory()