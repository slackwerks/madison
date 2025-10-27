"""Model capability registry for tracking tool calling support."""

import logging
from typing import Dict, List, Set

logger = logging.getLogger(__name__)


class ModelRegistry:
    """Registry of model capabilities, particularly tool calling support."""

    # Models known to support tool calling
    # Based on OpenRouter documentation and provider capabilities
    TOOL_CALLING_MODELS: Set[str] = {
        # OpenAI models (via OpenRouter)
        "openai/gpt-4",
        "openai/gpt-4-turbo",
        "openai/gpt-4-turbo-preview",
        "openai/gpt-3.5-turbo",
        "openai/gpt-4-32k",
        "openai/gpt-4-1106-preview",
        "openai/gpt-4-vision",

        # Anthropic Claude models
        "anthropic/claude-3-opus",
        "anthropic/claude-3-sonnet",
        "anthropic/claude-3-haiku",
        "anthropic/claude-2",
        "anthropic/claude-2.1",
        "anthropic/claude-instant",

        # Google models
        "google/gemini-pro",
        "google/palm-2",

        # Meta Llama models
        "meta-llama/llama-2-70b-chat",
        "meta-llama/llama-2-13b-chat",
        "meta-llama/llama-2-7b-chat",

        # Mistral models
        "mistralai/mistral-7b-instruct",
        "mistralai/mistral-medium",
        "mistralai/mistral-large",

        # Other capable models
        "nousresearch/nous-hermes-2-mixtral-8x7b-dpo",
        "databricks/dbrx-instruct",
    }

    # Model families with partial or experimental tool calling support
    EXPERIMENTAL_TOOL_MODELS: Set[str] = {
        # Models being tested or with limited tool support
        "openchat/openchat-7b",
        "gryphe/mythomax-l2-13b",
    }

    # Known models without tool calling support
    # (helps avoid unnecessary API calls with unsupported models)
    NO_TOOL_MODELS: Set[str] = {
        "openai/text-davinci-003",  # Legacy models
        "openai/text-davinci-002",
        "huggingface/meta-llama/llama-2-70b",  # Base versions without chat tuning
        "huggingface/meta-llama/llama-2-13b",
        "huggingface/mistral-7b",
    }

    @classmethod
    def supports_tools(cls, model: str) -> bool:
        """Check if a model supports tool calling.

        Args:
            model: Model identifier (e.g., 'openai/gpt-4', 'anthropic/claude-3-opus')

        Returns:
            bool: True if model supports tool calling
        """
        # Exact match in supported models
        if model in cls.TOOL_CALLING_MODELS:
            return True

        # Check if model matches a known family pattern
        # (e.g., openai/gpt-4 matches all gpt-4 variants)
        for supported in cls.TOOL_CALLING_MODELS:
            if model.startswith(supported):
                return True

        # Check experimental models
        if model in cls.EXPERIMENTAL_TOOL_MODELS:
            return True

        # Known unsupported
        if model in cls.NO_TOOL_MODELS:
            return False

        # Default to assuming tools are supported for modern models
        # This is more optimistic than pessimistic
        logger.warning(f"Model {model} not in registry, assuming tool calling supported")
        return True

    @classmethod
    def register_model(cls, model: str, supports_tools: bool) -> None:
        """Register a model's tool calling capability.

        Args:
            model: Model identifier
            supports_tools: Whether the model supports tool calling
        """
        if supports_tools:
            cls.TOOL_CALLING_MODELS.add(model)
            cls.NO_TOOL_MODELS.discard(model)
        else:
            cls.NO_TOOL_MODELS.add(model)
            cls.TOOL_CALLING_MODELS.discard(model)

        logger.info(f"Registered model {model}: tools={'supported' if supports_tools else 'not supported'}")

    @classmethod
    def get_supported_models(cls) -> List[str]:
        """Get list of all known tool-supporting models.

        Returns:
            List of model identifiers
        """
        return sorted(list(cls.TOOL_CALLING_MODELS))

    @classmethod
    def get_unsupported_models(cls) -> List[str]:
        """Get list of all known models without tool support.

        Returns:
            List of model identifiers
        """
        return sorted(list(cls.NO_TOOL_MODELS))
