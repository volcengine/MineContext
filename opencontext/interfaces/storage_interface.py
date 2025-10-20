#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0


"""
Context storage interface
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from opencontext.models.context import ProcessedContext, Vectorize


class IContextStorage(ABC):
    """
    Context storage interface
    """

    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize storage backend"""

    @abstractmethod
    def get_name(self) -> str:
        """Get storage backend name"""

    @abstractmethod
    def get_description(self) -> str:
        """Get storage backend description"""

    @abstractmethod
    def upsert_processed_context(self, context: ProcessedContext) -> str:
        """Store processed context data"""

    @abstractmethod
    def batch_upsert_processed_context(self, contexts: List[ProcessedContext]) -> List[str]:
        """Batch store processed context data"""

    @abstractmethod
    def query(self, query: Vectorize, top_k: int = 5) -> List[ProcessedContext]:
        """
        Query processed context data

        Args:
            query (Vectorize): Query statement
            top_k (int, optional): Number of results to return. Defaults to 5.

        Returns:
            List[ProcessedContext]: List of query results
        """

    @abstractmethod
    def delete_processed_context(self, doc_id: str) -> bool:
        """Delete processed context data"""

    @abstractmethod
    def get_all_processed_contexts(
        self, limit: int = 100, offset: int = 0, filter: Dict[str, Any] = {}
    ) -> List[ProcessedContext]:
        """Get all processed context data"""
