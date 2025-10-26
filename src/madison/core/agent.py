"""Agent for planning and executing user intents."""

import logging
from typing import Optional, Tuple

from rich.console import Console

from madison.api.client import OpenRouterClient
from madison.core.config import Config
from madison.core.permissions import PermissionManager
from madison.core.plan import Plan, PlanAction
from madison.core.plan_parser import PlanParser
from madison.tools.command_exec import CommandExecutor
from madison.tools.file_ops import FileOperations
from madison.tools.web_search import WebSearcher
from madison.core.plan import ActionType

logger = logging.getLogger(__name__)
console = Console()


class Agent:
    """Agent that understands intent and executes plans."""

    def __init__(self, config: Config, client: OpenRouterClient):
        """Initialize the agent.

        Args:
            config: Madison configuration
            client: OpenRouter API client
        """
        self.config = config
        self.client = client
        self.permission_manager = PermissionManager()
        self.file_ops = FileOperations()
        self.command_executor = CommandExecutor()
        self.web_searcher = WebSearcher()

    async def process_intent(self, user_prompt: str) -> Tuple[bool, Optional[str]]:
        """Process a user intent and execute if allowed.

        Args:
            user_prompt: The user's natural language request

        Returns:
            Tuple of (success: bool, result: Optional[str])
        """
        # Generate a plan from the user's intent
        plan = await self.generate_plan(user_prompt)

        if plan is None or not plan.actions:
            # No actions to execute - this is just a conversation
            return False, None

        # Check permissions for all actions
        all_allowed, denied_actions = self.permission_manager.check_plan_permissions(plan)

        if not all_allowed:
            # Ask user for permission
            proceed, approved_indices = self.permission_manager.prompt_for_plan(plan, denied_actions)
            if not proceed:
                return False, "Plan execution cancelled."

        # Execute the plan
        results = await self.execute_plan(plan)
        return True, results

    async def generate_plan(self, user_prompt: str) -> Optional[Plan]:
        """Generate a plan from a user prompt using the AI model.

        Args:
            user_prompt: The user's request

        Returns:
            Plan object if actions are needed, None if just conversation
        """
        # Create a system prompt that instructs the model to generate plans
        system_prompt = self._build_planning_prompt()

        try:
            # Build messages with system context included in user message
            # (OpenRouter API doesn't use separate system parameter)
            messages = [
                {
                    "role": "user",
                    "content": f"{system_prompt}\n\nUser request: {user_prompt}"
                }
            ]

            # Get the model's response about what actions to take
            response = ""
            async for chunk in self.client.chat_stream(
                messages=messages,
                model=self.config.default_model,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            ):
                response += chunk

            # Parse the response to extract actions
            plan = PlanParser.build_plan(
                response,
                reasoning="Processing user request",
                description=user_prompt[:100],  # Use first 100 chars as description
            )

            if plan:
                logger.info(f"Generated plan with {len(plan.actions)} action(s)")
                return plan

            return None

        except Exception as e:
            logger.error(f"Failed to generate plan: {e}")
            logger.debug(f"Full error: {type(e).__name__}: {e}", exc_info=True)
            return None

    async def execute_plan(self, plan: Plan) -> str:
        """Execute a plan and return the results.

        Args:
            plan: The plan to execute

        Returns:
            Summary of execution results
        """
        results = []
        console.print(f"\n[cyan]Executing plan:[/cyan] {plan.description}\n")

        for i, action in enumerate(plan.actions, 1):
            result = await self._execute_action(action, i, len(plan.actions))
            results.append(result)
            action.executed = True

        # Return summary
        return "\n".join(results)

    async def _execute_action(self, action: PlanAction, index: int, total: int) -> str:
        """Execute a single action.

        Args:
            action: The action to execute
            index: Action number in plan
            total: Total actions in plan

        Returns:
            Result summary
        """
        try:
            console.print(f"[{index}/{total}] {action.description}... ", end="")

            if action.type == "exec":
                stdout, stderr, returncode = await self.command_executor.execute(action.command)
                action.result = stdout
                if returncode == 0:
                    console.print("[green]✓[/green]")
                    return f"✓ {action.description}"
                else:
                    console.print("[red]✗[/red]")
                    action.error = stderr or f"Command failed with exit code {returncode}"
                    return f"✗ {action.description}: {action.error}"

            elif action.type == "read":
                content = self.file_ops.read(action.file_path)
                action.result = content
                console.print("[green]✓[/green]")
                return f"✓ {action.description}\n\n{content}"

            elif action.type == "write":
                self.file_ops.write(action.file_path, action.content or "")
                action.result = f"Wrote {len(action.content or '')} bytes"
                console.print("[green]✓[/green]")
                return f"✓ {action.description}"

            elif action.type == "search":
                results = await self.web_searcher.search(action.query)
                action.result = results
                console.print("[green]✓[/green]")
                return f"✓ {action.description}\n\n{results}"

            else:
                console.print("[yellow]?[/yellow]")
                return f"? {action.description}: Unknown action type"

        except Exception as e:
            console.print("[red]✗[/red]")
            action.error = str(e)
            logger.error(f"Failed to execute action {index}: {e}")

            # Ask user for guidance
            console.print(f"[red]Error:[/red] {str(e)}")
            console.print("[dim]What would you like to do?[/dim]")
            console.print("  1. Continue with next action")
            console.print("  2. Cancel plan execution")
            console.print("  3. Provide alternative instruction")

            choice = console.input("Choice (1-3): ")

            if choice == "2":
                raise Exception("Plan execution cancelled by user")
            elif choice == "3":
                alt = console.input("Enter alternative instruction: ")
                # Re-attempt with alternative instruction - would need recursive call
                # For now just log
                logger.info(f"User provided alternative: {alt}")

            return f"✗ {action.description}: {str(e)}"

    def _build_planning_prompt(self) -> str:
        """Build a system prompt that instructs the model to generate plans.

        Returns:
            System prompt string
        """
        return """You are Madison, an AI assistant that helps users accomplish tasks.

When a user asks you to do something, your job is to:
1. Understand their intent
2. Briefly explain your plan
3. Express specific actions to execute it

IMPORTANT: Use backticks (`) to delimit all actions and commands:

Action Format:
- Shell commands: `command with args here` (e.g., `mkdir foo` or `ls -la`)
- Read files: read: `path/to/file`
- Write files: write: `path/to/file`
- Search: search: `query terms`

Examples of correct format:
- "I'll create the directory: `mkdir foo`"
- "Read the file: `README.md`"
- "Search for info: `python documentation`"

CRITICAL: Always put commands/paths in backticks. Do not use quotes or other delimiters.

For simple tasks, give one action. For complex tasks, list multiple actions.
Keep actions concise and clear."""
