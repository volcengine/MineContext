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
        Reinitialize embedding client (thread-safe)
        """
        with self._lock:
            try:
                embedding_config = get_config("embedding_model")
                if not embedding_config:
                    logger.error("No embedding config found during reinitialize")
                    raise ValueError("No embedding config found")
                logger.info("Reinitializing embedding client...")
                new_client = LLMClient(llm_type=LLMType.EMBEDDING, config=embedding_config)
                old_client = self._embedding_client
                self._embedding_client = new_client
                logger.info("Embedding client reinitialization completed")
            except Exception as e:
                logger.error(f"Failed to reinitialize embedding client: {e}")
                return False
            return True

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
    
    async def do_vectorize_async(self, vectorize: Vectorize, **kwargs):
        """
        Vectorize a Vectorize object asynchronously
        """
        if vectorize.vector:
            return
        await self._embedding_client.vectorize_async(vectorize, **kwargs)
        return


def is_initialized() -> bool:
    return GlobalEmbeddingClient.get_instance().is_initialized()


def do_embedding(text: str, **kwargs) -> List[float]:
    return GlobalEmbeddingClient.get_instance().do_embedding(text, **kwargs)


def do_vectorize(vectorize_obj: Vectorize, **kwargs):
    return GlobalEmbeddingClient.get_instance().do_vectorize(vectorize_obj, **kwargs)
  
async def do_vectorize_async(vectorize_obj: Vectorize, **kwargs):
    return await GlobalEmbeddingClient.get_instance().do_vectorize_async(vectorize_obj, **kwargs)
