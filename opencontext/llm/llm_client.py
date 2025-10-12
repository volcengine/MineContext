# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
OpenContext module: llm_client
"""

from enum import Enum
from openai import OpenAI, APIError, AsyncOpenAI
from opencontext.utils.logging_utils import get_logger
from typing import List, Dict, Any
from opencontext.models.context import Vectorize

logger = get_logger(__name__)

class LLMProvider(Enum):
    OPENAI = "openai"
    DOUBAO = "doubao"

class LLMType(Enum):
    CHAT = "chat"
    EMBEDDING = "embedding"

class LLMClient:
    def __init__(self, llm_type: LLMType, config: Dict[str, Any]):
        self.llm_type = llm_type
        self.config = config
        self.model = config.get("model")
        self.api_key = config.get("api_key")
        self.base_url = config.get("base_url")
        self.timeout = config.get("timeout", 300)
        self.provider = config.get("provider", LLMProvider.OPENAI.value)
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

    def _openai_chat_completion(self, messages: List[Dict[str, Any]], **kwargs):
        try:
            temperature = kwargs.get("temperature", self.config.get("temperature", 0.7))
            tools = kwargs.get("tools", None)
            thinking = kwargs.get("thinking", None)
            
            create_params = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
            }
            if tools:
                create_params["tools"] = tools
                create_params['tool_choice'] = "auto"
            
            if thinking:
                if self.provider == LLMProvider.DOUBAO.value:
                    create_params["extra_body"] = {
                        "thinking": {
                            "type": thinking
                        }
                    }

            response = self.client.chat.completions.create(**create_params)
            # if hasattr(response.choices[0].message, 'reasoning_content'):
            #     reasoning_content = response.choices[0].message.reasoning_content
            #     print(f"chat reason content is {reasoning_content}")
            
            # Record token usage
            if hasattr(response, 'usage') and response.usage:
                try:
                    from opencontext.monitoring import record_token_usage
                    record_token_usage(
                        model=self.model,
                        prompt_tokens=response.usage.prompt_tokens,
                        completion_tokens=response.usage.completion_tokens,
                        total_tokens=response.usage.total_tokens
                    )
                except ImportError:
                    pass  # Monitoring module not installed or initialized
            
            return response
        except APIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise
    
    async def _openai_chat_completion_async(self, messages: List[Dict[str, Any]], **kwargs):
        """Async chat completion"""
        try:
            temperature = kwargs.get("temperature", self.config.get("temperature", 0.7))
            tools = kwargs.get("tools", None)
            thinking = kwargs.get("thinking", None)
            
            create_params = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
            }
            if tools:
                create_params["tools"] = tools
                create_params['tool_choice'] = "auto"
            
            if thinking:
                if self.provider == LLMProvider.DOUBAO.value:
                    create_params["extra_body"] = {
                        "thinking": {
                            "type": thinking
                        }
                    }

            response = await self.async_client.chat.completions.create(**create_params)
            # if hasattr(response.choices[0].message, 'reasoning_content'):
            #     reasoning_content = response.choices[0].message.reasoning_content
            #     print(f"chat reason content is {reasoning_content}")
            
            # Record token usage
            if hasattr(response, 'usage') and response.usage:
                try:
                    from opencontext.monitoring import record_token_usage
                    record_token_usage(
                        model=self.model,
                        prompt_tokens=response.usage.prompt_tokens,
                        completion_tokens=response.usage.completion_tokens,
                        total_tokens=response.usage.total_tokens
                    )
                except ImportError:
                    pass  # Monitoring module not installed or initialized
            
            return response
        except APIError as e:
            logger.exception(f"OpenAI API async error: {e}")
            raise
    
    def _openai_chat_completion_stream(self, messages: List[Dict[str, Any]], **kwargs):
        """Sync stream chat completion"""
        try:
            temperature = kwargs.get("temperature", self.config.get("temperature", 0.7))
            tools = kwargs.get("tools", None)
            thinking = kwargs.get("thinking", None)
            
            create_params = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "stream": True,
            }
            if tools:
                create_params["tools"] = tools
                create_params['tool_choice'] = "auto"
            
            if thinking:
                if self.provider == LLMProvider.DOUBAO.value:
                    create_params["extra_body"] = {
                        "thinking": {
                            "type": thinking
                        }
                    }

            stream = self.client.chat.completions.create(**create_params)
            return stream
        except APIError as e:
            logger.error(f"OpenAI API stream error: {e}")
            raise
    
    async def _openai_chat_completion_stream_async(self, messages: List[Dict[str, Any]], **kwargs):
        """Async stream chat completion - async generator"""
        try:
            temperature = kwargs.get("temperature", self.config.get("temperature", 0.7))
            tools = kwargs.get("tools", None)
            thinking = kwargs.get("thinking", None)
            
            # Create async client
            from openai import AsyncOpenAI
            async_client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=self.timeout
            )
            
            create_params = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "stream": True,
            }
            if tools:
                create_params["tools"] = tools
                create_params['tool_choice'] = "auto"
            
            if thinking:
                if self.provider == LLMProvider.DOUBAO.value:
                    create_params["extra_body"] = {
                        "thinking": {
                            "type": thinking
                        }
                    }

            stream = await async_client.chat.completions.create(**create_params)
            
            # Return stream object directly, it's already an async iterator
            async for chunk in stream:
                yield chunk
        except APIError as e:
            logger.error(f"OpenAI API async stream error: {e}")
            raise

    def _openai_embedding(self, text: str, **kwargs) -> List[float]:
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=[text]
            )
            embedding = response.data[0].embedding
            
            # Record token usage
            if hasattr(response, 'usage') and response.usage:
                try:
                    from opencontext.monitoring import record_token_usage
                    record_token_usage(
                        model=self.model,
                        prompt_tokens=response.usage.prompt_tokens,
                        completion_tokens=0,  # embedding has no completion tokens
                        total_tokens=response.usage.total_tokens
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

    def validate(self) -> tuple[bool, str]:
        """
        Validate LLM configuration by making a simple API call.

        Returns:
            tuple[bool, str]: (success, message)
        """
        try:
            if self.llm_type == LLMType.CHAT:
                # Test with a simple message
                messages = [{"role": "user", "content": "Hi"}]
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=10,
                    temperature=0.7
                )
                if response.choices and len(response.choices) > 0:
                    return True, "Chat model validation successful"
                else:
                    return False, "Chat model returned empty response"

            elif self.llm_type == LLMType.EMBEDDING:
                # Test with a simple text
                response = self.client.embeddings.create(
                    model=self.model,
                    input=["test"]
                )
                if response.data and len(response.data) > 0 and response.data[0].embedding:
                    return True, "Embedding model validation successful"
                else:
                    return False, "Embedding model returned empty response"
            else:
                return False, f"Unsupported LLM type: {self.llm_type}"

        except APIError as e:
            error_msg = str(e)
            logger.error(f"LLM validation failed with API error: {error_msg}")
            return False, f"API error: {error_msg}"
        except Exception as e:
            error_msg = str(e)
            logger.error(f"LLM validation failed with unexpected error: {error_msg}")
            return False, f"Validation error: {error_msg}"