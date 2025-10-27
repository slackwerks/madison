"""Main CLI interface for Madison."""

import asyncio
import logging
import sys
from typing import Optional

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax

from madison.api.client import OpenRouterClient
from madison.api.models import Message
from madison.core.agent import Agent
from madison.core.agent_registry import AgentManager
from madison.core.agent_commands import handle_agent_command
from madison.core.config import Config
from madison.core.history import HistoryManager
from madison.core.session import Session
from madison.core.session_manager import SessionManager
from madison.exceptions import (
    CommandExecutionError,
    ConfigError,
    FileOperationError,
    MadisonError,
)
from madison.tools.command_exec import CommandExecutor
from madison.tools.file_ops import FileOperations
from madison.tools.web_search import WebSearcher
from madison.utils.cancellation import CancellationToken
from madison.utils.input_handler import InterruptedError, MadisonPrompt
from madison.utils.setup import run_setup_wizard

# Setup logging
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = typer.Typer(
    name="madison",
    help="A Python CLI for interacting with OpenRouter models",
    invoke_without_command=True,
)
console = Console()


def setup_logging(verbose: bool = False):
    """Setup logging level."""
    if verbose:
        logging.getLogger("madison").setLevel(logging.DEBUG)
    else:
        logging.getLogger("madison").setLevel(logging.WARNING)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    model: Optional[str] = typer.Option(
        None, "--model", "-m", help="OpenRouter model to use"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
):
    """Madison - OpenRouter CLI. Start an interactive chat session by default."""
    # If a subcommand was invoked, don't run chat
    if ctx.invoked_subcommand is not None:
        return

    # Otherwise, run chat
    setup_logging(verbose)

    try:
        # Load configuration
        config = Config.load()
        model = model or config.default_model

        # Initialize file operations
        file_ops = FileOperations()

        # Initialize session
        session = Session(
            system_prompt=config.system_prompt,
            history_size=config.history_size,
        )

        # Run the REPL
        asyncio.run(_repl_loop(config, session, model, file_ops))

    except ConfigError as e:
        console.print(f"[red]Configuration Error:[/red] {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Goodbye![/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        if verbose:
            logger.exception("Unexpected error")
        sys.exit(1)


async def _repl_loop(
    config: Config,
    session: Session,
    model: str,
    file_ops: FileOperations,
):
    """Main REPL loop.

    Args:
        config: Configuration
        session: Conversation session
        model: Model to use
        file_ops: File operations handler
    """
    console.print(
        Panel(
            f"[bold]Madison[/bold] - OpenRouter CLI\n"
            f"Model: {config.default_model}\n\n"
            f"Commands: [cyan]/read[/cyan], [cyan]/write[/cyan], [cyan]/exec[/cyan], "
            f"[cyan]/search[/cyan], [cyan]/ask[/cyan], [cyan]/agent[/cyan], [cyan]/clear[/cyan], [cyan]/history[/cyan], "
            f"[cyan]/save[/cyan], [cyan]/load[/cyan], [cyan]/sessions[/cyan], "
            f"[cyan]/model[/cyan], [cyan]/model-list[/cyan], [cyan]/system[/cyan], [cyan]/quit[/cyan] ([cyan]/exit[/cyan])",
            expand=False,
        )
    )

    # Initialize tools and managers
    cmd_executor = CommandExecutor(timeout=config.timeout)
    searcher = WebSearcher(max_results=5)
    session_manager = SessionManager()
    history_manager = HistoryManager()
    prompt = MadisonPrompt()
    agent_manager = AgentManager()

    async with OpenRouterClient(
        config.api_key,
        timeout=config.timeout,
        max_retries=config.max_retries,
        retry_initial_delay=config.retry_initial_delay,
        retry_backoff_factor=config.retry_backoff_factor,
    ) as client:
        # Initialize agent for intent processing
        agent = Agent(config, client)
        while True:
            try:
                # Get user input (can be interrupted with ESC)
                try:
                    user_input = await prompt.prompt_async()
                except InterruptedError as e:
                    if "EOF" in str(e):
                        # User pressed Ctrl+D - exit
                        console.print("[yellow]Goodbye![/yellow]")
                        sys.exit(0)
                    # User pressed ESC - just continue to next prompt
                    continue

                if not user_input or not user_input.strip():
                    continue

                # Create cancellation token for this operation
                cancel_token = CancellationToken()

                # Add to history
                history_manager.add_entry(user_input, "query")

                # Handle special commands
                if await _handle_commands(
                    user_input, session, file_ops, config, client, model, cmd_executor, searcher, cancel_token, session_manager, history_manager, agent, agent_manager, prompt
                ):
                    continue

                # Regular chat (with agent intent processing)
                await _handle_chat(
                    user_input, session, client, model, config, file_ops, cancel_token, agent
                )

            except KeyboardInterrupt:
                console.print("\n[yellow]Interrupted. Type '/quit' or '/exit' to exit.[/yellow]")
            except Exception as e:
                logger.exception("Error in REPL loop")
                console.print(f"[red]Error:[/red] {e}")


async def _handle_commands(
    user_input: str,
    session: Session,
    file_ops: FileOperations,
    config: Config,
    client: OpenRouterClient,
    model: str,
    cmd_executor: CommandExecutor,
    searcher: WebSearcher,
    cancel_token: CancellationToken,
    session_manager: SessionManager,
    history_manager: HistoryManager,
    agent: Agent,
    agent_manager: AgentManager,
    prompt: MadisonPrompt,
) -> bool:
    """Handle special commands.

    Args:
        user_input: User input
        session: Session
        file_ops: File operations
        config: Config
        client: API client
        model: Current model
        cmd_executor: Command executor
        searcher: Web searcher
        cancel_token: Cancellation token
        session_manager: Session manager
        history_manager: History manager

    Returns:
        bool: Whether a command was handled
    """
    if not user_input.startswith("/"):
        return False

    parts = user_input.split(maxsplit=1)
    command = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""

    if command in ("/quit", "/exit"):
        console.print("[yellow]Goodbye![/yellow]")
        sys.exit(0)

    elif command == "/clear":
        session.clear()
        console.print("[green]Conversation cleared.[/green]")

    elif command == "/retry":
        if not session.last_user_prompt:
            console.print("[yellow]No previous prompt to retry.[/yellow]")
        else:
            console.print(f"[dim]Retrying: {session.last_user_prompt[:100]}{'...' if len(session.last_user_prompt) > 100 else ''}[/dim]")
            await _handle_chat(
                session.last_user_prompt, session, client, model, config, file_ops, cancel_token, agent
            )

    elif command == "/history":
        history = session.get_history()
        if not history:
            console.print("[yellow]No conversation history yet.[/yellow]")
        else:
            console.print("\n[bold]Conversation History:[/bold]")
            for msg in history:
                role = f"[cyan]{msg.role.upper()}[/cyan]"
                console.print(f"{role}: {msg.content[:100]}")

    elif command == "/read":
        if not args:
            console.print("[red]Usage: /read <filepath>[/red]")
        else:
            try:
                content = file_ops.read(args)
                console.print(f"\n[bold]Contents of {args}:[/bold]")
                console.print(Syntax(content, "python", theme="monokai", line_numbers=True))
                # Add to session for context
                session.add_message(
                    "user",
                    f"Please look at this file content and respond:\n\n```\n{content}\n```",
                )
            except FileOperationError as e:
                console.print(f"[red]Error:[/red] {e}")

    elif command == "/write":
        console.print("[yellow]/write command requires file path and content.[/yellow]")
        console.print("[yellow]Usage: /write <filepath>[/yellow]")
        console.print("[yellow]Then paste your content and press Ctrl+D (or Ctrl+Z on Windows)[/yellow]")
        # For now, just acknowledge
        # Full implementation would require reading multi-line input

    elif command == "/model":
        if not args:
            # Show all configured models
            console.print("\n[bold]Configured Models:[/bold]")
            for task_type, model_name in sorted(config.models.items()):
                tool_support = "✓ tools" if config.model_supports_tools(model_name) else "✗ no tools"
                console.print(f"  [cyan]{task_type}:[/cyan] {model_name} [{tool_support}]")

            # Show which model will be used for tool execution
            console.print("\n[bold]Tool Execution Strategy:[/bold]")
            default_model = config.default_model
            tools_model = config.models.get("tools")
            default_supports = config.model_supports_tools(default_model)

            if default_supports:
                console.print(f"  [green]✓[/green] Using default model for tools: {default_model}")
            elif tools_model:
                console.print(f"  [green]✓[/green] Using tools model: {tools_model}")
                console.print(f"    (default '{default_model}' doesn't support tools)")
            else:
                console.print(f"  [yellow]⚠[/yellow] Default model '{default_model}' doesn't support tools")
                console.print(f"    Set a tools model with: /model tools <model-name>")
        else:
            # Parse model setting command: /model <task_type> <model_name>
            parts = args.split(maxsplit=1)
            if len(parts) == 2:
                task_type, new_model = parts
                _handle_model_change(config, new_model, task_type, history_manager)
            else:
                # Single arg could be just model name (set default) or invalid
                if " " not in args:
                    # Assume setting default model
                    _handle_model_change(config, args, "default", history_manager)
                else:
                    console.print("[red]Usage: /model [task_type] [model_name][/red]")
                    console.print("[dim]Examples:[/dim]")
                    console.print("  /model                                    # Show all models & strategy")
                    console.print("  /model gpt-4                              # Set default model")
                    console.print("  /model default gpt-4                      # Set default model")
                    console.print("  /model tools claude-sonnet-4              # Set tools-only model")
                    console.print("  /model thinking claude-opus               # Set thinking model")
                    console.print("\n[dim]Tool Execution Model:[/dim]")
                    console.print("  Use '/model tools <model>' to set a dedicated model for tool execution.")
                    console.print("  This is useful when your default model doesn't support tool calling.")

    elif command == "/model-list":
        if not args:
            console.print("[red]Usage: /model-list <search_term> OR /model-list series=<series>[/red]")
            console.print("[dim]Examples:[/dim]")
            console.print("  /model-list gpt                 # Search for 'gpt' models")
            console.print("  /model-list claude              # Search for 'claude' models")
            console.print("  /model-list series=gpt          # List all GPT series models")
            console.print("  /model-list series=claude       # List all Claude series models")
        else:
            try:
                console.print("[dim]Fetching available models from OpenRouter...[/dim]")
                models = await client.list_models()

                # Parse the search term or series filter
                search_term = None
                series_filter = None

                if args.startswith("series="):
                    series_filter = args[7:].lower()  # Remove "series=" prefix
                else:
                    search_term = args.lower()

                # Filter models
                matching_models = []
                for model in models:
                    model_id = model.get("id", "").lower()
                    model_name = model.get("name", "").lower()

                    if series_filter:
                        # Filter by series (e.g., "gpt", "claude")
                        if series_filter in model_id or series_filter in model_name:
                            matching_models.append(model)
                    elif search_term:
                        # Search by term
                        if search_term in model_id or search_term in model_name:
                            matching_models.append(model)

                if not matching_models:
                    console.print(
                        f"[yellow]No models found matching: {args}[/yellow]"
                    )
                else:
                    console.print(
                        f"\n[bold]Found {len(matching_models)} model(s) matching '{args}':[/bold]"
                    )
                    for model in matching_models[:50]:  # Limit to 50 results
                        model_id = model.get("id", "unknown")
                        model_name = model.get("name", "")
                        pricing = model.get("pricing", {})
                        input_price = pricing.get("prompt", "N/A")
                        output_price = pricing.get("completion", "N/A")

                        console.print(f"\n[cyan]{model_id}[/cyan]")
                        if model_name:
                            console.print(f"  Name: {model_name}")
                        console.print(f"  Input: ${input_price} | Output: ${output_price}")

                    if len(matching_models) > 50:
                        console.print(
                            f"\n[dim]... and {len(matching_models) - 50} more (showing first 50)[/dim]"
                        )

                    console.print()
                    console.print("[dim]Tip: Use /model <strategy> <model_id> to register a model for a strategy[/dim]")
            except Exception as e:
                logger.exception("Error listing models")
                console.print(f"[red]Error:[/red] {e}")

    elif command == "/system":
        if not args:
            console.print(f"[cyan]Current system prompt:[/cyan]\n{session.system_prompt}")
        else:
            session.messages[0].content = args
            console.print("[green]System prompt updated.[/green]")

    elif command == "/exec":
        if not args:
            console.print("[red]Usage: /exec <command>[/red]")
        else:
            try:
                console.print(f"[dim]Executing:[/dim] {args}")

                # Check if already cancelled
                if cancel_token.is_cancelled:
                    console.print("[yellow]Operation cancelled.[/yellow]")
                    return True

                stdout, stderr, returncode = await cmd_executor.execute(args)

                # Check if cancelled during execution
                if cancel_token.is_cancelled:
                    console.print("[yellow]Operation cancelled.[/yellow]")
                    return True

                if stdout:
                    console.print("\n[bold cyan]Output:[/bold cyan]")
                    console.print(stdout)
                if stderr:
                    console.print("\n[bold red]Errors:[/bold red]")
                    console.print(stderr)
                if returncode != 0:
                    console.print(f"\n[yellow]Exit code: {returncode}[/yellow]")

                # Add command and output to session for context
                context_msg = f"Command: {args}\n\nOutput:\n{stdout}"
                if stderr:
                    context_msg += f"\n\nErrors:\n{stderr}"
                session.add_message("user", context_msg)
            except CommandExecutionError as e:
                console.print(f"[red]Error:[/red] {e}")

    elif command == "/search":
        if not args:
            console.print("[red]Usage: /search <query>[/red]")
        else:
            try:
                console.print(f"[dim]Searching for:[/dim] {args}")

                # Check if already cancelled
                if cancel_token.is_cancelled:
                    console.print("[yellow]Operation cancelled.[/yellow]")
                    return True

                results = await searcher.search(args)

                # Check if cancelled during search
                if cancel_token.is_cancelled:
                    console.print("[yellow]Operation cancelled.[/yellow]")
                    return True

                console.print(f"\n{results}")

                # Add search results to session for context
                session.add_message("user", f"Web search results for '{args}':\n\n{results}")
            except MadisonError as e:
                console.print(f"[red]Error:[/red] {e}")

    elif command == "/save":
        try:
            session_name = args if args else None
            filename = session_manager.save_session(session, session_name)
            console.print(f"[green]✓ Session saved as:[/green] {filename}")
            history_manager.add_entry(f"Saved session: {filename}", "command")
        except MadisonError as e:
            console.print(f"[red]Error:[/red] {e}")

    elif command == "/load":
        if not args:
            console.print("[red]Usage: /load <session_name>[/red]")
        else:
            try:
                loaded_session = session_manager.load_session(args)
                session.messages = loaded_session.messages
                session.system_prompt = loaded_session.system_prompt
                console.print(f"[green]✓ Session loaded:[/green] {args}")
                console.print(f"[dim]Messages: {len(session.get_history())}[/dim]")
                history_manager.add_entry(f"Loaded session: {args}", "command")
            except MadisonError as e:
                console.print(f"[red]Error:[/red] {e}")

    elif command == "/sessions":
        try:
            sessions = session_manager.list_sessions()
            if not sessions:
                console.print("[yellow]No saved sessions yet.[/yellow]")
            else:
                console.print("\n[bold]Saved Sessions:[/bold]")
                for session_info in sessions:
                    console.print(
                        f"  [cyan]{session_info['filename']}[/cyan] - "
                        f"[dim]{session_info['message_count']} messages[/dim] - "
                        f"[dim]{session_info['created_at']}[/dim]"
                    )
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")

    elif command == "/ask":
        if not args:
            console.print("[red]Usage: /ask <strategy|model=MODEL> <prompt>[/red]")
            console.print("[dim]Examples:[/dim]")
            console.print("  /ask thinking What is 2+2?")
            console.print("  /ask planning Write a 5-year plan")
            console.print("  /ask model=gpt-4 Quick question")
            console.print("\n[dim]Available strategies:[/dim]")
            for strategy_name in sorted(config.models.keys()):
                model_name = config.models[strategy_name]
                console.print(f"  [cyan]{strategy_name}[/cyan] → {model_name}")
        else:
            # Parse strategy/model and prompt: /ask <strategy|model=MODEL> <prompt>
            parts = args.split(maxsplit=1)
            if len(parts) == 2:
                strategy_or_model, prompt = parts

                # Determine which model to use
                specific_model = None
                strategy_label = None

                if strategy_or_model.startswith("model="):
                    # Direct model specification
                    specific_model = strategy_or_model[6:]  # Remove "model=" prefix
                    strategy_label = specific_model
                else:
                    # Strategy-based lookup
                    strategy_name = strategy_or_model
                    if strategy_name in config.models:
                        specific_model = config.models[strategy_name]
                        strategy_label = strategy_name
                    else:
                        console.print(f"[red]Unknown strategy: {strategy_name}[/red]")
                        console.print("[dim]Available strategies:[/dim]")
                        for avail_strategy in sorted(config.models.keys()):
                            model_name = config.models[avail_strategy]
                            console.print(f"  [cyan]{avail_strategy}[/cyan] → {model_name}")
                        return True

                try:
                    # Add user message to session
                    session.add_message("user", prompt)

                    # Get response from API with specific model (streaming)
                    console.print(f"\n[bold cyan]Assistant ({strategy_label}):[/bold cyan]", end=" ")

                    response_text = ""
                    async for token in client.chat_stream(
                        messages=session.get_messages(),
                        model=specific_model,
                        temperature=config.temperature,
                        max_tokens=config.max_tokens,
                    ):
                        # Check if cancelled
                        if cancel_token.is_cancelled:
                            console.print("\n[yellow]Response interrupted by user.[/yellow]")
                            break

                        # Write token directly to the console
                        console.file.write(token)
                        console.file.flush()
                        response_text += token

                    console.print()

                    # Only add to session if not cancelled
                    if response_text and not cancel_token.is_cancelled:
                        session.add_message("assistant", response_text)

                    history_manager.add_entry(f"Asked {strategy_label}: {prompt[:50]}...", "query")
                except Exception as e:
                    logger.exception("Error in /ask command")
                    console.print(f"\n[red]Error:[/red] {e}")
            else:
                console.print("[red]Usage: /ask <strategy|model=MODEL> <prompt>[/red]")

    elif command == "/agent":
        selected_agent = await handle_agent_command(args, agent_manager, prompt)
        if selected_agent:
            # Load the agent into the current Agent instance
            agent.load_agent(selected_agent)

    else:
        console.print(f"[red]Unknown command: {command}[/red]")
        console.print(
            "[yellow]Available commands: /read, /write, /exec, /search, /ask, /agent, /clear, /retry, /history, /model, /model-list, /system, /save, /load, /sessions, /quit, /exit[/yellow]"
        )

    return True


def _handle_model_change(
    config: Config,
    new_model: str,
    task_type: str,
    history_manager: HistoryManager,
) -> None:
    """Handle model change with validation and user notification.

    Args:
        config: Configuration object
        new_model: Model to set
        task_type: Task type to set model for
        history_manager: History manager for logging
    """
    # Check if model supports tools
    supports_tools = config.model_supports_tools(new_model)

    if not supports_tools:
        console.print(f"\n[yellow]⚠ Warning:[/yellow] Model [cyan]{new_model}[/cyan] does NOT support tool calling")
        console.print("[dim]This means the agent won't be able to execute commands, read files, etc.[/dim]")
        console.print("[dim]The model will only be available for regular chat conversations.[/dim]\n")

        # Ask for confirmation
        response = console.input("Continue setting this model anyway? [y/N]: ").lower()
        if response not in ("y", "yes"):
            console.print("[yellow]Model change cancelled.[/yellow]")
            return

    # Set the model
    config.set_model(new_model, task_type)
    config.save()

    # Show confirmation
    tool_indicator = "[green]✓ supports tools[/green]" if supports_tools else "[yellow]✗ no tool support[/yellow]"
    console.print(f"[green]✓ Set {task_type} model to:[/green] {new_model} {tool_indicator}")
    history_manager.add_entry(f"Set {task_type} model to {new_model}", "command")


def _is_retryable_error(error_msg: str) -> bool:
    """Check if an error message indicates a retryable error.

    Args:
        error_msg: Error message from API

    Returns:
        bool: True if error is retryable (rate limit, service unavailable, etc.)
    """
    retryable_codes = ["429", "503", "504"]
    return any(code in error_msg for code in retryable_codes)


async def _handle_chat(
    user_input: str,
    session: Session,
    client: OpenRouterClient,
    model: str,
    config: Config,
    file_ops: FileOperations,
    cancel_token: CancellationToken,
    agent: Agent,
):
    """Handle a chat message.

    Args:
        user_input: User input
        session: Session
        client: API client
        model: Model to use
        config: Config
        file_ops: File operations
        cancel_token: Cancellation token
        agent: Agent for intent processing
    """
    # Store the prompt for /retry command
    session.last_user_prompt = user_input

    # Try to process as agent intent first
    try:
        intent_handled, intent_result = await agent.process_intent(user_input)
        if intent_handled and intent_result:
            # Agent found and executed actions
            console.print(f"\n[cyan]Agent Execution Result:[/cyan]\n{intent_result}")
            # Add the result to conversation context
            session.add_message("user", user_input)
            session.add_message("assistant", f"Executed plan:\n{intent_result}")
            return
    except Exception as e:
        logger.debug(f"Agent processing failed (continuing with chat): {e}")
        # If agent fails, continue with regular chat

    # Add user message to session
    session.add_message("user", user_input)

    # Get response from API (streaming)
    try:
        console.print("\n[bold cyan]Assistant:[/bold cyan]", end=" ")

        response_text = ""
        async for token in client.chat_stream(
            messages=session.get_messages(),
            model=config.default_model,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        ):
            # Check if cancelled
            if cancel_token.is_cancelled:
                console.print("\n[yellow]Response interrupted by user.[/yellow]")
                break

            # Write token directly to the console file object
            console.file.write(token)
            console.file.flush()
            response_text += token

        console.print()

        # Only add to session if not cancelled
        if response_text and not cancel_token.is_cancelled:
            # Add assistant response to session
            session.add_message("assistant", response_text)

    except Exception as e:
        logger.exception("Error getting chat response")
        error_msg = str(e)

        # Check if this is a retryable error (rate limit, service unavailable)
        if _is_retryable_error(error_msg):
            console.print(f"\n[red]Transient Error (Rate Limit/Service Unavailable):[/red] {e}")
            console.print("[yellow]The API is temporarily unavailable or rate-limited.[/yellow]")
            console.print("[yellow]Use /retry to resubmit your prompt for another round of retries.[/yellow]")
        else:
            # Non-retryable error
            console.print(f"\n[red]Error:[/red] {e}")


@app.command()
def config(
    action: str = typer.Argument("show", help="Action: show, set, reset, or setup"),
    key: Optional[str] = typer.Argument(None, help="Config key to set"),
    value: Optional[str] = typer.Argument(None, help="Config value"),
):
    """Manage Madison configuration."""
    try:
        if action == "show":
            cfg = Config.load()
            console.print("\n[bold]Current Configuration:[/bold]")
            for key, val in cfg.dict().items():
                if key == "api_key":
                    val = "*" * (len(val) - 4) + val[-4:]
                console.print(f"  {key}: {val}")

        elif action == "set":
            if not key or not value:
                console.print("[red]Usage: madison config set <key> <value>[/red]")
                sys.exit(1)

            cfg = Config.load()
            if hasattr(cfg, key):
                # Special handling for model settings - validate tool support
                if key == "default_model":
                    supports_tools = cfg.model_supports_tools(value)
                    if not supports_tools:
                        console.print(f"\n[yellow]⚠ Warning:[/yellow] Model [cyan]{value}[/cyan] does NOT support tool calling")
                        console.print("[dim]This means the agent won't be able to execute commands, read files, etc.[/dim]")
                        response = console.input("Continue? [y/N]: ").lower()
                        if response not in ("y", "yes"):
                            console.print("[yellow]Change cancelled.[/yellow]")
                            return

                setattr(cfg, key, value)
                cfg.save()
                console.print(f"[green]Set {key} = {value}[/green]")
            else:
                console.print(f"[red]Unknown config key: {key}[/red]")

        elif action == "reset":
            Config.config_file().unlink(missing_ok=True)
            console.print("[green]Configuration reset.[/green]")

        elif action == "setup":
            run_setup_wizard()

        else:
            console.print(f"[red]Unknown action: {action}[/red]")
            console.print("[yellow]Available actions: show, set, reset, setup[/yellow]")

    except ConfigError as e:
        console.print(f"[red]Configuration Error:[/red] {e}")
        sys.exit(1)


def main():
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
