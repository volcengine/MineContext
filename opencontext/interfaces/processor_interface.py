#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0


"""
Context processor component interface definition
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class IContextProcessor(ABC):
    """
    Context processor component interface

    Defines basic behaviors for context processor components, including initialization, configuration, processing, and information retrieval.
    """

    @abstractmethod
    def get_name(self) -> str:
        """
        Get the name of the processor component

        Returns:
            str: Name of the processor component
        """

    @abstractmethod
    def get_description(self) -> str:
        """
        Get the description of the processor component

        Returns:
            str: Description of the processor component
        """

    @abstractmethod
    def get_version(self) -> str:
        """
        Get the version of the processor component

        Returns:
            str: Version of the processor component
        """

    @abstractmethod
    def initialize(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Initialize the processor component

        Args:
            config (Optional[Dict[str, Any]]): Configuration dictionary

        Returns:
            bool: Whether initialization was successful
        """

    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate if the configuration is valid

        Args:
            config (Dict[str, Any]): Configuration dictionary

        Returns:
            bool: Whether the configuration is valid
        """

    @abstractmethod
    def can_process(self, context: Any) -> bool:
        """
        Determine if this context can be processed

        Args:
            context (Any): Context data, can be raw context or processed context

        Returns:
            bool: Whether the context can be processed
        """

    @abstractmethod
    def process(self, context: Any) -> bool:
        """
        Process context data

        Args:
            context (Any): Context data, can be raw context or processed context

        Returns:
            List[ProcessedContext]: List of processed context data
        """

    @abstractmethod
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics information

        Returns:
            Dict[str, Any]: Statistics information
        """

    @abstractmethod
    def reset_statistics(self) -> bool:
        """
        Reset statistics information

        Returns:
            bool: Whether reset was successful
        """

    @abstractmethod
    def set_callback(self, callback: callable) -> bool:
        """
        Set callback function to be called when processing is complete

        Args:
            callback (callable): Callback function that accepts a list of ProcessedContext as parameter

        Returns:
            bool: Whether setting was successful
        """

    @abstractmethod
    def shutdown(self, graceful: bool = False) -> bool:
        """
        Shutdown the processor component

        Returns:
            bool: Whether shutdown was successful
        """
