#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Global embedding client singleton wrapper
Provides global access to embedding client instances
"""

import threading
from typing import Dict, List, Optional

from opencontext.config.global_config import get_config
from opencontext.llm.llm_client import LLMClient, LLMType
from opencontext.models.context import Vectorize
from opencontext.utils.logging_utils import get_logger

logger = get_logger(__name__)


class GlobalEmbeddingClient:
    """
    Global embedding client (singleton pattern)
    """

    _instance = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls):
        """Ensure singleton pattern"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize global embedding client"""
        if not self._initialized:
            with self._lock:
                if not self._initialized:
                    self._embedding_client: Optional[LLMClient] = None
                    self._auto_initialized = False
                    GlobalEmbeddingClient._initialized = True

    @classmethod
    def get_instance(cls) -> "GlobalEmbeddingClient":
        """
        Get global embedding client instance
        """
        instance = cls()
        # If not initialized yet, try auto-initialization
        if not instance._auto_initialized and instance._embedding_client is None:
            instance._auto_initialize()
        return instance

    def _auto_initialize(self):
        """Auto-initialize embedding client"""
        if self._auto_initialized:
            return
        try:
            embedding_config = get_config("embedding_model")
            if not embedding_config:
                logger.warning("No embedding config found in embedding_model")
                self._auto_initialized = True
                return

            self._embedding_client = LLMClient(llm_type=LLMType.EMBEDDING, config=embedding_config)
            logger.info("GlobalEmbeddingClient auto-initialized successfully")
            self._auto_initialized = True
        except Exception as e:
            logger.error(f"GlobalEmbeddingClient auto-initialization failed: {e}")
            self._auto_initialized = True

    def is_initialized(self) -> bool:
        return self._embedding_client is not None

    def reinitialize(self, new_config: Optional[Dict] = None):
        """
        Thread-safe reinitialization of embedding client.
        This method ensures that if reinitialization fails, the old client is restored.

        Args:
            new_config: Optional new configuration dict (if None, loads from global config)

        Returns:
            bool: True if reinitialization succeeded, False otherwise
        """
        with self._lock:
            old_client = self._embedding_client
            try:
                embedding_config = new_config or get_config("embedding_model")
                if not embedding_config:
                    logger.error("No embedding_config found during reinitialization.")
                    raise ValueError("No embedding_config found during reinitialization")

                logger.info("Reinitializing embedding client...")
                new_client = LLMClient(llm_type=LLMType.EMBEDDING, config=embedding_config)

                # Validate the new client before replacing the old one
                is_valid, msg = new_client.validate()
                if not is_valid:
                    raise ValueError(f"New embedding client validation failed: {msg}")

                self._embedding_client = new_client
                logger.info("Embedding client reinitialized successfully.")
                return True
            except Exception as e:
                logger.error(
                    f"Failed to reinitialize embedding client: {e}. Restoring previous client."
                )
                self._embedding_client = old_client
                return False

    def do_embedding(self, text: str, **kwargs) -> List[float]:
        """
        Get text embeddings
        """
        return self._embedding_client.generate_embedding(text, **kwargs)

    def do_vectorize(self, vectorize: Vectorize, **kwargs):
        """
        Vectorize a Vectorize object
        """
        if vectorize.vector:
            return
        self._embedding_client.vectorize(vectorize, **kwargs)
        return


def is_initialized() -> bool:
    return GlobalEmbeddingClient.get_instance().is_initialized()


def do_embedding(text: str, **kwargs) -> List[float]:
    return GlobalEmbeddingClient.get_instance().do_embedding(text, **kwargs)


def do_vectorize(vectorize_obj: Vectorize, **kwargs):
    return GlobalEmbeddingClient.get_instance().do_vectorize(vectorize_obj, **kwargs)
