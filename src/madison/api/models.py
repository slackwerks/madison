"""Data models for OpenRouter API."""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class Message(BaseModel):
    """Chat message model."""

    role: str = Field(..., description="Message role: 'user', 'assistant', or 'system'")
    content: Optional[Union[str, List[Dict[str, Any]]]] = Field(
        default=None,
        description="Message content (string for text, list of dicts for tool results)"
    )
    tool_calls: Optional[List[Dict[str, Any]]] = Field(default=None, description="Tool calls made by assistant")


class ToolCall(BaseModel):
    """Tool call from model."""

    id: str = Field(..., description="Tool call ID")
    type: str = Field(default="function", description="Tool type (always 'function')")
    function: Dict[str, Any] = Field(..., description="Function call details")

    @property
    def name(self) -> str:
        """Get function name."""
        return self.function.get("name", "")

    @property
    def arguments(self) -> Dict[str, Any]:
        """Get function arguments as dict."""
        import json

        args_str = self.function.get("arguments", "{}")
        if isinstance(args_str, str):
            return json.loads(args_str)
        return args_str


class ChatCompletionRequest(BaseModel):
    """Chat completion request model."""

    model: str = Field(..., description="Model name from OpenRouter")
    messages: List[Message] = Field(..., description="List of messages")
    temperature: Optional[float] = Field(default=None)
    max_tokens: Optional[int] = Field(default=None)
    top_p: Optional[float] = Field(default=None)
    frequency_penalty: Optional[float] = Field(default=None)
    presence_penalty: Optional[float] = Field(default=None)
    top_k: Optional[int] = Field(default=None)
    repetition_penalty: Optional[float] = Field(default=None)
    min_p: Optional[float] = Field(default=None)
    stop: Optional[List[str]] = Field(default=None)
    stream: Optional[bool] = Field(default=False)
    tools: Optional[List[Dict[str, Any]]] = Field(default=None, description="Tools available for tool calling")

    class Config:
        """Pydantic config."""

        extra = "forbid"

    def to_openrouter_dict(self) -> Dict[str, Any]:
        """Convert to OpenRouter API format."""
        data = {
            "model": self.model,
            "messages": [m.dict() for m in self.messages],
        }

        # Add optional fields only if they're set
        optional_fields = [
            "temperature",
            "max_tokens",
            "top_p",
            "frequency_penalty",
            "presence_penalty",
            "top_k",
            "repetition_penalty",
            "min_p",
            "stop",
            "stream",
            "tools",
        ]

        for field in optional_fields:
            value = getattr(self, field)
            if value is not None:
                data[field] = value

        return data


class ChatCompletionChoice(BaseModel):
    """Chat completion choice model."""

    index: int = Field(..., description="Choice index")
    message: Optional[Message] = Field(default=None)
    delta: Optional[Dict[str, Any]] = Field(default=None)
    finish_reason: Optional[str] = Field(default=None)


class ChatCompletionUsage(BaseModel):
    """Token usage information."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    """Chat completion response model."""

    id: str
    object: str
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    usage: Optional[ChatCompletionUsage] = Field(default=None)


class Model(BaseModel):
    """OpenRouter model information."""

    id: str
    name: str
    description: Optional[str] = Field(default=None)
    context_length: Optional[int] = Field(default=None)
    pricing: Optional[Dict[str, Any]] = Field(default=None)
