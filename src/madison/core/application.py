"""Core Madison application logic, decoupled from UI implementation."""

import asyncio
import logging
from pathlib import Path
from typing import Optional, Union

from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.console import RenderableType

from madison.api.client import OpenRouterClient
from madison.core.agent import Agent
from madison.core.agent_registry import AgentManager
from madison.core.agent_commands import handle_agent_command
from madison.core.config import Config
from madison.core.history import HistoryManager
from madison.core.orchestrator import Orchestrator
from madison.core.planner import Planner
from madison.core.session import Session
from madison.core.session_manager import SessionManager
from madison.core.ui_interface import UIHandler
from madison.exceptions import (
    CommandExecutionError,
    MadisonError,
)
from madison.tools.command_exec import CommandExecutor
from madison.tools.file_ops import FileOperations
from madison.tools.web_search import WebSearcher
from madison.utils.cancellation import CancellationToken
from madison.utils.input_handler import InterruptedError, MadisonPrompt

logger = logging.getLogger(__name__)


class MadisonApplication:
    """Core Madison application logic.

    Handles the REPL loop, command dispatch, and chat processing.
    Decoupled from UI implementation via UIHandler interface.
    """

    def __init__(
        self,
        config: Config,
        ui_handler: UIHandler,
        model: Optional[str] = None,
    ):
        """Initialize the Madison application.

        Args:
            config: Configuration object
            ui_handler: UI implementation
            model: Optional model override
        """
        self.config = config
        self.ui_handler = ui_handler
        self.model = model or config.default_model

        # Initialize components
        self.session = Session(
            system_prompt=config.system_prompt,
            history_size=config.history_size,
        )
        self.file_ops = FileOperations()
        self.cmd_executor = CommandExecutor(timeout=config.timeout)
        self.searcher = WebSearcher(max_results=5)
        self.session_manager = SessionManager()
        self.history_manager = HistoryManager()
        self.agent_manager = AgentManager()

        # These will be initialized in initialize()
        self.client: Optional[OpenRouterClient] = None
        self.agent: Optional[Agent] = None

    async def initialize(self) -> None:
        """Initialize the application with async components."""
        # Create API client
        self.client = OpenRouterClient(
            self.config.api_key,
            timeout=self.config.timeout,
            max_retries=self.config.max_retries,
            retry_initial_delay=self.config.retry_initial_delay,
            retry_backoff_factor=self.config.retry_backoff_factor,
        )

        # Create agent
        self.agent = Agent(self.config, self.client)

        # Show welcome panel
        self.ui_handler.display_panel(
            f"[bold]Madison[/bold] - OpenRouter CLI\n"
            f"Model: {self.config.default_model}\n\n"
            f"Commands: [cyan]/read[/cyan], [cyan]/write[/cyan], [cyan]/exec[/cyan], "
            f"[cyan]/search[/cyan], [cyan]/ask[/cyan], [cyan]/agent[/cyan], [cyan]/clear[/cyan], [cyan]/history[/cyan], "
            f"[cyan]/save[/cyan], [cyan]/load[/cyan], [cyan]/sessions[/cyan], "
            f"[cyan]/model[/cyan], [cyan]/model-list[/cyan], [cyan]/system[/cyan], [cyan]/quit[/cyan] ([cyan]/exit[/cyan])",
            title="Madison",
        )

    async def run(self) -> None:
        """Run the main REPL loop."""
        if not self.client or not self.agent:
            raise RuntimeError("Application not initialized. Call initialize() first.")

        while True:
            try:
                # Get user input
                try:
                    user_input = await self.ui_handler.request_input()
                except InterruptedError as e:
                    if "EOF" in str(e):
                        # User pressed Ctrl+D - exit
                        self.ui_handler.display_info("Goodbye!")
                        break
                    # User pressed ESC - just continue to next prompt
                    continue

                if not user_input or not user_input.strip():
                    continue

                # Create cancellation token for this operation
                cancel_token = CancellationToken()

                # Add to history
                self.history_manager.add_entry(user_input, "query")

                # Handle special commands
                if await self._handle_commands(user_input, cancel_token):
                    continue

                # Regular chat (with agent intent processing)
                await self._handle_chat(user_input, cancel_token)

            except KeyboardInterrupt:
                self.ui_handler.display_info(
                    "Interrupted. Type '/quit' or '/exit' to exit."
                )
            except Exception as e:
                logger.exception("Error in REPL loop")
                self.ui_handler.display_error(str(e))

    async def _handle_commands(self, user_input: str, cancel_token: CancellationToken) -> bool:
        """Handle special commands.

        Args:
            user_input: User input
            cancel_token: Cancellation token

        Returns:
            bool: Whether a command was handled
        """
        if not user_input.startswith("/"):
            return False

        parts = user_input.split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if command in ("/quit", "/exit"):
            self.ui_handler.display_info("Goodbye!")
            await self.ui_handler.shutdown()
            raise KeyboardInterrupt()

        elif command == "/clear":
            self.session.clear()
            self.ui_handler.display_info("Conversation cleared.")

        elif command == "/retry":
            if not self.session.last_user_prompt:
                self.ui_handler.display_warning("No previous prompt to retry.")
            else:
                prompt_preview = self.session.last_user_prompt[:100]
                if len(self.session.last_user_prompt) > 100:
                    prompt_preview += "..."
                self.ui_handler.display_operation("retry", f"Retrying: {prompt_preview}")
                await self._handle_chat(self.session.last_user_prompt, cancel_token)

        elif command == "/history":
            history = self.session.get_history()
            if not history:
                self.ui_handler.display_warning("No conversation history yet.")
            else:
                content = "[bold]Conversation History:[/bold]\n"
                for msg in history:
                    content += f"[cyan]{msg.role.upper()}[/cyan]: {msg.content[:100]}\n"
                self.ui_handler.display_panel(content, title="History")

        elif command == "/read":
            if not args:
                self.ui_handler.display_error("Usage: /read <filepath>")
            else:
                op_context = self.ui_handler.start_operation("read", args)
                try:
                    content = self.file_ops.read(args)
                    line_count = len(content.splitlines())
                    op_context.add_detail(f"Read {line_count} lines ({len(content)} bytes)")
                    self.ui_handler.complete_operation(op_context)
                    # Format content based on file type
                    formatted_content = self._format_file_content(args, content)
                    self.ui_handler.display_panel(formatted_content, title=f"File: {args}")
                    # Add to session for context
                    self.session.add_message(
                        "user",
                        f"Please look at this file content and respond:\n\n```\n{content}\n```",
                    )
                except Exception as e:
                    op_context.add_detail(f"Error: {str(e)}", success=False)
                    self.ui_handler.complete_operation(op_context)
                    self.ui_handler.display_error(str(e))

        elif command == "/write":
            self.ui_handler.display_warning("/write command requires file path and content.")
            self.ui_handler.display_info("Usage: /write <filepath>")
            self.ui_handler.display_info("Then paste your content and press Ctrl+D (or Ctrl+Z on Windows)")

        elif command == "/model":
            await self._handle_model_command(args)

        elif command == "/model-list":
            await self._handle_model_list_command(args, cancel_token)

        elif command == "/system":
            if not args:
                self.ui_handler.display_panel(
                    self.session.system_prompt,
                    title="Current system prompt",
                )
            else:
                self.session.messages[0].content = args
                self.ui_handler.display_info("System prompt updated.")

        elif command == "/exec":
            if not args:
                self.ui_handler.display_error("Usage: /exec <command>")
            else:
                await self._handle_exec_command(args, cancel_token)

        elif command == "/search":
            if not args:
                self.ui_handler.display_error("Usage: /search <query>")
            else:
                await self._handle_search_command(args, cancel_token)

        elif command == "/save":
            try:
                session_name = args if args else None
                filename = self.session_manager.save_session(self.session, session_name)
                self.ui_handler.display_info(f"✓ Session saved as: {filename}")
                self.history_manager.add_entry(f"Saved session: {filename}", "command")
            except MadisonError as e:
                self.ui_handler.display_error(str(e))

        elif command == "/load":
            if not args:
                self.ui_handler.display_error("Usage: /load <session_name>")
            else:
                try:
                    loaded_session = self.session_manager.load_session(args)
                    self.session.messages = loaded_session.messages
                    self.session.system_prompt = loaded_session.system_prompt
                    msg_count = len(self.session.get_history())
                    self.ui_handler.display_info(f"✓ Session loaded: {args}")
                    self.ui_handler.display_info(f"Messages: {msg_count}")
                    self.history_manager.add_entry(f"Loaded session: {args}", "command")
                except MadisonError as e:
                    self.ui_handler.display_error(str(e))

        elif command == "/sessions":
            try:
                sessions = self.session_manager.list_sessions()
                if not sessions:
                    self.ui_handler.display_warning("No saved sessions yet.")
                else:
                    content = "[bold]Saved Sessions:[/bold]\n"
                    for session_info in sessions:
                        content += (
                            f"[cyan]{session_info['filename']}[/cyan] - "
                            f"[dim]{session_info['message_count']} messages[/dim] - "
                            f"[dim]{session_info['created_at']}[/dim]\n"
                        )
                    self.ui_handler.display_panel(content, title="Sessions")
            except Exception as e:
                self.ui_handler.display_error(str(e))

        elif command == "/ask":
            if not args:
                self._show_ask_help()
            else:
                await self._handle_ask_command(args, cancel_token)

        elif command == "/agent":
            selected_agent = await handle_agent_command(args, self.agent_manager, None)
            if selected_agent:
                self.agent.load_agent(selected_agent)

        else:
            self.ui_handler.display_error(f"Unknown command: {command}")
            self.ui_handler.display_info(
                "Available commands: /read, /write, /exec, /search, /ask, /agent, /clear, "
                "/retry, /history, /model, /model-list, /system, /save, /load, /sessions, /quit, /exit"
            )

        return True

    async def _handle_model_command(self, args: str) -> None:
        """Handle /model command."""
        if not args:
            # Show all configured models
            content = "[bold]Configured Models:[/bold]\n"
            for task_type, model_name in sorted(self.config.models.items()):
                tool_support = "✓ tools" if self.config.model_supports_tools(model_name) else "✗ no tools"
                content += f"[cyan]{task_type}:[/cyan] {model_name} [{tool_support}]\n"

            content += "\n[bold]Tool Execution Strategy:[/bold]\n"
            default_model = self.config.default_model
            tools_model = self.config.models.get("tools")
            default_supports = self.config.model_supports_tools(default_model)

            if default_supports:
                content += f"[green]✓[/green] Using default model for tools: {default_model}\n"
            elif tools_model:
                content += f"[green]✓[/green] Using tools model: {tools_model}\n"
                content += f"(default '{default_model}' doesn't support tools)\n"
            else:
                content += f"[yellow]⚠[/yellow] Default model '{default_model}' doesn't support tools\n"
                content += "Set a tools model with: /model tools <model-name>\n"

            self.ui_handler.display_panel(content, title="Models")
        else:
            # Parse model setting command: /model <task_type> <model_name>
            parts = args.split(maxsplit=1)
            if len(parts) == 2:
                task_type, new_model = parts
                await self._handle_model_change(new_model, task_type)
            else:
                # Single arg could be just model name (set default) or invalid
                if " " not in args:
                    # Assume setting default model
                    await self._handle_model_change(args, "default")
                else:
                    self.ui_handler.display_error("Usage: /model [task_type] [model_name]")
                    self.ui_handler.display_info(
                        "Examples:\n"
                        "  /model                                    # Show all models & strategy\n"
                        "  /model gpt-4                              # Set default model\n"
                        "  /model default gpt-4                      # Set default model\n"
                        "  /model tools claude-sonnet-4              # Set tools-only model\n"
                        "  /model thinking claude-opus               # Set thinking model\n"
                    )

    async def _handle_model_list_command(self, args: str, cancel_token: CancellationToken) -> None:
        """Handle /model-list command."""
        if not args:
            self.ui_handler.display_error("Usage: /model-list <search_term> OR /model-list series=<series>")
            self.ui_handler.display_info(
                "Examples:\n"
                "  /model-list gpt                 # Search for 'gpt' models\n"
                "  /model-list claude              # Search for 'claude' models\n"
                "  /model-list series=gpt          # List all GPT series models\n"
                "  /model-list series=claude       # List all Claude series models"
            )
        else:
            try:
                self.ui_handler.display_operation("model-list", "Fetching available models from OpenRouter...")
                models = await self.client.list_models()

                # Parse the search term or series filter
                search_term = None
                series_filter = None

                if args.startswith("series="):
                    series_filter = args[7:].lower()
                else:
                    search_term = args.lower()

                # Filter models
                matching_models = []
                for model in models:
                    model_id = model.get("id", "").lower()
                    model_name = model.get("name", "").lower()

                    if series_filter:
                        if series_filter in model_id or series_filter in model_name:
                            matching_models.append(model)
                    elif search_term:
                        if search_term in model_id or search_term in model_name:
                            matching_models.append(model)

                if not matching_models:
                    self.ui_handler.display_warning(f"No models found matching: {args}")
                else:
                    # Check if cancelled
                    if cancel_token.is_cancelled:
                        self.ui_handler.display_warning("Operation cancelled.")
                        return

                    content = f"[bold]Found {len(matching_models)} model(s) matching '{args}':[/bold]\n"
                    for model in matching_models[:50]:
                        model_id = model.get("id", "unknown")
                        model_name = model.get("name", "")
                        pricing = model.get("pricing", {})
                        input_price = pricing.get("prompt", "N/A")
                        output_price = pricing.get("completion", "N/A")

                        content += f"\n[cyan]{model_id}[/cyan]\n"
                        if model_name:
                            content += f"  Name: {model_name}\n"
                        content += f"  Input: ${input_price} | Output: ${output_price}\n"

                    if len(matching_models) > 50:
                        content += f"\n[dim]... and {len(matching_models) - 50} more (showing first 50)[/dim]\n"

                    content += "\n[dim]Tip: Use /model <strategy> <model_id> to register a model for a strategy[/dim]"
                    self.ui_handler.display_panel(content, title="Models")

            except Exception as e:
                logger.exception("Error listing models")
                self.ui_handler.display_error(str(e))

    async def _handle_model_change(self, new_model: str, task_type: str) -> None:
        """Handle model change with validation."""
        supports_tools = self.config.model_supports_tools(new_model)

        if not supports_tools:
            self.ui_handler.display_warning(f"Model {new_model} does NOT support tool calling")
            self.ui_handler.display_info("This means the agent won't be able to execute commands, read files, etc.")
            self.ui_handler.display_info("The model will only be available for regular chat conversations.")

            # Ask for confirmation
            response = await self.ui_handler.prompt_user(
                "Continue setting this model anyway? [y/N]",
                options=["y", "n"],
            )
            if response.lower() not in ("y", "yes"):
                self.ui_handler.display_warning("Model change cancelled.")
                return

        self.config.set_model(new_model, task_type)
        self.config.save()

        tool_indicator = "[green]✓ supports tools[/green]" if supports_tools else "[yellow]✗ no tool support[/yellow]"
        self.ui_handler.display_info(f"✓ Set {task_type} model to: {new_model} {tool_indicator}")
        self.history_manager.add_entry(f"Set {task_type} model to {new_model}", "command")

    async def _handle_exec_command(self, command: str, cancel_token: CancellationToken) -> None:
        """Handle /exec command."""
        op_context = self.ui_handler.start_operation("exec", command)
        try:
            if cancel_token.is_cancelled:
                op_context.add_detail("Cancelled", success=False)
                self.ui_handler.complete_operation(op_context)
                return

            stdout, stderr, returncode = await self.cmd_executor.execute(command)

            if cancel_token.is_cancelled:
                op_context.add_detail("Cancelled", success=False)
                self.ui_handler.complete_operation(op_context)
                return

            success = returncode == 0
            op_context.add_detail(f"Exit code: {returncode}", success=success)
            if stdout:
                op_context.add_detail(f"Output: {len(stdout)} bytes")
            if stderr:
                op_context.add_detail(f"Errors: {len(stderr)} bytes", success=False)
            self.ui_handler.complete_operation(op_context)

            output = ""
            if stdout:
                output += f"[bold cyan]Output:[/bold cyan]\n{stdout}\n"
            if stderr:
                output += f"[bold red]Errors:[/bold red]\n{stderr}\n"
            if returncode != 0:
                output += f"[yellow]Exit code: {returncode}[/yellow]\n"

            self.ui_handler.display_panel(output, title="Execution Result")

            # Add to session for context
            context_msg = f"Command: {command}\n\nOutput:\n{stdout}"
            if stderr:
                context_msg += f"\n\nErrors:\n{stderr}"
            self.session.add_message("user", context_msg)
        except CommandExecutionError as e:
            self.ui_handler.display_error(str(e))

    async def _handle_search_command(self, query: str, cancel_token: CancellationToken) -> None:
        """Handle /search command."""
        op_context = self.ui_handler.start_operation("search", query)
        try:
            if cancel_token.is_cancelled:
                op_context.add_detail("Cancelled", success=False)
                self.ui_handler.complete_operation(op_context)
                return

            results = await self.searcher.search(query)

            if cancel_token.is_cancelled:
                op_context.add_detail("Cancelled", success=False)
                self.ui_handler.complete_operation(op_context)
                return

            op_context.add_detail(f"Found {len(str(results))} characters")
            self.ui_handler.complete_operation(op_context)

            self.ui_handler.display_panel(str(results), title="Search Results")

            # Add search results to session for context
            self.session.add_message("user", f"Web search results for '{query}':\n\n{results}")
        except MadisonError as e:
            op_context.add_detail(f"Error: {str(e)}", success=False)
            self.ui_handler.complete_operation(op_context)
            self.ui_handler.display_error(str(e))

    def _format_file_content(self, file_path: str, content: str) -> RenderableType:
        """Format file content based on file type for rich display.

        Args:
            file_path: The file path (used to detect file type)
            content: The file content

        Returns:
            A Rich renderable object (Syntax, Markdown, or plain string)
        """
        path = Path(file_path)
        suffix = path.suffix.lower()

        # Markdown files
        if suffix == ".md":
            return Markdown(content)

        # Code files with syntax highlighting
        code_extensions = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".jsx": "javascript",
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".toml": "toml",
            ".rust": "rust",
            ".rs": "rust",
            ".go": "go",
            ".java": "java",
            ".cpp": "cpp",
            ".c": "c",
            ".h": "c",
            ".hpp": "cpp",
            ".cs": "csharp",
            ".rb": "ruby",
            ".php": "php",
            ".swift": "swift",
            ".kt": "kotlin",
            ".scala": "scala",
            ".sh": "bash",
            ".bash": "bash",
            ".html": "html",
            ".htm": "html",
            ".css": "css",
            ".scss": "scss",
            ".sql": "sql",
            ".xml": "xml",
            ".vim": "vim",
        }

        if suffix in code_extensions:
            language = code_extensions[suffix]
            try:
                return Syntax(content, language, theme="monokai", line_numbers=True)
            except Exception:
                # Fallback to plain text if syntax highlighting fails
                return content

        # Plain text for other files
        return content

    def _show_ask_help(self) -> None:
        """Show help for /ask command."""
        content = (
            "[red]Usage: /ask <strategy|model=MODEL> <prompt>[/red]\n\n"
            "[dim]Examples:[/dim]\n"
            "  /ask thinking What is 2+2?\n"
            "  /ask planning Write a 5-year plan\n"
            "  /ask model=gpt-4 Quick question\n\n"
            "[dim]Available strategies:[/dim]\n"
        )
        for strategy_name in sorted(self.config.models.keys()):
            model_name = self.config.models[strategy_name]
            content += f"  [cyan]{strategy_name}[/cyan] → {model_name}\n"

        self.ui_handler.display_panel(content, title="/ask Help")

    async def _handle_ask_command(self, args: str, cancel_token: CancellationToken) -> None:
        """Handle /ask command."""
        parts = args.split(maxsplit=1)
        if len(parts) != 2:
            self._show_ask_help()
            return

        strategy_or_model, prompt = parts

        # Determine which model to use
        specific_model = None
        strategy_label = None

        if strategy_or_model.startswith("model="):
            specific_model = strategy_or_model[6:]
            strategy_label = specific_model
        else:
            strategy_name = strategy_or_model
            if strategy_name in self.config.models:
                specific_model = self.config.models[strategy_name]
                strategy_label = strategy_name
            else:
                self.ui_handler.display_error(f"Unknown strategy: {strategy_name}")
                self._show_ask_help()
                return

        try:
            self.session.add_message("user", prompt)

            header = f"Assistant ({strategy_label} — {specific_model})"
            self.ui_handler.start_streaming(header)

            response_text = ""
            async for token in self.client.chat_stream(
                messages=self.session.get_messages(),
                model=specific_model,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            ):
                if cancel_token.is_cancelled:
                    self.ui_handler.end_streaming()
                    self.ui_handler.display_warning("Response interrupted by user.")
                    break

                self.ui_handler.stream_token(token)
                response_text += token

            self.ui_handler.end_streaming()

            if response_text and not cancel_token.is_cancelled:
                self.session.add_message("assistant", response_text)

            self.history_manager.add_entry(f"Asked {strategy_label}: {prompt[:50]}...", "query")
        except Exception as e:
            logger.exception("Error in /ask command")
            self.ui_handler.display_error(str(e))

    async def _handle_chat(self, user_input: str, cancel_token: CancellationToken) -> None:
        """Handle a regular chat message."""
        self.session.last_user_prompt = user_input

        # Try orchestration first if enabled
        if self.config.enable_orchestration:
            try:
                planner = Planner(self.config, self.client)

                history = self.session.get_history()[-10:] if self.session.get_history() else []
                recent_messages = [{"role": msg.role, "content": msg.content} for msg in history]

                plan = await planner.plan(user_input, conversation_history=recent_messages)

                if plan:
                    if self.config.show_execution_plan:
                        task_summary = ", ".join(task.task_id for task in plan.tasks)
                        self.ui_handler.display_plain(f"Created plan with tasks: {task_summary}")

                    orchestrator = Orchestrator(self.config, self.client, self.agent.tool_executor, self.ui_handler)
                    result = await orchestrator.execute(plan)

                    self.session.add_message("user", user_input)
                    self.session.add_message("assistant", result)
                    # Display result on right pane, not left
                    self.ui_handler.display_panel(result, title="Execution Result")
                    return
            except Exception as e:
                logger.debug(f"Orchestration failed (falling back to agent/chat): {e}")

        # Try agent processing
        try:
            intent_handled, intent_result = await self.agent.process_intent(user_input)
            if intent_handled and intent_result:
                self.session.add_message("user", user_input)
                self.session.add_message("assistant", f"Executed plan:\n{intent_result}")
                # Display result on right pane, not left
                self.ui_handler.display_panel(intent_result, title="Agent Execution Result")
                return
        except Exception as e:
            logger.debug(f"Agent processing failed (continuing with chat): {e}")

        # Regular chat
        self.session.add_message("user", user_input)

        try:
            header = "[bold cyan]Assistant"
            if self.agent.active_agent:
                agent_name = self.agent.active_agent.name
                agent_category = self.agent.active_agent.category
                header += f" ({agent_name}"
                if agent_category:
                    header += f" — {agent_category}"
                header += ")"
            header += f" — {self.config.default_model}[/bold cyan]"

            self.ui_handler.start_streaming(header)

            response_text = ""
            async for token in self.client.chat_stream(
                messages=self.session.get_messages(),
                model=self.config.default_model,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            ):
                if cancel_token.is_cancelled:
                    self.ui_handler.end_streaming()
                    self.ui_handler.display_warning("Response interrupted by user.")
                    break

                self.ui_handler.stream_token(token)
                response_text += token

            self.ui_handler.end_streaming()

            if response_text and not cancel_token.is_cancelled:
                self.session.add_message("assistant", response_text)

        except Exception as e:
            logger.exception("Error getting chat response")
            self.ui_handler.display_error(str(e))
