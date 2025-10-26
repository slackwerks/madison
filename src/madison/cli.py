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
            f"Model: {model}\n\n"
            f"Commands: [cyan]/read[/cyan], [cyan]/write[/cyan], [cyan]/exec[/cyan], "
            f"[cyan]/search[/cyan], [cyan]/clear[/cyan], [cyan]/history[/cyan], "
            f"[cyan]/save[/cyan], [cyan]/load[/cyan], [cyan]/sessions[/cyan], "
            f"[cyan]/model[/cyan], [cyan]/system[/cyan], [cyan]/quit[/cyan] ([cyan]/exit[/cyan])",
            expand=False,
        )
    )

    # Initialize tools and managers
    cmd_executor = CommandExecutor(timeout=config.timeout)
    searcher = WebSearcher(max_results=5)
    session_manager = SessionManager()
    history_manager = HistoryManager()
    prompt = MadisonPrompt()

    async with OpenRouterClient(config.api_key, timeout=config.timeout) as client:
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
                    user_input, session, file_ops, config, client, model, cmd_executor, searcher, cancel_token, session_manager, history_manager
                ):
                    continue

                # Regular chat
                await _handle_chat(
                    user_input, session, client, model, config, file_ops, cancel_token
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
            console.print(f"[cyan]Current model:[/cyan] {model}")
        else:
            # TODO: Implement model switching
            console.print("[yellow]Model switching not yet implemented.[/yellow]")

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

    else:
        console.print(f"[red]Unknown command: {command}[/red]")
        console.print(
            "[yellow]Available commands: /read, /write, /exec, /search, /clear, /history, /model, /system, /save, /load, /sessions, /quit, /exit[/yellow]"
        )

    return True


async def _handle_chat(
    user_input: str,
    session: Session,
    client: OpenRouterClient,
    model: str,
    config: Config,
    file_ops: FileOperations,
    cancel_token: CancellationToken,
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
    """
    # Add user message to session
    session.add_message("user", user_input)

    # Get response from API (streaming)
    try:
        console.print("\n[bold cyan]Assistant:[/bold cyan]", end=" ")

        response_text = ""
        async for token in client.chat_stream(
            messages=session.get_messages(),
            model=model,
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
