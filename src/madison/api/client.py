"""OpenRouter API client."""

import json
import logging
from typing import AsyncIterator, List, Optional

import httpx

from madison.api.models import ChatCompletionRequest, ChatCompletionResponse, Message
from madison.exceptions import APIError

logger = logging.getLogger(__name__)

OPENROUTER_API_URL = "https://openrouter.ai/api/v1"


class OpenRouterClient:
    """Client for interacting with OpenRouter API."""

    def __init__(
        self,
        api_key: str,
        timeout: int = 30,
        base_url: str = OPENROUTER_API_URL,
    ):
        """Initialize OpenRouter client.

        Args:
            api_key: OpenRouter API key
            timeout: Request timeout in seconds
            base_url: Base URL for the API
        """
        self.api_key = api_key
        self.timeout = timeout
        self.base_url = base_url
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "OpenRouterClient":
        """Async context manager entry."""
        self._client = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _get_headers(self) -> dict:
        """Get request headers."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/anthropics/madison",
            "X-Title": "Madison CLI",
        }

    async def _ensure_client(self) -> httpx.AsyncClient:
        """Ensure async client is initialized."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def chat(
        self,
        messages: List[Message],
        model: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
    ) -> ChatCompletionResponse:
        """Send a chat completion request.

        Args:
            messages: List of messages
            model: Model name
            temperature: Temperature for sampling
            max_tokens: Maximum tokens in response
            stream: Whether to stream response

        Returns:
            ChatCompletionResponse: The API response

        Raises:
            APIError: If the API request fails
        """
        request = ChatCompletionRequest(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream,
        )

        try:
            client = await self._ensure_client()
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self._get_headers(),
                json=request.to_openrouter_dict(),
            )
            response.raise_for_status()
            return ChatCompletionResponse(**response.json())
        except httpx.HTTPStatusError as e:
            error_msg = f"OpenRouter API error: {e.status_code}"
            try:
                response_text = e.response.text
                logger.error(f"Response body: {response_text}")
                error_data = json.loads(response_text)
                if "error" in error_data:
                    error_details = error_data['error']
                    if isinstance(error_details, dict):
                        error_msg += f" - {error_details.get('message', 'Unknown error')}"
                    else:
                        error_msg += f" - {error_details}"
            except Exception as ex:
                logger.debug(f"Failed to parse error response: {ex}")
            logger.error(error_msg)
            raise APIError(error_msg) from e
        except Exception as e:
            logger.error(f"API request failed: {e}")
            raise APIError(f"API request failed: {e}") from e

    async def chat_stream(
        self,
        messages: List[Message],
        model: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[str]:
        """Stream a chat completion response.

        Args:
            messages: List of messages
            model: Model name
            temperature: Temperature for sampling
            max_tokens: Maximum tokens in response

        Yields:
            str: Streamed response tokens

        Raises:
            APIError: If the API request fails
        """
        request = ChatCompletionRequest(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )

        try:
            client = await self._ensure_client()
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=self._get_headers(),
                json=request.to_openrouter_dict(),
            ) as response:
                if response.status_code != 200:
                    error_msg = f"OpenRouter API error: {response.status_code}"
                    try:
                        response_text = await response.aread()
                        logger.error(f"Response body: {response_text}")
                        try:
                            error_data = json.loads(response_text)
                            if "error" in error_data:
                                error_details = error_data['error']
                                if isinstance(error_details, dict):
                                    error_msg += f" - {error_details.get('message', 'Unknown error')}"
                                else:
                                    error_msg += f" - {error_details}"
                        except json.JSONDecodeError:
                            error_msg += f" - {response_text.decode('utf-8', errors='ignore')}"
                    except Exception as e:
                        logger.error(f"Failed to read error response: {e}")
                    logger.error(error_msg)
                    raise APIError(error_msg)

                async for line in response.aiter_lines():
                    if not line.strip() or line.startswith(":"):
                        continue

                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break

                        try:
                            chunk = json.loads(data)
                            if "choices" in chunk and chunk["choices"]:
                                choice = chunk["choices"][0]
                                if "delta" in choice and "content" in choice["delta"]:
                                    yield choice["delta"]["content"]
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to decode streaming chunk: {data}")
                            continue

        except APIError:
            raise
        except Exception as e:
            logger.error(f"Streaming request failed: {e}")
            raise APIError(f"Streaming request failed: {e}") from e

    async def list_models(self) -> List[dict]:
        """List available models.

        Returns:
            List[dict]: List of available models

        Raises:
            APIError: If the API request fails
        """
        try:
            client = await self._ensure_client()
            response = await client.get(
                f"{self.base_url}/models",
                headers=self._get_headers(),
            )
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            raise APIError(f"Failed to list models: {e}") from e
