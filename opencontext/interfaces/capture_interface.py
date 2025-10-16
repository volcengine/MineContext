#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0


"""
Context capture component interface definition
"""

import abc
from typing import Any, Dict, List

from opencontext.models.context import RawContextProperties


class ICaptureComponent(abc.ABC):
    """
    Context capture component interface

    Defines common behaviors for context capture components. All capture components should implement this interface.
    """

    @abc.abstractmethod
    def initialize(self, config: Dict[str, Any]) -> bool:
        """
        Initialize the capture component

        Args:
            config (Dict[str, Any]): Component configuration

        Returns:
            bool: Whether initialization was successful
        """

    @abc.abstractmethod
    def start(self) -> bool:
        """
        Start the capture component

        Returns:
            bool: Whether startup was successful
        """

    @abc.abstractmethod
    def stop(self, graceful: bool = True) -> bool:
        """
        Stop the capture component

        Args:
            graceful (bool): Whether to stop gracefully, waiting for current captures to complete

        Returns:
            bool: Whether shutdown was successful
        """

    @abc.abstractmethod
    def is_running(self) -> bool:
        """
        Check if the capture component is running

        Returns:
            bool: Whether the component is running
        """

    @abc.abstractmethod
    def capture(self) -> List[RawContextProperties]:
        """
        Execute a single capture operation

        Returns:
            List[RawContextProperties]: List of captured context data
        """

    @abc.abstractmethod
    def get_name(self) -> str:
        """
        Get the capture component name

        Returns:
            str: Component name
        """

    @abc.abstractmethod
    def get_description(self) -> str:
        """
        Get the capture component description

        Returns:
            str: Component description
        """

    @abc.abstractmethod
    def get_config_schema(self) -> Dict[str, Any]:
        """
        Get the configuration schema

        Returns:
            Dict[str, Any]: Configuration schema describing types and constraints of config items
        """

    @abc.abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate if the configuration is valid

        Args:
            config (Dict[str, Any]): Configuration to validate

        Returns:
            bool: Whether the configuration is valid
        """

    @abc.abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """
        Get component status

        Returns:
            Dict[str, Any]: Component status information
        """

    @abc.abstractmethod
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics information

        Returns:
            Dict[str, Any]: Statistics information
        """

    @abc.abstractmethod
    def reset_statistics(self) -> bool:
        """
        Reset statistics information

        Returns:
            bool: Whether reset was successful
        """

    @abc.abstractmethod
    def set_callback(self, callback: callable) -> bool:
        """
        Set callback function to be called when new data is captured

        Args:
            callback (callable): Callback function that accepts a list of RawContextProperties as parameter

        Returns:
            bool: Whether setting was successful
        """
