#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Component initialization utilities for OpenContext.
Separated from main OpenContext class for better maintainability.
"""

import importlib
from typing import Dict, Any, Optional

from opencontext.config.config_manager import ConfigManager
from opencontext.config.global_config import GlobalConfig
from opencontext.managers.capture_manager import ContextCaptureManager
from opencontext.managers.processor_manager import ContextProcessorManager
from opencontext.managers.consumption_manager import ConsumptionManager
from opencontext.storage.global_storage import get_storage
from opencontext.storage.unified_storage import UnifiedStorage
from opencontext.context_processing.processor.processor_factory import ProcessorFactory
from opencontext.config.prompt_manager import PromptManager
from opencontext.utils.logging_utils import get_logger
# Import capture components
from opencontext.context_capture.screenshot import ScreenshotCapture
from opencontext.context_capture.vault_document_monitor import VaultDocumentMonitor

# Import consumption components
from opencontext.context_consumption.generation import *
from opencontext.context_consumption.completion import CompletionService

logger = get_logger(__name__)

# Component mappings
CAPTURE_COMPONENTS = {
    'screenshot': ScreenshotCapture,
    'vault_document_monitor': VaultDocumentMonitor,
}

CONSUMPTION_COMPONENTS = {
    'smart_tip_generator': SmartTipGenerator,
    'realtime_activity_monitor': RealtimeActivityMonitor,
    'generation_report': ReportGenerator,
    'smart_todo_manager': SmartTodoManager,
}


class ComponentInitializer:
    """Handles initialization of various OpenContext components."""
    
    def __init__(self):
        # Use global config
        global_config = GlobalConfig.get_instance()
        self.config_manager = global_config.get_config_manager()
        
        self.config = self.config_manager.get_config() if self.config_manager else GlobalConfig.get_instance().get_config()
        self.global_config = GlobalConfig.get_instance()
        
    def _to_camel_case(self, name: str) -> str:
        """Convert snake_case to CamelCase."""
        return "".join(word.capitalize() for word in name.split('_'))
    
    def initialize_capture_components(self, capture_manager: ContextCaptureManager) -> None:
        """Initialize context capture components."""
        capture_config = self.config.get("capture", {})
        if not capture_config or not capture_config.get("enabled", False):
            logger.info("Capture modules not found or not enabled in configuration")
            return

        for name, config in capture_config.items():
            if name == "enabled" or not isinstance(config, dict) or not config.get("enabled", False):
                continue
            
            try:
                component_instance = self._create_capture_component(name, config)
                capture_manager.register_component(name, component_instance)
                capture_manager.initialize_component(name, config)
                logger.info(f"Capture component '{name}' initialized successfully")

            except Exception as e:
                logger.error(f"Failed to initialize capture component '{name}': {e}")
                raise RuntimeError(f"Failed to initialize capture component '{name}'") from e
    
        logger.info("Context capture modules initialization complete")
    
    def _create_capture_component(self, name: str, config: Dict[str, Any]):
        """Create a capture component instance."""
        if name in CAPTURE_COMPONENTS:
            component_class = CAPTURE_COMPONENTS[name]
            return component_class()
        
        # Fallback to dynamic import
        module_path = config.get("module")
        class_name = config.get("class")
        
        if not module_path or not class_name:
            module_path = f"opencontext.context_capture.{name}"
            class_name = f"{self._to_camel_case(name)}Capture"
            logger.info(f"Auto-inferred capture component '{name}' module='{module_path}' and class='{class_name}'")

        module = importlib.import_module(module_path)
        component_class = getattr(module, class_name)
        return component_class()
    
    def initialize_processors(
        self, 
        processor_manager: ContextProcessorManager,
        processed_context_callback
    ) -> None:
        """
        Initialize context processors.
        
        Processors now automatically obtain required dependencies from global configuration.
        """
        processing_config = self.config.get("processing", {})
        if not processing_config or not processing_config.get("enabled", False):
            logger.info("Processing modules not found or not enabled in configuration")
            return
            
        processor_factory = ProcessorFactory()
        
        # Now config.yaml structure is flattened, directly under processing
        # Create various processors
        processor_types = ['document_processor', 'screenshot_processor']
        
        for processor_type in processor_types:
            processor_config = processing_config.get(processor_type, {})
            if processor_config.get('enabled', False):
                try:
                    # Now processors use parameterless constructors
                    processor = processor_factory.create_processor(processor_type)
                    if processor:
                        processor.set_callback(processed_context_callback)
                        processor_manager.register_processor(processor)
                        logger.info(f"Processor component '{processor_type}' created and registered successfully")
                    else:
                        logger.error(f"Failed to create processor component '{processor_type}'")
                        raise RuntimeError(f"Failed to create processor component '{processor_type}'")
                except Exception as e:
                    logger.error(f"Failed to initialize processor component '{processor_type}': {e}", exc_info=True)
                    raise RuntimeError(f"Failed to initialize processor component '{processor_type}'") from e
        
        # Initialize context merger if enabled
        if processing_config.get("context_merger", {}).get("enabled", False):
            merger = processor_factory.create_processor("context_merger")
            if not merger:
                logger.error("Failed to create context merger")
                raise RuntimeError("Failed to create context merger")
            processor_manager.set_merger(merger)
            processor_manager.start_periodic_compression()
            logger.info("Periodic memory compression started")

        logger.info("Context processors initialization complete")
    
    def initialize_completion_service(self) -> Optional[CompletionService]:
        """Initialize completion service for smart content completion."""
        logger.info("Initializing completion service...")
        
        try:
            # Get completion configuration
            completion_config = self.config.get("completion", {})
            if not completion_config.get("enabled", True):
                logger.info("Completion service disabled in configuration")
                return None
            
            # Use global service instance to avoid duplicate initialization
            from opencontext.context_consumption.completion import get_completion_service
            completion_service = get_completion_service()
            logger.info("Completion service initialized successfully")
            
            return completion_service
            
        except Exception as e:
            logger.exception(f"Failed to initialize completion service: {e}")
            return None
    
    def initialize_consumption_components(self) -> ConsumptionManager:
        consumption_manager = ConsumptionManager()
        
        # Start scheduled tasks if configured
        content_generation_config = self.config.get("content_generation", {})
        if content_generation_config.get("enabled", True) and content_generation_config.get("auto_start", True):
            consumption_manager.start_scheduled_tasks(content_generation_config)
            logger.info("Content generation scheduled tasks auto-started")

        logger.info("Context consumption components initialization complete")
        return consumption_manager
    
    def _create_consumption_component(self, name: str, config: Dict[str, Any]):
        """Create a consumption component instance."""
        if name in CONSUMPTION_COMPONENTS:
            component_class = CONSUMPTION_COMPONENTS[name]
            return component_class()  # Now use parameterless constructor
        
        # Fallback to dynamic import
        module_path = config.get("module")
        class_name = config.get("class")
        
        if not module_path or not class_name:
            module_path = f"opencontext.context_consumption.{name}"
            class_name = f"{self._to_camel_case(name)}Consumer"
            logger.info(f"Auto-inferred consumption component '{name}' module='{module_path}' and class='{class_name}'")

        module = importlib.import_module(module_path)
        component_class = getattr(module, class_name)
        return component_class()