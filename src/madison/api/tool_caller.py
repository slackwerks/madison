"""Provider-specific tool calling handlers.

Different API providers use different formats for tool calling:
- Anthropic: tool_result blocks as message content
- OpenAI: separate messages with role="tool"
- etc.

This module provides an abstraction layer to handle these differences.
"""

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, List, Tuple

from madison.api.models import ToolCall

if TYPE_CHECKING:
    from madison.api.models import Message

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

    def serialize_message(self, message: "Message") -> Dict[str, Any]:
        """Serialize a message for the provider API.

        Default implementation just uses model_dump(). Override for provider-specific formatting.

        Args:
            message: Message to serialize

        Returns:
            Dict suitable for sending to provider API
        """
        return message.model_dump(exclude_none=True)


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

    def serialize_message(self, message: "Message") -> Dict[str, Any]:
        """Serialize a message for Anthropic API.

        Anthropic needs tool_use blocks in the content array, not in a separate field.
        """
        # Get basic message dict without tool_calls
        msg_dict = message.model_dump(exclude={"tool_calls"}, exclude_none=True)

        logger.debug(f"AnthropicToolCaller.serialize_message: role={message.role}, has_tool_calls={bool(message.tool_calls)}")

        # Convert tool_calls to content blocks for Anthropic
        if message.tool_calls and len(message.tool_calls) > 0:
            content = []

            # Add any existing text content, but skip tool_use blocks (we'll recreate from tool_calls)
            if message.content and isinstance(message.content, str):
                content.append({"type": "text", "text": message.content})
            elif isinstance(message.content, list):
                # Filter out tool_use blocks from existing content (we'll recreate them from tool_calls)
                # Keep only text blocks and other non-tool_use blocks
                for block in message.content:
                    if block.get("type") != "tool_use":
                        content.append(block)

            # Add tool_use blocks from tool_calls
            for tool_call in message.tool_calls:
                logger.debug(f"  Adding tool_call: id={tool_call.get('id')}, name={tool_call.get('function', {}).get('name')}")
                content.append({
                    "type": "tool_use",
                    "id": tool_call.get("id", ""),
                    "name": tool_call.get("function", {}).get("name", ""),
                    "input": tool_call.get("function", {}).get("arguments", {}),
                })

            msg_dict["content"] = content
            logger.debug(f"  Final content has {len(content)} blocks")
        elif message.content is None and message.role == "assistant":
            # Assistant message with no content and no tool calls - add empty text to satisfy API
            logger.debug("  Assistant message with no content - adding empty text block")
            msg_dict["content"] = [{"type": "text", "text": ""}]

        return msg_dict

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
