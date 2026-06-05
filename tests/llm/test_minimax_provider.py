# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for MiniMax LLM provider integration."""

import json
from unittest.mock import MagicMock, patch

import pytest

from opencontext.llm.llm_client import LLMClient, LLMProvider, LLMType


# ==================== Unit Tests ====================


class TestLLMProviderEnum:
    """Test that LLMProvider enum includes MiniMax."""

    def test_minimax_enum_exists(self):
        assert hasattr(LLMProvider, "MINIMAX")
        assert LLMProvider.MINIMAX.value == "minimax"

    def test_all_providers(self):
        providers = [p.value for p in LLMProvider]
        assert "openai" in providers
        assert "doubao" in providers
        assert "minimax" in providers


class TestMiniMaxChatClient:
    """Test MiniMax chat client initialization and behavior."""

    def _make_config(self, **overrides):
        config = {
            "api_key": "test-minimax-api-key",
            "base_url": "https://api.minimax.io/v1",
            "model": "MiniMax-M3",
            "provider": "minimax",
        }
        config.update(overrides)
        return config

    def test_init_creates_openai_client(self):
        """MiniMax uses OpenAI-compatible API, so it should create an OpenAI client."""
        client = LLMClient(llm_type=LLMType.CHAT, config=self._make_config())
        assert client.provider == "minimax"
        assert client.model == "MiniMax-M3"
        assert client.base_url == "https://api.minimax.io/v1"
        # Should use OpenAI client (not Ark)
        assert client.client is not None
        assert client.async_client is not None

    def test_init_with_m27_highspeed(self):
        """Test initialization with MiniMax-M2.7-highspeed model."""
        client = LLMClient(
            llm_type=LLMType.CHAT,
            config=self._make_config(model="MiniMax-M2.7-highspeed"),
        )
        assert client.model == "MiniMax-M2.7-highspeed"

    def test_init_missing_api_key_raises(self):
        with pytest.raises(ValueError, match="API key"):
            LLMClient(
                llm_type=LLMType.CHAT,
                config=self._make_config(api_key=""),
            )

    def test_init_missing_base_url_raises(self):
        with pytest.raises(ValueError, match="base URL"):
            LLMClient(
                llm_type=LLMType.CHAT,
                config=self._make_config(base_url=""),
            )

    @patch("opencontext.llm.llm_client.OpenAI")
    def test_chat_completion(self, mock_openai_cls):
        """Test that chat completion works via OpenAI-compat API."""
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Hello from MiniMax"
        mock_response.usage.prompt_tokens = 5
        mock_response.usage.completion_tokens = 10
        mock_response.usage.total_tokens = 15
        mock_client.chat.completions.create.return_value = mock_response

        client = LLMClient(llm_type=LLMType.CHAT, config=self._make_config())
        client.client = mock_client

        result = client.generate("Hello")
        assert result == mock_response
        mock_client.chat.completions.create.assert_called_once()
        call_kwargs = mock_client.chat.completions.create.call_args
        assert call_kwargs[1]["model"] == "MiniMax-M3"

    @patch("opencontext.llm.llm_client.OpenAI")
    def test_stream_completion(self, mock_openai_cls):
        """Test streaming chat completion."""
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client

        mock_stream = MagicMock()
        mock_client.chat.completions.create.return_value = mock_stream

        client = LLMClient(llm_type=LLMType.CHAT, config=self._make_config())
        client.client = mock_client

        result = client.generate_with_messages_stream(
            [{"role": "user", "content": "Hi"}]
        )
        assert result == mock_stream
        call_kwargs = mock_client.chat.completions.create.call_args
        assert call_kwargs[1]["stream"] is True

    @patch("opencontext.llm.llm_client.OpenAI")
    def test_thinking_not_applied_for_minimax(self, mock_openai_cls):
        """MiniMax should not use Doubao-style extra_body for thinking."""
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.usage = None
        mock_client.chat.completions.create.return_value = mock_response

        client = LLMClient(llm_type=LLMType.CHAT, config=self._make_config())
        client.client = mock_client

        client.generate_with_messages(
            [{"role": "user", "content": "test"}], thinking="enabled"
        )
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        # Should NOT have extra_body (that's Doubao-specific)
        assert "extra_body" not in call_kwargs


class TestMiniMaxEmbeddingClient:
    """Test MiniMax embedding client using native API."""

    def _make_config(self, **overrides):
        config = {
            "api_key": "test-minimax-api-key",
            "base_url": "https://api.minimax.io/v1",
            "model": "embo-01",
            "provider": "minimax",
        }
        config.update(overrides)
        return config

    def test_init_embedding_client(self):
        """MiniMax embedding should use OpenAI client (embedding handled separately)."""
        client = LLMClient(llm_type=LLMType.EMBEDDING, config=self._make_config())
        assert client.provider == "minimax"
        assert client.model == "embo-01"

    @patch("httpx.post")
    def test_minimax_embedding_request(self, mock_post):
        """Test MiniMax embedding uses native API format."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "vectors": [[0.1, 0.2, 0.3] * 512],
            "total_tokens": 5,
            "base_resp": {"status_code": 0, "status_msg": "success"},
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        client = LLMClient(llm_type=LLMType.EMBEDDING, config=self._make_config())
        embedding = client.generate_embedding("Hello world")

        assert len(embedding) == 1536
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        payload = call_args[1]["json"]
        assert payload["model"] == "embo-01"
        assert payload["texts"] == ["Hello world"]
        assert payload["type"] == "db"

    @patch("httpx.post")
    def test_minimax_embedding_error_response(self, mock_post):
        """Test error handling for MiniMax embedding API errors."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "vectors": [],
            "base_resp": {"status_code": 1001, "status_msg": "invalid api key"},
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        client = LLMClient(llm_type=LLMType.EMBEDDING, config=self._make_config())
        with pytest.raises(ValueError, match="MiniMax embedding error"):
            client.generate_embedding("test")

    @patch("httpx.post")
    def test_minimax_embedding_empty_vectors(self, mock_post):
        """Test error handling when MiniMax returns empty vectors."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "vectors": [],
            "base_resp": {"status_code": 0, "status_msg": "success"},
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        client = LLMClient(llm_type=LLMType.EMBEDDING, config=self._make_config())
        with pytest.raises(ValueError, match="empty vectors"):
            client.generate_embedding("test")

    @patch("httpx.post")
    def test_minimax_embedding_output_dim_truncation(self, mock_post):
        """Test that output_dim truncation works for MiniMax embeddings."""
        full_vector = [float(i) for i in range(1536)]
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "vectors": [full_vector],
            "total_tokens": 5,
            "base_resp": {"status_code": 0, "status_msg": "success"},
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        config = self._make_config()
        config["output_dim"] = 768
        client = LLMClient(llm_type=LLMType.EMBEDDING, config=config)
        embedding = client.generate_embedding("test")

        assert len(embedding) == 768

    @patch("httpx.post")
    def test_minimax_embedding_auth_header(self, mock_post):
        """Test that MiniMax embedding sends correct auth header."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "vectors": [[0.1] * 1536],
            "base_resp": {"status_code": 0, "status_msg": "success"},
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        client = LLMClient(llm_type=LLMType.EMBEDDING, config=self._make_config())
        client.generate_embedding("test")

        call_args = mock_post.call_args
        headers = call_args[1]["headers"]
        assert headers["Authorization"] == "Bearer test-minimax-api-key"
        assert headers["Content-Type"] == "application/json"

    @patch("httpx.post")
    def test_minimax_embedding_url_construction(self, mock_post):
        """Test URL is correctly constructed from base_url."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "vectors": [[0.1] * 1536],
            "base_resp": {"status_code": 0, "status_msg": "success"},
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        client = LLMClient(llm_type=LLMType.EMBEDDING, config=self._make_config())
        client.generate_embedding("test")

        call_args = mock_post.call_args
        url = call_args[0][0]
        assert url == "https://api.minimax.io/v1/embeddings"


class TestMiniMaxValidation:
    """Test MiniMax model validation."""

    def _make_chat_config(self):
        return {
            "api_key": "test-key",
            "base_url": "https://api.minimax.io/v1",
            "model": "MiniMax-M3",
            "provider": "minimax",
            "timeout": 15,
        }

    def _make_embedding_config(self):
        return {
            "api_key": "test-key",
            "base_url": "https://api.minimax.io/v1",
            "model": "embo-01",
            "provider": "minimax",
            "timeout": 15,
        }

    @patch("opencontext.llm.llm_client.OpenAI")
    def test_validate_chat_success(self, mock_openai_cls):
        """Test successful chat model validation."""
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_client.chat.completions.create.return_value = mock_response

        client = LLMClient(llm_type=LLMType.CHAT, config=self._make_chat_config())
        client.client = mock_client

        success, msg = client.validate()
        assert success is True
        assert "successful" in msg

    @patch("opencontext.llm.llm_client.OpenAI")
    def test_validate_chat_empty_response(self, mock_openai_cls):
        """Test chat validation with empty response."""
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = []
        mock_client.chat.completions.create.return_value = mock_response

        client = LLMClient(llm_type=LLMType.CHAT, config=self._make_chat_config())
        client.client = mock_client

        success, msg = client.validate()
        assert success is False

    @patch("httpx.post")
    def test_validate_embedding_success(self, mock_post):
        """Test successful embedding validation via MiniMax native API."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "vectors": [[0.1] * 1536],
            "base_resp": {"status_code": 0, "status_msg": "success"},
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        client = LLMClient(
            llm_type=LLMType.EMBEDDING, config=self._make_embedding_config()
        )
        success, msg = client.validate()
        assert success is True
        assert "successful" in msg

    @patch("httpx.post")
    def test_validate_embedding_failure(self, mock_post):
        """Test embedding validation failure."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "vectors": [],
            "base_resp": {"status_code": 1001, "status_msg": "invalid api key"},
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        client = LLMClient(
            llm_type=LLMType.EMBEDDING, config=self._make_embedding_config()
        )
        success, msg = client.validate()
        assert success is False


class TestMiniMaxErrorHandling:
    """Test MiniMax-specific error message extraction."""

    def _make_config(self):
        return {
            "api_key": "test-key",
            "base_url": "https://api.minimax.io/v1",
            "model": "MiniMax-M3",
            "provider": "minimax",
            "timeout": 15,
        }

    @patch("opencontext.llm.llm_client.OpenAI")
    def test_invalid_api_key_error(self, mock_openai_cls):
        """Test MiniMax invalid_api_key error extraction."""
        from openai import APIError

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = APIError(
            message="invalid_api_key: The API key is invalid",
            request=MagicMock(),
            body=None,
        )

        client = LLMClient(llm_type=LLMType.CHAT, config=self._make_config())
        client.client = mock_client

        success, msg = client.validate()
        assert success is False
        assert "Invalid MiniMax API key" in msg

    @patch("opencontext.llm.llm_client.OpenAI")
    def test_insufficient_balance_error(self, mock_openai_cls):
        """Test MiniMax insufficient_balance error extraction."""
        from openai import APIError

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = APIError(
            message="insufficient_balance: Account balance is too low",
            request=MagicMock(),
            body=None,
        )

        client = LLMClient(llm_type=LLMType.CHAT, config=self._make_config())
        client.client = mock_client

        success, msg = client.validate()
        assert success is False
        assert "Insufficient MiniMax account balance" in msg


# ==================== Integration Tests ====================


@pytest.mark.integration
class TestMiniMaxIntegration:
    """Integration tests that require a real MiniMax API key.

    Set MINIMAX_API_KEY environment variable to run these tests.
    Run with: pytest -m integration tests/llm/test_minimax_provider.py
    """

    @pytest.fixture
    def api_key(self):
        import os

        key = os.environ.get("MINIMAX_API_KEY")
        if not key:
            pytest.skip("MINIMAX_API_KEY not set")
        return key

    def test_chat_completion_real(self, api_key):
        """Test real chat completion with MiniMax API."""
        config = {
            "api_key": api_key,
            "base_url": "https://api.minimax.io/v1",
            "model": "MiniMax-M3",
            "provider": "minimax",
        }
        client = LLMClient(llm_type=LLMType.CHAT, config=config)
        response = client.generate("Say hello in one word.")
        assert response.choices
        assert len(response.choices) > 0
        content = response.choices[0].message.content
        assert content and len(content) > 0

    def test_embedding_real(self, api_key):
        """Test real embedding generation with MiniMax API."""
        config = {
            "api_key": api_key,
            "base_url": "https://api.minimax.io/v1",
            "model": "embo-01",
            "provider": "minimax",
        }
        client = LLMClient(llm_type=LLMType.EMBEDDING, config=config)
        embedding = client.generate_embedding("Hello world")
        assert isinstance(embedding, list)
        assert len(embedding) == 1536
        assert all(isinstance(v, float) for v in embedding)

    def test_validate_chat_real(self, api_key):
        """Test chat model validation with real API."""
        config = {
            "api_key": api_key,
            "base_url": "https://api.minimax.io/v1",
            "model": "MiniMax-M3",
            "provider": "minimax",
            "timeout": 30,
        }
        client = LLMClient(llm_type=LLMType.CHAT, config=config)
        success, msg = client.validate()
        assert success is True
