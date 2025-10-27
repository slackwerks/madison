"""OpenRouter API client."""

import asyncio
import json
import logging
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Tuple

import httpx

from madison.api.models import ChatCompletionRequest, ChatCompletionResponse, Message, ToolCall
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
        max_retries: int = 3,
        retry_initial_delay: float = 1.0,
        retry_backoff_factor: float = 2.0,
    ):
        """Initialize OpenRouter client.

        Args:
            api_key: OpenRouter API key
            timeout: Request timeout in seconds
            base_url: Base URL for the API
            max_retries: Maximum number of retries for failed requests
            retry_initial_delay: Initial delay in seconds before first retry
            retry_backoff_factor: Multiply delay by this factor after each retry
        """
        self.api_key = api_key
        self.timeout = timeout
        self.base_url = base_url
        self.max_retries = max_retries
        self.retry_initial_delay = retry_initial_delay
        self.retry_backoff_factor = retry_backoff_factor
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

    def _is_retryable_error(self, status_code: int) -> bool:
        """Check if an error is retryable.

        Args:
            status_code: HTTP status code

        Returns:
            bool: True if the error should be retried
        """
        # Retryable errors: rate limit, service unavailable, gateway timeout
        return status_code in (429, 503, 504)

    def _extract_error_details(self, response_text: bytes, status_code: int) -> tuple[str, Optional[str]]:
        """Extract error message and provider info from API response.

        Args:
            response_text: Response body
            status_code: HTTP status code

        Returns:
            tuple: (error_message, provider_info)
        """
        error_msg = f"OpenRouter API error: {status_code}"
        provider_info = None

        try:
            error_data = json.loads(response_text)
            if "error" in error_data:
                error_details = error_data['error']
                if isinstance(error_details, dict):
                    msg = error_details.get('message', 'Unknown error')
                    error_msg += f" - {msg}"
                    # Try to extract provider-specific info
                    metadata = error_details.get('metadata', {})
                    if isinstance(metadata, dict):
                        raw = metadata.get('raw', '')
                        provider_name = metadata.get('provider_name', '')
                        if provider_name:
                            provider_info = f"{provider_name}: {raw}" if raw else provider_name
                else:
                    error_msg += f" - {error_details}"
        except json.JSONDecodeError:
            error_msg += f" - {response_text.decode('utf-8', errors='ignore')}"

        return error_msg, provider_info

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

    async def _do_chat_stream(
        self,
        messages: List[Message],
        model: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[str]:
        """Internal method to perform streaming chat completion (no retries).

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
                    response_text = await response.aread()
                    logger.error(f"Response body: {response_text}")
                    error_msg, provider_info = self._extract_error_details(response_text, response.status_code)
                    logger.error(error_msg)
                    if provider_info:
                        logger.error(f"Provider info: {provider_info}")
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

    async def chat_stream(
        self,
        messages: List[Message],
        model: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[str]:
        """Stream a chat completion response with automatic retries.

        Automatically retries on transient errors (429, 503, 504) with
        exponential backoff.

        Args:
            messages: List of messages
            model: Model name
            temperature: Temperature for sampling
            max_tokens: Maximum tokens in response

        Yields:
            str: Streamed response tokens

        Raises:
            APIError: If the API request fails after all retries
        """
        last_error = None
        delay = self.retry_initial_delay

        for attempt in range(self.max_retries + 1):
            try:
                async for token in self._do_chat_stream(messages, model, temperature, max_tokens):
                    yield token
                return  # Success!

            except APIError as e:
                last_error = e
                error_msg = str(e)

                # Extract status code from error message
                status_code = None
                if "error:" in error_msg:
                    try:
                        status_code = int(error_msg.split("error:")[1].split()[0])
                    except (ValueError, IndexError):
                        pass

                # Check if retryable and if we have more attempts
                if status_code and self._is_retryable_error(status_code) and attempt < self.max_retries:
                    logger.warning(f"Retryable error on attempt {attempt + 1}/{self.max_retries + 1}: {error_msg}")
                    logger.info(f"Retrying in {delay:.1f} seconds...")
                    await asyncio.sleep(delay)
                    delay *= self.retry_backoff_factor
                else:
                    # Non-retryable error or out of retries
                    raise

        # Should not reach here, but just in case
        if last_error:
            raise last_error
        raise APIError("Unknown error in chat_stream")

    async def call_with_tools(
        self,
        messages: List[Message],
        model: str,
        tools: List[Dict[str, Any]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Tuple[str, Optional[List[ToolCall]]]:
        """Call model with tools support (non-streaming).

        Args:
            messages: List of messages
            model: Model name
            tools: List of tool definitions
            temperature: Temperature for sampling
            max_tokens: Maximum tokens in response

        Returns:
            Tuple of (response_text, tool_calls)
            - response_text: Assistant's text response (may be empty if tool called)
            - tool_calls: List of ToolCall objects if tools were called, None otherwise

        Raises:
            APIError: If the API request fails
        """
        request = ChatCompletionRequest(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools,
            stream=False,  # Non-streaming for tool calls
        )

        try:
            client = await self._ensure_client()
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self._get_headers(),
                json=request.to_openrouter_dict(),
            )

            if response.status_code != 200:
                error_msg, provider_info = self._extract_error_details(
                    response.text, response.status_code
                )
                logger.error(error_msg)
                if provider_info:
                    logger.error(f"Provider info: {provider_info}")
                raise APIError(error_msg)

            data = response.json()
            if "choices" not in data or not data["choices"]:
                raise APIError("No choices in response")

            choice = data["choices"][0]
            message = choice.get("message", {})
            finish_reason = choice.get("finish_reason")

            # Extract text response
            response_text = message.get("content", "")

            # Extract tool calls if present
            tool_calls = None
            if finish_reason == "tool_calls" and "tool_calls" in message:
                tool_calls = self._parse_tool_calls(message["tool_calls"])

            return response_text, tool_calls

        except APIError:
            raise
        except Exception as e:
            logger.error(f"Tool calling request failed: {e}")
            raise APIError(f"Tool calling request failed: {e}") from e

    def _parse_tool_calls(self, tool_calls_data: List[Dict[str, Any]]) -> List[ToolCall]:
        """Parse tool call data from API response.

        Args:
            tool_calls_data: Raw tool call data from API

        Returns:
            List of ToolCall objects
        """
        tool_calls = []
        for call_data in tool_calls_data:
            try:
                tool_call = ToolCall(**call_data)
                tool_calls.append(tool_call)
            except Exception as e:
                logger.warning(f"Failed to parse tool call: {e}")
                continue
        return tool_calls

    async def call_with_tool_loop(
        self,
        initial_message: str,
        model: str,
        tools: List[Dict[str, Any]],
        tool_executor: Callable[[str, Dict[str, Any]], Any],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        max_iterations: int = 10,
    ) -> str:
        """Execute a multi-turn tool calling conversation.

        This implements the standard tool calling loop:
        1. Send user message with available tools
        2. Get response with potential tool calls
        3. Execute tools locally
        4. Send tool results back to model
        5. Repeat until model returns final response

        Args:
            initial_message: Initial user message/intent
            model: Model name
            tools: List of tool definitions
            tool_executor: Function(tool_name, arguments) -> result
            temperature: Temperature for sampling
            max_tokens: Maximum tokens per response
            max_iterations: Maximum conversation turns (safety limit)

        Returns:
            Final response text from model

        Raises:
            APIError: If API calls fail
        """
        messages: List[Message] = [
            Message(role="user", content=initial_message)
        ]

        for iteration in range(max_iterations):
            logger.debug(f"Tool calling iteration {iteration + 1}/{max_iterations}")

            # Get response with potential tool calls
            response_text, tool_calls = await self.call_with_tools(
                messages=messages,
                model=model,
                tools=tools,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            # Add assistant's response to conversation
            assistant_message = Message(
                role="assistant",
                content=response_text if response_text else None,
                tool_calls=[tc.dict() for tc in tool_calls] if tool_calls else None,
            )
            messages.append(assistant_message)

            # If no tool calls, we're done
            if not tool_calls:
                return response_text

            # Execute tool calls and collect results
            tool_results = []
            for tool_call in tool_calls:
                try:
                    logger.info(f"Executing tool: {tool_call.name}")
                    result = tool_executor(tool_call.name, tool_call.arguments)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_call.id,
                        "content": str(result),
                    })
                except Exception as e:
                    logger.error(f"Tool execution failed: {e}")
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_call.id,
                        "content": f"Error: {str(e)}",
                    })

            # Add tool results to conversation
            tool_result_message = Message(
                role="user",
                content=json.dumps(tool_results),
            )
            messages.append(tool_result_message)

        logger.warning(f"Tool calling loop exceeded max iterations ({max_iterations})")
        return "Max iterations reached"

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
