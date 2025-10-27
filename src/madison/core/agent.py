"""Agent for planning and executing user intents."""

import logging
from typing import Optional, Tuple

from rich.console import Console

from madison.api.client import OpenRouterClient
from madison.core.config import Config
from madison.core.permissions import PermissionManager
from madison.core.tool_executor import ToolExecutor
from madison.core.tools import get_tools_as_dicts

logger = logging.getLogger(__name__)
console = Console()


class Agent:
    """Agent that understands intent and executes tasks using tool calling."""

    def __init__(self, config: Config, client: OpenRouterClient):
        """Initialize the agent.

        Args:
            config: Madison configuration
            client: OpenRouter API client
        """
        self.config = config
        self.client = client
        self.permission_manager = PermissionManager()
        self.tool_executor = ToolExecutor()

    def _get_tool_model(self) -> str:
        """Get the model to use for tool execution.

        Falls back logic:
        1. If a 'tools' task type model is configured and supports tools, use it
        2. If default model supports tools, use it
        3. Otherwise use the tools model anyway (may fail, but user configured it)

        Returns:
            str: Model identifier to use for tool execution
        """
        default_model = self.config.default_model
        default_supports_tools = self.config.model_supports_tools(default_model)

        # If default model supports tools, use it
        if default_supports_tools:
            logger.debug(f"Using default model for tools: {default_model}")
            return default_model

        # Otherwise check for a dedicated tools model
        tools_model = self.config.models.get("tools")
        if tools_model:
            logger.info(
                f"Default model '{default_model}' doesn't support tools, "
                f"using dedicated tools model: '{tools_model}'"
            )
            return tools_model

        # No tools model configured, log warning and return default anyway
        logger.warning(
            f"Default model '{default_model}' doesn't support tools and no 'tools' model is configured. "
            "Tool execution may fail. Configure a tools model with: /model tools <model-name>"
        )
        return default_model

    async def process_intent(self, user_prompt: str) -> Tuple[bool, Optional[str]]:
        """Process a user intent and execute tools as needed.

        Args:
            user_prompt: The user's natural language request

        Returns:
            Tuple of (success: bool, result: Optional[str])
        """
        try:
            # Get available tools
            tools = get_tools_as_dicts()

            # Get the appropriate model for tool execution
            tool_model = self._get_tool_model()

            # Use tool calling loop to process intent
            # Pass the async execute method directly - the client handles both sync and async callbacks
            response = await self.client.call_with_tool_loop(
                initial_message=user_prompt,
                model=tool_model,
                tools=tools,
                tool_executor=self.tool_executor.execute,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )

            # Check if any actual work was done (vs just conversation)
            if response and response.strip():
                return True, response
            else:
                return False, None

        except Exception as e:
            error_msg = f"Failed to process intent: {str(e)}"
            logger.error(error_msg)
            logger.debug(f"Full error: {type(e).__name__}: {e}", exc_info=True)
            return False, error_msg

    def _build_system_prompt(self) -> str:
        """Build a system prompt for the tool calling agent.

        Returns:
            System prompt string
        """
        return """You are Madison, an AI assistant that helps users accomplish tasks.

When a user asks you to do something:
1. Understand their intent
2. Use the available tools to accomplish it
3. Provide a clear summary of what you did

Available tools:
- execute_command: Run shell commands (mkdir, ls, etc.)
- read_file: Read file contents
- write_file: Write or create files
- search_web: Search for information online

Always use tools to accomplish tasks. Call the appropriate tool(s) with the necessary arguments.
When done, provide a clear summary of what was accomplished."""
