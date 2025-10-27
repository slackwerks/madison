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

            # Use tool calling loop to process intent
            # Pass the async execute method directly - the client handles both sync and async callbacks
            response = await self.client.call_with_tool_loop(
                initial_message=user_prompt,
                model=self.config.default_model,
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
