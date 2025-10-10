#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
OpenContext main class - system entry point integrating all components.
Refactored for better separation of concerns and maintainability.
"""

import threading
from typing import Dict, Any, Optional, List

from opencontext.config.config_manager import ConfigManager
from opencontext.managers.capture_manager import ContextCaptureManager
from opencontext.managers.processor_manager import ContextProcessorManager
from opencontext.managers.consumption_manager import ConsumptionManager
from opencontext.models.context import RawContextProperties, ProcessedContext
from opencontext.utils.logging_utils import get_logger
from opencontext.server.component_initializer import ComponentInitializer
from opencontext.server.context_operations import ContextOperations
from opencontext.llm.global_embedding_client import GlobalEmbeddingClient
from opencontext.llm.global_vlm_client import GlobalVLMClient
from opencontext.config.global_config import GlobalConfig
from opencontext.storage.global_storage import GlobalStorage

logger = get_logger(__name__)


class OpenContext:
    """OpenContext main class - integrates all components and provides unified API."""

    def __init__(
        self,
        config_path: Optional[str] = None
    ):
        """
        Initialize OpenContext.

        Args:
            config_path: Configuration file path
            config_dict: Configuration dictionary (unused, kept for compatibility)
        """
        # Initialize core components
        self.capture_manager = ContextCaptureManager()
        self.processor_manager = ContextProcessorManager()

        self.consumption_manager: Optional[ConsumptionManager] = None
        self.workflow_engine = None  # New Agent-based workflow engine
        self.completion_service = None  # Smart completion service
        
        # Helper classes
        self.component_initializer = ComponentInitializer()
        self.context_operations: Optional[ContextOperations] = None
        
        # Web server state
        self.web_server: Optional[threading.Thread] = None
        self.web_server_running: bool = False

        logger.info("OpenContext initialization completed")

    def initialize(self) -> None:
        """Initialize all components in proper order."""
        logger.info("Starting initialization of all components...")
        
        try:
            GlobalConfig.get_instance()
            GlobalEmbeddingClient.get_instance()
            GlobalStorage.get_instance()
            GlobalVLMClient.get_instance()
            self.context_operations = ContextOperations()
            self.capture_manager.set_callback(self._handle_captured_context)
            self.component_initializer.initialize_capture_components(self.capture_manager)
            logger.info("Capture modules initialization completed")
            self.component_initializer.initialize_processors(
                self.processor_manager,
                self._handle_processed_context
            )
            self.consumption_manager = self.component_initializer.initialize_consumption_components()
            self.completion_service = self.component_initializer.initialize_completion_service()
            self._initialize_monitoring()
            logger.info("All components initialization completed successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize components: {e}", exc_info=True)
            self.shutdown(graceful=False)
            raise


    def _initialize_monitoring(self):
        """Initialize monitoring system"""
        try:
            from opencontext.monitoring import initialize_monitor
            initialize_monitor()
            logger.info("Monitoring system initialized with storage backend")
        except ImportError:
            logger.warning("Monitoring module not available, skipping monitoring initialization")
        except Exception as e:
            logger.error(f"Failed to initialize monitoring system: {e}")

    def _handle_captured_context(self, contexts: List[RawContextProperties]) -> bool:
        """
        Handle batch processing and storage of captured context data.
        """
        if not contexts:
            return False
            
        try:
            for context_data in contexts:
                self.processor_manager.process(context_data)
            return True
        except Exception as e:
            logger.error(f"Error processing captured contexts: {e}")
            return False
    
    def _handle_processed_context(self, contexts: List[ProcessedContext]) -> bool:
        """
        Store processed contexts.
        
        Args:
            contexts: List of processed contexts to store
            
        Returns:
            True if storage was successful, False otherwise
        """
        if not contexts:
            return False
            
        if self.storage:
            try:
                return self.storage.batch_upsert_processed_context(contexts)
            except Exception as e:
                logger.error(f"Error storing processed contexts: {e}")
                return False
        else:
            logger.warning("Storage is not initialized.")
            return False

    def start_capture(self) -> None:
        """Start all capture components."""
        logger.info("Starting all capture components...")
        try:
            self.capture_manager.start_all_components()
            logger.info("All capture components started successfully")
        except Exception as e:
            logger.error(f"Failed to start capture components: {e}")
            raise

    def shutdown(self, graceful: bool = True) -> None:
        """Shutdown all components gracefully.
        
        Args:
            graceful: Whether to perform graceful shutdown
        """
        logger.info("Shutting down all components...")
        
        try:
            # Stop content generation scheduled tasks
            if self.consumption_manager:
                try:
                    self.consumption_manager.stop_scheduled_tasks()
                    logger.info("Content generation scheduled tasks stopped")
                except Exception as e:
                    logger.warning(f"Error stopping content generation scheduled tasks: {e}")
            
            # Shutdown managers
            self.capture_manager.shutdown(graceful=graceful)
            self.processor_manager.shutdown(graceful=graceful)
            
            if self.web_server and self.web_server.is_alive():
                logger.info("Web server will close when main thread exits.")
                
            logger.info("All components shut down successfully.")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            if not graceful:
                raise

    def add_context(self, context_data: RawContextProperties) -> bool:
        """
        Process a single context data item.
        
        Args:
            context_data: Raw context properties to process
            
        Returns:
            True if processing was successful, False otherwise
        """
        try:
            return self.processor_manager.process(context_data)
        except Exception as e:
            logger.error(f"Error adding context: {e}")
            return False
    
    # Delegate context operations to ContextOperations helper
    def get_all_contexts(
        self, 
        limit: int = 10, 
        offset: int = 0, 
        filter_criteria: Optional[Dict[str, Any]] = None
    ) -> Dict[str, List[ProcessedContext]]:
        """Get all processed contexts."""
        if not self.context_operations:
            logger.warning("Context operations not initialized.")
            return {}
        return self.context_operations.get_all_contexts(limit, offset, filter_criteria, need_vector=False)

    def get_context(self, doc_id: str, context_type: str) -> Optional[ProcessedContext]:
        """Get a single processed context."""
        if not self.context_operations:
            logger.warning("Context operations not initialized.")
            return None
        return self.context_operations.get_context(doc_id, context_type)

    def update_context(self, doc_id: str, context: ProcessedContext) -> bool:
        """Update a processed context."""
        if not self.context_operations:
            logger.warning("Context operations not initialized.")
            return False
        return self.context_operations.update_context(doc_id, context)

    def delete_context(self, doc_id: str, context_type: str) -> bool:
        """Delete a processed context."""
        if not self.context_operations:
            logger.warning("Context operations not initialized.")
            return False
        return self.context_operations.delete_context(doc_id, context_type)

    def add_screenshot(self, path: str, window: str, create_time: str, app: str) -> Optional[str]:
        """Add a screenshot to the system."""
        if not self.context_operations:
            logger.warning("Context operations not initialized.")
            return "Context operations not initialized"
        return self.context_operations.add_screenshot(
            path, window, create_time, app, self.add_context
        )

    def search(
        self, 
        query: str, 
        top_k: int = 10, 
        context_types: Optional[List[str]] = None, 
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Perform vector search without LLM processing."""
        if not self.context_operations:
            raise RuntimeError("Context operations not initialized")
        return self.context_operations.search(query, top_k, context_types, filters)

    def get_context_types(self) -> List[str]:
        """Get all available context types."""
        if not self.context_operations:
            raise RuntimeError("Context operations not initialized")
        return self.context_operations.get_context_types()
    
    def check_components_health(self) -> Dict[str, bool]:
        """Check health status of all components."""
        return {
            "config": GlobalConfig.get_instance().is_initialized(),
            "storage": GlobalStorage.get_instance().get_storage() is not None,
            "llm": GlobalEmbeddingClient.get_instance().is_initialized() and GlobalVLMClient.get_instance().is_initialized(),
            "capture": bool(self.capture_manager),
            "consumption": bool(self.consumption_manager),
        }


def main():
    """Main entry point for running the server."""
    import argparse
    import uvicorn
    
    parser = argparse.ArgumentParser(description="OpenContext Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--config", help="Configuration file path", default="./config/config.yaml")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    
    args = parser.parse_args()
    
    print(f"Starting OpenContext Server on {args.host}:{args.port}")
    if args.config:
        print(f"Using config file: {args.config}")
    
    uvicorn.run(
        "opencontext.cli:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info"
    )


if __name__ == "__main__":
    main()