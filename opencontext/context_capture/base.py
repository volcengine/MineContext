#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0


"""
Base capture component class implementing common functionality from ICaptureComponent interface
"""

import abc
import time
import threading
from typing import Any, Dict, List, Callable
from datetime import datetime

from opencontext.interfaces.capture_interface import ICaptureComponent
from opencontext.models.context import RawContextProperties
from opencontext.models.enums import ContextSource
from opencontext.utils.logging_utils import get_logger

logger = get_logger(__name__)


class BaseCaptureComponent(ICaptureComponent):
    """
    Base capture component class implementing common functionality from ICaptureComponent interface
    
    All concrete capture components should inherit from this class and implement specific capture logic
    """
    
    def __init__(self, name: str, description: str, source_type: ContextSource):
        """
        Initialize base capture component
        
        Args:
            name (str): Component name
            description (str): Component description
            source_type (ContextSource): Capture source type
        """
        self._name = name
        self._description = description
        self._source_type = source_type
        self._config = {}
        self._running = False
        self._capture_thread = None
        self._stop_event = threading.Event()
        self._callback = None
        self._capture_interval = 1.0  # Default capture interval is 1 second
        self._last_capture_time = None
        self._capture_count = 0
        self._error_count = 0
        self._last_error = None
        self._lock = threading.RLock()
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        """
        Initialize capture component
        
        Args:
            config (Dict[str, Any]): Component configuration
            
        Returns:
            bool: Whether initialization was successful
        """
        if not self.validate_config(config):
            logger.error(f"{self._name}: Configuration validation failed")
            return False
        
        with self._lock:
            self._config = config.copy()
            
            # Set capture interval (if present in config)
            if "capture_interval" in config:
                self._capture_interval = max(0.1, float(config["capture_interval"]))
            
            try:
                # Subclasses can implement specific initialization logic in _initialize_impl
                result = self._initialize_impl(config)
                if result:
                    logger.info(f"{self._name}: Initialization successful")
                else:
                    logger.error(f"{self._name}: Initialization failed")
                return result
            except Exception as e:
                logger.exception(f"{self._name}: Exception occurred during initialization: {str(e)}")
                self._last_error = str(e)
                self._error_count += 1
                return False
    
    def start(self) -> bool:
        """
        Start capture component
        
        Returns:
            bool: Whether startup was successful
        """
        with self._lock:
            if self._running:
                logger.warning(f"{self._name}: Component is already running")
                return True
            
            try:
                # Subclasses can implement specific startup logic in _start_impl
                if not self._start_impl():
                    logger.error(f"{self._name}: Startup failed")
                    return False
                
                self._running = True
                self._stop_event.clear()
                
                # If capture interval is configured, start capture thread
                if "capture_interval" in self._config:
                    self._capture_thread = threading.Thread(
                        target=self._capture_loop,
                        name=f"{self._name}_capture_thread",
                        daemon=True
                    )
                    self._capture_thread.start()
                
                logger.info(f"{self._name}: Startup successful")
                return True
            except Exception as e:
                logger.exception(f"{self._name}: Exception occurred during startup: {str(e)}")
                self._last_error = str(e)
                self._error_count += 1
                return False
    
    def stop(self, graceful: bool = True) -> bool:
        """
        Stop capture component
        
        Returns:
            bool: Whether stopping was successful
        """
        with self._lock:
            if not self._running:
                logger.warning(f"{self._name}: Component is not running")
                return True
            
            try:
                # Stop capture thread
                if self._capture_thread and self._capture_thread.is_alive():
                    self._stop_event.set()
                    self._capture_thread.join(timeout=5.0)
                    if self._capture_thread.is_alive():
                        logger.warning(f"{self._name}: Capture thread failed to stop within 5 seconds")
                
                # Subclasses can implement specific stop logic in _stop_impl
                if not self._stop_impl(graceful=graceful):
                    logger.error(f"{self._name}: Stop failed")
                    return False
                
                self._running = False
                logger.info(f"{self._name}: Stop successful")
                return True
            except Exception as e:
                logger.exception(f"{self._name}: Exception occurred during stop: {str(e)}")
                self._last_error = str(e)
                self._error_count += 1
                return False
    
    def is_running(self) -> bool:
        """
        Check if capture component is running
        
        Returns:
            bool: Whether it is running
        """
        with self._lock:
            return self._running
    
    def capture(self) -> List[RawContextProperties]:
        """
        Execute one capture operation
        
        Returns:
            List[RawContextProperties]: List of captured context data
        """
        if not self._running:
            logger.warning(f"{self._name}: Component is not running, cannot execute capture")
            return []
        
        try:
            # Record capture start time
            start_time = time.time()
            self._last_capture_time = datetime.now()
            
            # Subclasses need to implement specific capture logic in _capture_impl
            result = self._capture_impl()
            
            # Update statistics
            self._capture_count += 1
            
            # Record capture elapsed time
            time.time() - start_time
            # if elapsed > 2.0:  # If capture takes longer than 2 seconds, log warning
            #     logger.warning(f"{self._name}: Capture operation took too long: {elapsed:.2f}s")
            # else:
            #     logger.debug(f"{self._name}: Capture operation completed, elapsed: {elapsed:.2f}s, got {len(result)} data items")
            
            # If callback function is set and data was captured, call the callback function
            if self._callback and result:
                try:
                    self._callback(result)
                except Exception as e:
                    logger.exception(f"{self._name}: Callback function execution exception: {str(e)}")
            
            return result
        except Exception as e:
            logger.exception(f"{self._name}: Exception occurred during capture: {str(e)}")
            self._last_error = str(e)
            self._error_count += 1
            return []
    
    def get_name(self) -> str:
        """
        Get capture component name
        
        Returns:
            str: Component name
        """
        return self._name
    
    def get_description(self) -> str:
        """
        Get capture component description
        
        Returns:
            str: Component description
        """
        return self._description
    
    def get_config_schema(self) -> Dict[str, Any]:
        """
        Get configuration schema
        
        Returns:
            Dict[str, Any]: Configuration schema describing types and constraints of config items
        """
        # Base configuration schema, subclasses can extend in _get_config_schema_impl
        schema = {
            "type": "object",
            "properties": {
                "auto_capture": {
                    "type": "boolean",
                    "description": "Whether to auto capture",
                    "default": False
                },
                "capture_interval": {
                    "type": "number",
                    "description": "Capture interval (seconds)",
                    "minimum": 0.1,
                    "default": 1.0
                }
            },
            "required": []
        }
        
        # Merge subclass configuration schema
        custom_schema = self._get_config_schema_impl()
        if custom_schema:
            if "properties" in custom_schema:
                schema["properties"].update(custom_schema["properties"])
            if "required" in custom_schema:
                schema["required"].extend(custom_schema["required"])
        
        return schema
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate if configuration is valid
        
        Args:
            config (Dict[str, Any]): Configuration to validate
            
        Returns:
            bool: Whether configuration is valid
        """
        try:
            # Validate basic configuration
            if "auto_capture" in config and not isinstance(config["auto_capture"], bool):
                logger.error(f"{self._name}: auto_capture must be boolean type")
                return False
            
            if "capture_interval" in config:
                try:
                    interval = float(config["capture_interval"])
                    if interval < 0.1:
                        logger.error(f"{self._name}: capture_interval must be greater than or equal to 0.1 seconds")
                        return False
                except (ValueError, TypeError):
                    logger.error(f"{self._name}: capture_interval must be numeric type")
                    return False
            
            # Subclasses can implement specific config validation logic in _validate_config_impl
            return self._validate_config_impl(config)
        except Exception as e:
            logger.exception(f"{self._name}: Exception occurred during configuration validation: {str(e)}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get component status
        
        Returns:
            Dict[str, Any]: Component status information
        """
        with self._lock:
            status = {
                "name": self._name,
                "description": self._description,
                "source_type": self._source_type.value,
                "running": self._running,
                "last_capture_time": self._last_capture_time.isoformat() if self._last_capture_time else None,
                "capture_interval": self._capture_interval,
                "auto_capture": self._config.get("auto_capture", False)
            }
            
            # Subclasses can extend status information in _get_status_impl
            custom_status = self._get_status_impl()
            if custom_status:
                status.update(custom_status)
            
            return status
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics
        
        Returns:
            Dict[str, Any]: Statistics information
        """
        with self._lock:
            stats = {
                "capture_count": self._capture_count,
                "error_count": self._error_count,
                "last_error": self._last_error,
                "uptime": (datetime.now() - self._last_capture_time).total_seconds() if self._last_capture_time else 0
            }
            
            # Subclasses can extend statistics in _get_statistics_impl
            custom_stats = self._get_statistics_impl()
            if custom_stats:
                stats.update(custom_stats)
            
            return stats
    
    def reset_statistics(self) -> bool:
        """
        Reset statistics
        
        Returns:
            bool: Whether reset was successful
        """
        with self._lock:
            try:
                self._capture_count = 0
                self._error_count = 0
                self._last_error = None
                
                # Subclasses can implement specific statistics reset logic in _reset_statistics_impl
                self._reset_statistics_impl()
                
                logger.info(f"{self._name}: Statistics have been reset")
                return True
            except Exception as e:
                logger.exception(f"{self._name}: Exception occurred during statistics reset: {str(e)}")
                return False
    
    def set_callback(self, callback: Callable[[List[RawContextProperties]], None]):
        """
        Set callback function to be called when new data is captured
        
        Args:
            callback (callable): Callback function that receives a list of RawContextProperties as parameter
            
        Returns:
            bool: Whether setting was successful
        """
        with self._lock:
            try:
                self._callback = callback
                return True
            except Exception as e:
                logger.exception(f"{self._name}: Exception occurred during callback function setup: {str(e)}")
                return False
    
    def _capture_loop(self):
        """
        Capture loop that periodically executes capture operations
        """
        logger.info(f"{self._name}: Capture thread started, interval: {self._capture_interval}s")
        
        while not self._stop_event.is_set():
            try:
                # Execute one capture operation
                self.capture()
                
                # Wait for next capture
                self._stop_event.wait(self._capture_interval)
            except Exception as e:
                logger.exception(f"{self._name}: Exception occurred in capture loop: {str(e)}")
                self._last_error = str(e)
                self._error_count += 1
                
                # After exception, wait for a while before continuing
                self._stop_event.wait(max(1.0, self._capture_interval / 2))
        
        logger.info(f"{self._name}: Capture thread stopped")
    
    # The following methods need to be implemented by subclasses
    
    @abc.abstractmethod
    def _initialize_impl(self, config: Dict[str, Any]) -> bool:
        """
        Initialization implementation
        
        Args:
            config (Dict[str, Any]): Component configuration
            
        Returns:
            bool: Whether initialization was successful
        """
    
    @abc.abstractmethod
    def _start_impl(self) -> bool:
        """
        Startup implementation
        
        Returns:
            bool: Whether startup was successful
        """
    
    @abc.abstractmethod
    def _stop_impl(self, graceful: bool = True) -> bool:
        """
        Stop implementation
        
        Returns:
            bool: Whether stop was successful
        """
    
    @abc.abstractmethod
    def _capture_impl(self) -> List[RawContextProperties]:
        """
        Capture implementation
        
        Returns:
            List[RawContextProperties]: List of captured context data
        """
    
    def _get_config_schema_impl(self) -> Dict[str, Any]:
        """
        Get configuration schema implementation
        
        Returns:
            Dict[str, Any]: Configuration schema
        """
        return {}
    
    def _validate_config_impl(self, config: Dict[str, Any]) -> bool:
        """
        Validate configuration implementation
        
        Args:
            config (Dict[str, Any]): Configuration to validate
            
        Returns:
            bool: Whether configuration is valid
        """
        return True
    
    def _get_status_impl(self) -> Dict[str, Any]:
        """
        Get status implementation
        
        Returns:
            Dict[str, Any]: Status information
        """
        return {}
    
    def _get_statistics_impl(self) -> Dict[str, Any]:
        """
        Get statistics implementation
        
        Returns:
            Dict[str, Any]: Statistics information
        """
        return {}
    
    def _reset_statistics_impl(self) -> None:
        """
        Reset statistics implementation
        """
