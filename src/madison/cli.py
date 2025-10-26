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
from madison.core.session import Session
from madison.exceptions import ConfigError, FileOperationError
from madison.tools.file_ops import FileOperations

# Setup logging
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = typer.Typer(
    name="madison",
    help="A Python CLI for interacting with OpenRouter models",
)
console = Console()


def setup_logging(verbose: bool = False):
    """Setup logging level."""
    if verbose:
        logging.getLogger("madison").setLevel(logging.DEBUG)
    else:
        logging.getLogger("madison").setLevel(logging.WARNING)


@app.command()
def chat(
    model: Optional[str] = typer.Option(
        None, "--model", "-m", help="OpenRouter model to use"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
):
    """Start an interactive chat session with an OpenRouter model."""
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
            f"Commands: [cyan]@read[/cyan], [cyan]@write[/cyan], [cyan]@clear[/cyan], "
            f"[cyan]@history[/cyan], [cyan]@model[/cyan], [cyan]@quit[/cyan]",
            expand=False,
        )
    )

    async with OpenRouterClient(config.api_key, timeout=config.timeout) as client:
        while True:
            try:
                # Get user input
                user_input = await _get_user_input()

                if not user_input.strip():
                    continue

                # Handle special commands
                if await _handle_commands(user_input, session, file_ops, config, client, model):
                    continue

                # Regular chat
                await _handle_chat(
                    user_input, session, client, model, config, file_ops
                )

            except KeyboardInterrupt:
                console.print("\n[yellow]Interrupted. Type '@quit' to exit.[/yellow]")
            except Exception as e:
                logger.exception("Error in REPL loop")
                console.print(f"[red]Error:[/red] {e}")


async def _get_user_input() -> str:
    """Get user input asynchronously with a nice bar-based prompt.

    Returns:
        str: User input
    """
    from rich.text import Text

    # Display top bar
    console.print()
    console.print("─" * console.width)

    # Get input
    loop = asyncio.get_event_loop()
    user_input = await loop.run_in_executor(None, lambda: console.input("> ").strip())

    # Display bottom bar with commands
    console.print("─" * console.width)
    console.print(
        "[dim]Commands:[/dim] "
        "[cyan]@read[/cyan] [cyan]@write[/cyan] [cyan]@clear[/cyan] "
        "[cyan]@history[/cyan] [cyan]@model[/cyan] [cyan]@system[/cyan] [cyan]@quit[/cyan]",
        style="dim",
    )

    return user_input


async def _handle_commands(
    user_input: str,
    session: Session,
    file_ops: FileOperations,
    config: Config,
    client: OpenRouterClient,
    model: str,
) -> bool:
    """Handle special commands.

    Args:
        user_input: User input
        session: Session
        file_ops: File operations
        config: Config
        client: API client
        model: Current model

    Returns:
        bool: Whether a command was handled
    """
    if not user_input.startswith("@"):
        return False

    parts = user_input.split(maxsplit=1)
    command = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""

    if command == "@quit":
        console.print("[yellow]Goodbye![/yellow]")
        sys.exit(0)

    elif command == "@clear":
        session.clear()
        console.print("[green]Conversation cleared.[/green]")

    elif command == "@history":
        history = session.get_history()
        if not history:
            console.print("[yellow]No conversation history yet.[/yellow]")
        else:
            console.print("\n[bold]Conversation History:[/bold]")
            for msg in history:
                role = f"[cyan]{msg.role.upper()}[/cyan]"
                console.print(f"{role}: {msg.content[:100]}")

    elif command == "@read":
        if not args:
            console.print("[red]Usage: @read <filepath>[/red]")
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

    elif command == "@write":
        console.print("[yellow]@write command requires file path and content.[/yellow]")
        console.print("[yellow]Usage: @write <filepath>[/yellow]")
        console.print("[yellow]Then paste your content and press Ctrl+D (or Ctrl+Z on Windows)[/yellow]")
        # For now, just acknowledge
        # Full implementation would require reading multi-line input

    elif command == "@model":
        if not args:
            console.print(f"[cyan]Current model:[/cyan] {model}")
        else:
            # TODO: Implement model switching
            console.print("[yellow]Model switching not yet implemented.[/yellow]")

    elif command == "@system":
        if not args:
            console.print(f"[cyan]Current system prompt:[/cyan]\n{session.system_prompt}")
        else:
            session.messages[0].content = args
            console.print("[green]System prompt updated.[/green]")

    else:
        console.print(f"[red]Unknown command: {command}[/red]")
        console.print(
            "[yellow]Available commands: @read, @write, @clear, @history, @model, @system, @quit[/yellow]"
        )

    return True


async def _handle_chat(
    user_input: str,
    session: Session,
    client: OpenRouterClient,
    model: str,
    config: Config,
    file_ops: FileOperations,
):
    """Handle a chat message.

    Args:
        user_input: User input
        session: Session
        client: API client
        model: Model to use
        config: Config
        file_ops: File operations
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
            # Write token directly to the console file object
            console.file.write(token)
            console.file.flush()
            response_text += token

        console.print()

        # Add assistant response to session
        session.add_message("assistant", response_text)

    except Exception as e:
        logger.exception("Error getting chat response")
        console.print(f"\n[red]Error:[/red] {e}")


@app.command()
def config(
    action: str = typer.Argument("show", help="Action: show, set, or reset"),
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

        else:
            console.print(f"[red]Unknown action: {action}[/red]")

    except ConfigError as e:
        console.print(f"[red]Configuration Error:[/red] {e}")
        sys.exit(1)


def main():
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
