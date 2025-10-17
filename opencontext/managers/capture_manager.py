#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Context capture management.
Manages and coordinates context capture components with loose coupling.
"""

import time
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Set

from opencontext.interfaces import ICaptureComponent
from opencontext.models.context import RawContextProperties
from opencontext.utils.logging_utils import get_logger

logger = get_logger(__name__)


class ContextCaptureManager:
    """
    Context Capture Manager

    Manages and coordinates multiple context capture components, providing a unified interface for context capture.
    """

    def __init__(self):
        """Initializes the context capture manager."""
        # Dictionary of registered capture components, with component name as key and component instance as value
        self._components: Dict[str, ICaptureComponent] = {}
        self._component_configs: Dict[str, Dict[str, Any]] = {}

        # Set of running components
        self._running_components: Set[str] = set()

        # Callback function, called when new data is captured
        self._callback: Optional[callable] = None

        # Statistics
        self._statistics: Dict[str, Any] = {
            "total_captures": 0,
            "total_contexts_captured": 0,
            "components": {},
            "last_capture_time": None,
            "errors": 0,
        }

    def register_component(self, name: str, component: ICaptureComponent) -> bool:
        """
        Register a capture component.

        Args:
            name (str): Component name
            component (ICaptureComponent): Capture component instance

        Returns:
            bool: Whether registration was successful
        """
        if name in self._components:
            logger.warning(f"Component '{name}' is already registered and will be overwritten")

        self._components[name] = component
        self._statistics["components"][name] = {
            "captures": 0,
            "contexts_captured": 0,
            "errors": 0,
            "last_capture_time": None,
        }

        logger.info(f"Component '{name}' registered successfully")
        return True

    def unregister_component(self, component_name: str) -> bool:
        """
        Unregister a capture component.

        Args:
            component_name (str): Component name

        Returns:
            bool: Whether unregistration was successful
        """
        if component_name not in self._components:
            logger.warning(f"Component '{component_name}' is not registered, cannot unregister")
            return False

        if component_name in self._running_components:
            self.stop_component(component_name)

        del self._components[component_name]
        if component_name in self._statistics["components"]:
            del self._statistics["components"][component_name]

        logger.info(f"Component '{component_name}' unregistered successfully")
        return True

    def initialize_component(self, component_name: str, config: Dict[str, Any]) -> bool:
        """
        Initialize a capture component.

        Args:
            component_name (str): Component name
            config (Dict[str, Any]): Component configuration

        Returns:
            bool: Whether initialization was successful
        """
        if component_name not in self._components:
            logger.error(f"Component '{component_name}' is not registered, cannot initialize")
            return False

        component = self._components[component_name]
        self._component_configs[component_name] = config

        try:
            if not component.validate_config(config):
                logger.error(f"Component '{component_name}' configuration is invalid")
                return False

            success = component.initialize(config)
            if success:
                logger.info(f"Component '{component_name}' initialized successfully")
            else:
                logger.error(f"Component '{component_name}' initialization failed")

            return success
        except Exception as e:
            logger.exception(f"Component '{component_name}' initialization exception: {str(e)}")
            self._statistics["errors"] += 1
            return False

    def start_component(self, component_name: str) -> bool:
        """
        Start a capture component.

        Args:
            component_name (str): Component name

        Returns:
            bool: Whether startup was successful
        """
        if component_name not in self._components:
            logger.error(f"Component '{component_name}' is not registered, cannot start")
            return False

        if component_name in self._running_components:
            logger.warning(f"Component '{component_name}' is already running")
            return True

        component = self._components[component_name]

        try:
            # Set the callback function, the component will report data through this callback
            component.set_callback(self._on_component_capture)

            # Start the component (the component will manage its own capture thread internally)
            success = component.start()
            if success:
                self._running_components.add(component_name)
                logger.info(f"Component '{component_name}' started successfully")
            else:
                logger.error(f"Component '{component_name}' failed to start")

            return success
        except Exception as e:
            logger.exception(f"Component '{component_name}' startup exception: {str(e)}")
            self._statistics["errors"] += 1
            return False

    def stop_component(self, component_name: str, graceful: bool = True) -> bool:
        """
        Stop a capture component.

        Args:
            component_name (str): Component name
            graceful (bool): Whether to stop gracefully, waiting for current captures to complete.

        Returns:
            bool: Whether stopping was successful
        """
        if component_name not in self._components:
            logger.error(f"Component '{component_name}' is not registered, cannot stop")
            return False

        if component_name not in self._running_components:
            logger.warning(f"Component '{component_name}' is not running")
            return True

        component = self._components[component_name]

        try:
            success = component.stop(graceful=graceful)
            if success:
                self._running_components.remove(component_name)
                logger.info(f"Component '{component_name}' stopped successfully")
            else:
                logger.error(f"Component '{component_name}' failed to stop")

            return success
        except Exception as e:
            logger.exception(f"Component '{component_name}' stop exception: {str(e)}")
            self._statistics["errors"] += 1
            return False

    def start_all_components(self) -> Dict[str, bool]:
        """
        Start all capture components.

        Returns:
            Dict[str, bool]: A mapping from component name to startup result.
        """
        results = {}
        for component_name in self._components:
            results[component_name] = self.start_component(component_name)

        return results

    def stop_all_components(self, graceful: bool = True) -> Dict[str, bool]:
        """
        Stop all capture components.

        Returns:
            Dict[str, bool]: A mapping from component name to stop result.
        """
        results = {}
        for component_name in list(self._running_components):
            results[component_name] = self.stop_component(component_name, graceful=graceful)

        return results

    def get_component(self, component_name: str) -> Optional[ICaptureComponent]:
        """
        Get a capture component.

        Args:
            component_name (str): Component name

        Returns:
            Optional[ICaptureComponent]: The component instance, or None if it does not exist.
        """
        return self._components.get(component_name)

    def get_all_components(self) -> Dict[str, ICaptureComponent]:
        """
        Get all capture components.

        Returns:
            Dict[str, ICaptureComponent]: A mapping from component name to component instance.
        """
        return self._components.copy()

    def get_running_components(self) -> Dict[str, ICaptureComponent]:
        """
        Get all running capture components.

        Returns:
            Dict[str, ICaptureComponent]: A mapping from component name to component instance.
        """
        return {name: self._components[name] for name in self._running_components}

    def set_callback(self, callback: callable) -> None:
        """
        Set the callback function, which is called when new data is captured.

        Args:
            callback (callable): The callback function, which accepts a list of RawContextProperties as a parameter.
        """
        self._callback = callback

    def _on_component_capture(self, contexts: List[RawContextProperties]) -> None:
        """
        Component capture callback function.

        This function is called when any component captures data.
        It is responsible for updating statistics and passing the data to the upper-level callback.

        Args:
            contexts (List[RawContextProperties]): List of captured context data.
        """
        if not contexts:
            return

        num_contexts = len(contexts)
        # Assuming the source is homogeneous in a single capture batch
        component_name = contexts[0].source.name

        # Update statistics
        self._statistics["total_captures"] += 1
        self._statistics["total_contexts_captured"] += num_contexts
        self._statistics["last_capture_time"] = time.time()

        comp_stats = self._statistics["components"].get(component_name)
        if comp_stats:
            comp_stats["captures"] += 1
            comp_stats["contexts_captured"] += num_contexts
            comp_stats["last_capture_time"] = time.time()

        # logger.debug(f"Received {num_contexts} context data from component '{component_name}'")

        # Call the upper-level callback (e.g., pass to OpenContext for processing)
        if self._callback:
            try:
                self._callback(contexts)
            except Exception as e:
                logger.exception(
                    f"An exception occurred when executing the upper-level callback function: {e}"
                )

    def capture(self, component_name: str) -> List[RawContextProperties]:
        """
        Manually trigger a capture from a specified component.
        Note: This method is mainly used for manual or one-time captures. Regular automatic captures are handled by the component's internal thread.

        Args:
            component_name (str): Component name

        Returns:
            List[RawContextProperties]: List of captured context data.
        """
        if component_name not in self._components:
            logger.error(f"Component '{component_name}' is not registered, cannot capture")
            return []

        component = self._components[component_name]

        try:
            # Manually call the component's capture method
            # Data will be reported through the component's internal set_callback mechanism
            return component.capture()
        except Exception as e:
            logger.exception(f"Component '{component_name}' manual capture exception: {str(e)}")
            self._statistics["errors"] += 1
            if component_name in self._statistics["components"]:
                self._statistics["components"][component_name]["errors"] += 1
            return []

    def capture_all(self) -> Dict[str, List[RawContextProperties]]:
        """
        Manually trigger a capture from all running components.

        Returns:
            Dict[str, List[RawContextProperties]]: A mapping from component name to the list of captured context data.
        """
        results = {}
        # Create a copy of the running components to iterate over safely
        running_components_copy = list(self._running_components)

        for component_name in running_components_copy:
            contexts = self.capture(component_name)
            results[component_name] = contexts

        return results

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics.

        Returns:
            Dict[str, Any]: Statistics information.
        """
        return self._statistics.copy()

    def shutdown(self, graceful: bool = True) -> None:
        """
        Shutdown the manager, stopping all components and threads.

        Args:
            graceful (bool): Whether to shut down gracefully, waiting for current captures to complete.
        """
        logger.info("Shutting down Context Capture Manager...")
        self.stop_all_components(graceful=graceful)
        logger.info("Context Capture Manager has been shut down.")

    def reset_statistics(self) -> None:
        """Reset statistics."""
        for component_name in self._statistics["components"]:
            self._statistics["components"][component_name] = {
                "captures": 0,
                "contexts_captured": 0,
                "errors": 0,
                "last_capture_time": None,
            }

        self._statistics["total_captures"] = 0
        self._statistics["total_contexts_captured"] = 0
        self._statistics["last_capture_time"] = None
        self._statistics["errors"] = 0
