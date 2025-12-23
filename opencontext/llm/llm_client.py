# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
OpenContext module: llm_client
"""

import re
from enum import Enum
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, parse_qs

from openai import APIError, AsyncOpenAI, OpenAI, AzureOpenAI, AsyncAzureOpenAI

from opencontext.models.context import Vectorize
from opencontext.utils.logging_utils import get_logger
from opencontext.monitoring import record_processing_stage

logger = get_logger(__name__)


class LLMProvider(Enum):
    OPENAI = "openai"
    DOUBAO = "doubao"
    AZURE = "azure"


class LLMType(Enum):
    CHAT = "chat"
    EMBEDDING = "embedding"


class LLMClient:
    def __init__(self, llm_type: LLMType, config: Dict[str, Any]):
        self.llm_type = llm_type
        self.config = config
        self.model = config.get("model")
        self.api_key = config.get("api_key")
        self.timeout = config.get("timeout", 300)
        self.provider = config.get("provider", LLMProvider.OPENAI.value)
        
        # Azure OpenAI specific initialization
        if self.provider == LLMProvider.AZURE.value:
            # Check if user provided base_url (which might be a complete Azure URL)
            base_url = config.get("base_url")
            azure_endpoint = config.get("azure_endpoint")
            
            # If no azure_endpoint but has base_url, try to parse it
            if not azure_endpoint and base_url:
                parsed_azure = self._parse_azure_url(base_url)
                azure_endpoint = parsed_azure['azure_endpoint']
                
                # If URL contains model and user didn't provide one, use parsed model
                if parsed_azure['model'] and not self.model:
                    self.model = parsed_azure['model']
                    logger.info(f"Extracted model from Azure URL: {self.model}")
                
                # If URL contains api_version, use it
                if parsed_azure['api_version']:
                    self.api_version = parsed_azure['api_version']
                    logger.info(f"Extracted api_version from Azure URL: {self.api_version}")
                else:
                    # No api_version in URL, check config
                    self.api_version = config.get("api_version")
            else:
                # User provided azure_endpoint (standard way)
                self.api_version = config.get("api_version")
            
            self.azure_endpoint = azure_endpoint
            
            # Validate required parameters
            if not self.api_key:
                raise ValueError(
                    "Azure OpenAI requires api_key. "
                    "Please provide your Azure OpenAI API key."
                )
            
            if not self.azure_endpoint:
                raise ValueError(
                    "Azure OpenAI requires azure_endpoint or a full URL in base_url. "
                    "Example: https://your-resource.openai.azure.com/openai/deployments/gpt-4/chat/completions?api-version=2024-02-01"
                )
            
            if not self.model:
                raise ValueError(
                    "Azure OpenAI requires model (deployment name). "
                    "Please provide it explicitly or include it in the URL."
                )
            
            # Validate api_version must exist
            if not self.api_version:
                raise ValueError(
                    "Azure OpenAI requires api_version. "
                    "Please provide a full Azure API URL with api-version parameter. "
                    "Example: https://your-resource.openai.azure.com/openai/deployments/gpt-4/chat/completions?api-version=2024-02-01"
                )
            
            self.client = AzureOpenAI(
                api_key=self.api_key,
                azure_endpoint=self.azure_endpoint,
                api_version=self.api_version,
                timeout=self.timeout
            )
            self.async_client = AsyncAzureOpenAI(
                api_key=self.api_key,
                azure_endpoint=self.azure_endpoint,
                api_version=self.api_version,
                timeout=self.timeout
            )
        else:
            # Standard OpenAI or compatible APIs (Doubao, custom, etc.)
            self.base_url = config.get("base_url")
            if not self.api_key or not self.base_url or not self.model:
                raise ValueError("API key, base URL, and model must be provided")
            
            self.client = OpenAI(
                api_key=self.api_key, 
                base_url=self.base_url, 
                timeout=self.timeout
            )
            self.async_client = AsyncOpenAI(
                api_key=self.api_key, 
                base_url=self.base_url, 
                timeout=self.timeout
            )

    @staticmethod
    def _parse_azure_url(url: str) -> Dict[str, Optional[str]]:
        """
        Parse Azure OpenAI URL and extract configuration parameters
        
        Args:
            url: Azure OpenAI URL (full URL or just endpoint)
        
        Returns:
            Dict with keys: azure_endpoint, model, api_version
        
        Examples:
            >>> _parse_azure_url("https://xxx.openai.azure.com/openai/deployments/gpt-4/chat/completions?api-version=2024-02-01")
            {
                'azure_endpoint': 'https://xxx.openai.azure.com/',
                'model': 'gpt-4',
                'api_version': '2024-02-01'
            }
        """
        if not url or not url.strip():
            return {'azure_endpoint': None, 'model': None, 'api_version': None}
        
        url = url.strip()
        parsed = urlparse(url)
        
        # Extract azure_endpoint (base domain)
        azure_endpoint = f"{parsed.scheme}://{parsed.netloc}/"
        
        # Extract deployment name (model) from path
        # Path format: /openai/deployments/{deployment-name}/...
        model = None
        if parsed.path:
            match = re.search(r'/openai/deployments/([^/]+)', parsed.path)
            if match:
                model = match.group(1)
        
        # Extract api_version from query params
        api_version = None
        if parsed.query:
            query_params = parse_qs(parsed.query)
            api_version = query_params.get('api-version', [None])[0]
        
        return {
            'azure_endpoint': azure_endpoint,
            'model': model,
            'api_version': api_version
        }

    def generate(self, prompt: str, **kwargs) -> str:
        messages = [{"role": "user", "content": prompt}]
        return self.generate_with_messages(messages, **kwargs)

    def generate_with_messages(self, messages: List[Dict[str, Any]], **kwargs):
        if self.llm_type == LLMType.CHAT:
            return self._openai_chat_completion(messages, **kwargs)
        else:
            raise ValueError(f"Unsupported LLM type for message generation: {self.llm_type}")

    async def generate_with_messages_async(self, messages: List[Dict[str, Any]], **kwargs):
        if self.llm_type == LLMType.CHAT:
            return await self._openai_chat_completion_async(messages, **kwargs)
        else:
            raise ValueError(f"Unsupported LLM type for message generation: {self.llm_type}")

    def generate_with_messages_stream(self, messages: List[Dict[str, Any]], **kwargs):
        """Stream generate response"""
        if self.llm_type == LLMType.CHAT:
            return self._openai_chat_completion_stream(messages, **kwargs)
        else:
            raise ValueError(f"Unsupported LLM type for stream generation: {self.llm_type}")

    async def generate_with_messages_stream_async(self, messages: List[Dict[str, Any]], **kwargs):
        """Async stream generate response"""
        if self.llm_type == LLMType.CHAT:
            return self._openai_chat_completion_stream_async(messages, **kwargs)
        else:
            raise ValueError(f"Unsupported LLM type for stream generation: {self.llm_type}")

    def generate_embedding(self, text: str, **kwargs) -> List[float]:
        if self.llm_type == LLMType.EMBEDDING:
            return self._openai_embedding(text, **kwargs)
        else:
            raise ValueError(f"Unsupported LLM type for embedding generation: {self.llm_type}")

    async def generate_embedding_async(self, text: str, **kwargs) -> List[float]:
        if self.llm_type == LLMType.EMBEDDING:
            return await self._openai_embedding_async(text, **kwargs)
        else:
            raise ValueError(f"Unsupported LLM type for embedding generation: {self.llm_type}")

    def _openai_chat_completion(self, messages: List[Dict[str, Any]], **kwargs):
        import time

        request_start = time.time()
        try:
            # Stage: LLM request preparation

            tools = kwargs.get("tools", None)
            thinking = kwargs.get("thinking", None)

            create_params = {
                "model": self.model,
                "messages": messages,
            }
            if tools:
                create_params["tools"] = tools
                create_params["tool_choice"] = "auto"

            if thinking:
                if self.provider == LLMProvider.DOUBAO.value:
                    create_params["extra_body"] = {"thinking": {"type": thinking}}

            # Stage: LLM API call
            api_start = time.time()
            response = self.client.chat.completions.create(**create_params)

            record_processing_stage(
                "chat_cost", int((time.time() - api_start) * 1000), status="success"
            )

            # Stage: Response parsing
            parse_start = time.time()

            # Record token usage
            if hasattr(response, "usage") and response.usage:
                try:
                    from opencontext.monitoring import record_token_usage

                    record_token_usage(
                        model=self.model,
                        prompt_tokens=response.usage.prompt_tokens,
                        completion_tokens=response.usage.completion_tokens,
                        total_tokens=response.usage.total_tokens,
                    )
                except ImportError:
                    pass  # Monitoring module not installed or initialized

            return response
        except APIError as e:
            logger.error(f"OpenAI API error: {e}")
            # Record failure
            try:
                record_processing_stage(
                    "chat_cost", int((time.time() - request_start) * 1000), status="failure"
                )
            except ImportError:
                pass
            raise

    async def _openai_chat_completion_async(self, messages: List[Dict[str, Any]], **kwargs):
        """Async chat completion"""
        import time

        request_start = time.time()
        try:
            tools = kwargs.get("tools", None)
            thinking = kwargs.get("thinking", None)

            create_params = {
                "model": self.model,
                "messages": messages,
            }
            if tools:
                create_params["tools"] = tools
                create_params["tool_choice"] = "auto"

            if thinking:
                if self.provider == LLMProvider.DOUBAO.value:
                    create_params["extra_body"] = {"thinking": {"type": thinking}}
            # Stage: LLM API call
            api_start = time.time()
            response = await self.async_client.chat.completions.create(**create_params)

            record_processing_stage(
                "chat_cost", int((time.time() - api_start) * 1000), status="success"
            )

            # Record token usage
            if hasattr(response, "usage") and response.usage:
                try:
                    from opencontext.monitoring import record_token_usage

                    record_token_usage(
                        model=self.model,
                        prompt_tokens=response.usage.prompt_tokens,
                        completion_tokens=response.usage.completion_tokens,
                        total_tokens=response.usage.total_tokens,
                    )
                except ImportError:
                    pass  # Monitoring module not installed or initialized

            return response
        except APIError as e:
            logger.exception(f"OpenAI API async error: {e}")
            # Record failure
            try:
                record_processing_stage(
                    "chat_cost", int((time.time() - request_start) * 1000), status="failure"
                )
            except ImportError:
                pass
            raise

    def _openai_chat_completion_stream(self, messages: List[Dict[str, Any]], **kwargs):
        """Sync stream chat completion"""
        try:
            tools = kwargs.get("tools", None)
            thinking = kwargs.get("thinking", None)

            create_params = {
                "model": self.model,
                "messages": messages,
                "stream": True,
            }
            if tools:
                create_params["tools"] = tools
                create_params["tool_choice"] = "auto"

            if thinking:
                if self.provider == LLMProvider.DOUBAO.value:
                    create_params["extra_body"] = {"thinking": {"type": thinking}}

            stream = self.client.chat.completions.create(**create_params)
            return stream
        except APIError as e:
            logger.error(f"OpenAI API stream error: {e}")
            raise

    async def _openai_chat_completion_stream_async(self, messages: List[Dict[str, Any]], **kwargs):
        """Async stream chat completion - async generator"""
        try:
            tools = kwargs.get("tools", None)
            thinking = kwargs.get("thinking", None)

            # Use the existing async_client that was initialized in __init__
            # This ensures proper Azure vs OpenAI client is used
            async_client = self.async_client

            create_params = {
                "model": self.model,
                "messages": messages,
                "stream": True,
            }
            if tools:
                create_params["tools"] = tools
                create_params["tool_choice"] = "auto"

            if thinking:
                if self.provider == LLMProvider.DOUBAO.value:
                    create_params["extra_body"] = {"thinking": {"type": thinking}}

            stream = await async_client.chat.completions.create(**create_params)

            # Return stream object directly, it's already an async iterator
            async for chunk in stream:
                yield chunk
        except APIError as e:
            logger.error(f"OpenAI API async stream error: {e}")
            raise

    def _openai_embedding(self, text: str, **kwargs) -> List[float]:
        try:
            response = self.client.embeddings.create(model=self.model, input=[text])
            embedding = response.data[0].embedding

            # Record token usage
            if hasattr(response, "usage") and response.usage:
                try:
                    from opencontext.monitoring import record_token_usage

                    record_token_usage(
                        model=self.model,
                        prompt_tokens=response.usage.prompt_tokens,
                        completion_tokens=0,  # embedding has no completion tokens
                        total_tokens=response.usage.total_tokens,
                    )
                except ImportError:
                    pass  # Monitoring module not installed or initialized

            output_dim = kwargs.get("output_dim", self.config.get("output_dim", 0))
            if output_dim and len(embedding) > output_dim:
                import math

                embedding = embedding[:output_dim]
                norm = math.sqrt(sum(x**2 for x in embedding))
                if norm > 0:
                    embedding = [x / norm for x in embedding]

            return embedding
        except APIError as e:
            logger.error(f"OpenAI API error during embedding: {e}")
            raise
          
    async def _openai_embedding_async(self, text: str, **kwargs) -> List[float]:
        try:
            response = await self.async_client.embeddings.create(model=self.model, input=[text])
            embedding = response.data[0].embedding

            # Record token usage
            if hasattr(response, "usage") and response.usage:
                try:
                    from opencontext.monitoring import record_token_usage

                    record_token_usage(
                        model=self.model,
                        prompt_tokens=response.usage.prompt_tokens,
                        completion_tokens=0,  # embedding has no completion tokens
                        total_tokens=response.usage.total_tokens,
                    )
                except ImportError:
                    pass  # Monitoring module not installed or initialized

            output_dim = kwargs.get("output_dim", self.config.get("output_dim", 0))
            if output_dim and len(embedding) > output_dim:
                import math

                embedding = embedding[:output_dim]
                norm = math.sqrt(sum(x**2 for x in embedding))
                if norm > 0:
                    embedding = [x / norm for x in embedding]

            return embedding
        except APIError as e:
            logger.error(f"OpenAI API error during embedding: {e}")
            raise



    def vectorize(self, vectorize: Vectorize, **kwargs):
        if vectorize.vector:
            return
        vectorize.vector = self.generate_embedding(vectorize.get_vectorize_content(), **kwargs)
        return
      
    async def vectorize_async(self, vectorize: Vectorize, **kwargs):
        if vectorize.vector:
            return
        vectorize.vector = await self.generate_embedding_async(vectorize.get_vectorize_content(), **kwargs)
        return
      

    def validate(self) -> tuple[bool, str]:
        """
        Validate LLM configuration by making a simple API call.

        Returns:
            tuple[bool, str]: (success, message)
        """

        def _extract_error_summary(error: Any) -> str:
            """
            Extract a concise error summary from API error messages.
            Removes verbose API error details and keeps only the essential information.
            """
            error_msg = str(error)
            if not error_msg:
                return "Unknown error"

            # 1. Check for specific Volcengine/Doubao error codes
            volcengine_errors = {
                "AccessDenied": "Access denied. Please ensure the model is enabled in the Volcengine console.",
                "QuotaExceeded": "Quota exceeded. Please check your Volcengine account balance.",
                "ModelAccountIpmRateLimitExceeded": "Model rate limit (IPM) exceeded.",
                "AccountRateLimitExceeded": "Account rate limit exceeded.",
                "RateLimitExceeded": "Rate limit exceeded.",
                "InternalServiceError": "Volcengine internal service error.",
                "ServiceUnavailable": "Service unavailable.",
                "MethodNotAllowed": "Method not allowed. Check your configuration.",
            }
            
            for code, msg in volcengine_errors.items():
                if code in error_msg:
                    return msg

            # 2. Check for OpenAI specific errors
            openai_errors = {
                "insufficient_quota": "Insufficient quota. Check your plan and billing details.",
                "invalid_api_key": "Invalid API key provided.",
                "model_not_found": "The model does not exist or you do not have access to it.",
                "context_length_exceeded": "Context length exceeded.",
            }

            for code, msg in openai_errors.items():
                if code in error_msg:
                    return msg

            # If it's an API error with detailed JSON response, extract key info
            if "Error code:" in error_msg:
                parts = error_msg.split("Error code:", 1)
                if len(parts) > 1:
                    code_part = parts[1].strip()
                    # Get just the code number and basic message
                    if "-" in code_part:
                        code = code_part.split("-", 1)[0].strip()
                        # Try to extract the error type/message from the dict
                        if "'message':" in code_part:
                            try:
                                msg_start = code_part.find("'message':") + len("'message':")
                                msg_part = code_part[msg_start:].strip()
                                if msg_part.startswith("'") or msg_part.startswith('"'):
                                    quote_char = msg_part[0]
                                    msg_end = msg_part.find(quote_char, 1)
                                    if msg_end > 0:
                                        actual_msg = msg_part[1:msg_end]
                                        # Remove Request id and everything after it
                                        if ". Request id:" in actual_msg:
                                            actual_msg = actual_msg.split(". Request id:")[0]
                                        return actual_msg
                            except:
                                pass
                        return f"Error {code}"

            # If the message is already concise (< 150 chars), return as-is
            if len(error_msg) < 150:
                return error_msg

            # Otherwise, truncate with ellipsis
            return error_msg[:147] + "..."

        try:
            if self.llm_type == LLMType.CHAT:
                # Test with an image input - 20x20 pixel PNG with clear red square pattern
                # This is a small but visible test image to validate vision capabilities
                # tiny_image_base64 = "iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAAMElEQVR42mP8z8DwHwMxgImBQjDwBo4aNWrUqFGjRlEEhtEwHDVq1KhRo0aNGgUAAN0/Af9dX6MgAAAAAElFTkSuQmCC"
                # messages = [
                #     {
                #         "role": "user",
                #         "content": [
                #             {"type": "text", "text": "Hi"},
                #             {
                #                 "type": "image_url",
                #                 "image_url": {"url": f"data:image/png;base64,{tiny_image_base64}"},
                #             },
                #         ],
                #     }
                # ]
                messages = [{"role": "user", "content": "Hi"}]
                response = self.client.chat.completions.create(model=self.model, messages=messages)
                if response.choices and len(response.choices) > 0:
                    return True, "Chat model validation successful"
                else:
                    return False, "Chat model returned empty response"

            elif self.llm_type == LLMType.EMBEDDING:
                # Test with a simple text
                response = self.client.embeddings.create(model=self.model, input=["test"])
                if response.data and len(response.data) > 0 and response.data[0].embedding:
                    return True, "Embedding model validation successful"
                else:
                    return False, "Embedding model returned empty response"
            else:
                return False, f"Unsupported LLM type: {self.llm_type}"

        except APIError as e:
            logger.error(f"LLM validation failed with API error: {e}")
            # Extract concise error summary before returning
            concise_error = _extract_error_summary(e)
            return False, concise_error
        except Exception as e:
            logger.error(f"LLM validation failed with unexpected error: {e}")
            # Extract concise error summary before returning
            concise_error = _extract_error_summary(e)
            return False, concise_error
