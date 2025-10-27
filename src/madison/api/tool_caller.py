"""Provider-specific tool calling handlers.

Different API providers use different formats for tool calling:
- Anthropic: tool_result blocks as message content
- OpenAI: separate messages with role="tool"
- etc.

This module provides an abstraction layer to handle these differences.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple

from madison.api.models import Message, ToolCall

logger = logging.getLogger(__name__)


class ToolCaller(ABC):
    """Base class for provider-specific tool calling handlers."""

    @abstractmethod
    def get_system_tools(self) -> List[Dict[str, Any]]:
        """Get tools in provider-specific format."""
        pass

    @abstractmethod
    def extract_tool_calls(self, response_dict: Dict[str, Any]) -> List[ToolCall]:
        """Extract tool calls from model response."""
        pass

    @abstractmethod
    def format_tool_results(
        self, tool_results: List[Dict[str, Any]]
    ) -> Tuple[str, str, Dict[str, Any]]:
        """Format tool results for next API call.

        Returns:
            Tuple of (role, content_type, content_data)
            - role: "user" or other
            - content_type: "text", "blocks", or "messages"
            - content_data: formatted content for the provider
        """
        pass


class AnthropicToolCaller(ToolCaller):
    """Handles tool calling for Anthropic models (claude-3.5-sonnet, claude-opus, etc.)"""

    def get_system_tools(self) -> List[Dict[str, Any]]:
        """Return tools in Anthropic format (tool_use support built-in)."""
        # Anthropic handles tools via system prompt and native tool_use blocks
        # This is handled by the API client directly
        return []

    def extract_tool_calls(self, response_dict: Dict[str, Any]) -> List[ToolCall]:
        """Extract tool calls from Anthropic response.

        Anthropic returns tool_use blocks in the content array.
        """
        tool_calls = []

        message = response_dict.get("message", {})
        content = message.get("content", [])

        for block in content:
            if block.get("type") == "tool_use":
                tool_call = ToolCall(
                    id=block.get("id", ""),
                    type="function",
                    function={
                        "name": block.get("name", ""),
                        "arguments": block.get("input", {}),
                    },
                )
                tool_calls.append(tool_call)

        return tool_calls

    def format_tool_results(
        self, tool_results: List[Dict[str, Any]]
    ) -> Tuple[str, str, Any]:
        """Format tool results as Anthropic content blocks.

        Anthropic expects tool_result blocks in the content array of a user message.
        """
        # Convert to Anthropic's tool_result format
        anthropic_results = []
        for result in tool_results:
            anthropic_results.append({
                "type": "tool_result",
                "tool_use_id": result.get("tool_use_id", ""),
                "content": result.get("content", ""),
            })

        return "user", "blocks", anthropic_results


class OpenAIToolCaller(ToolCaller):
    """Handles tool calling for OpenAI models (gpt-4, gpt-3.5-turbo, etc.)"""

    def get_system_tools(self) -> List[Dict[str, Any]]:
        """Return tools in OpenAI format (functions parameter)."""
        # OpenAI uses a separate tools/functions parameter
        # This is handled by the API client's tools parameter
        return []

    def extract_tool_calls(self, response_dict: Dict[str, Any]) -> List[ToolCall]:
        """Extract tool calls from OpenAI response.

        OpenAI returns tool_calls in the message.
        """
        tool_calls = []

        message = response_dict.get("message", {})
        message_tool_calls = message.get("tool_calls", [])

        for tool_call_data in message_tool_calls:
            if tool_call_data.get("type") == "function":
                tool_call = ToolCall(
                    id=tool_call_data.get("id", ""),
                    type="function",
                    function=tool_call_data.get("function", {}),
                )
                tool_calls.append(tool_call)

        return tool_calls

    def format_tool_results(
        self, tool_results: List[Dict[str, Any]]
    ) -> Tuple[str, str, Any]:
        """Format tool results as OpenAI tool messages.

        OpenAI expects each tool result as a separate message with role="tool".
        """
        # Return as separate messages (role="tool")
        # The client will add these to the messages list
        messages = []
        for result in tool_results:
            messages.append({
                "role": "tool",
                "tool_call_id": result.get("tool_use_id", ""),
                "content": result.get("content", ""),
            })

        return "tool", "messages", messages


def get_tool_caller(model: str) -> ToolCaller:
    """Get the appropriate ToolCaller for a model.

    Args:
        model: Model identifier (e.g., "anthropic/claude-3-opus", "openai/gpt-4")

    Returns:
        ToolCaller instance for the model's provider
    """
    if model.startswith("anthropic/"):
        return AnthropicToolCaller()
    elif model.startswith("openai/"):
        return OpenAIToolCaller()
    else:
        # Default to Anthropic format for unknown models
        # (most likely to be compatible)
        logger.warning(
            f"Unknown model provider for {model}, defaulting to Anthropic tool format"
        )
        return AnthropicToolCaller()
