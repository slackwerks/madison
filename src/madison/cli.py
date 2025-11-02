"""Main CLI interface for Madison."""

import asyncio
import logging
import sys
from typing import Optional

import typer
from rich.console import Console

from madison.core.application import MadisonApplication
from madison.core.cli_ui_handler import CLIUIHandler
from madison.core.config import Config
from madison.core.tui_launcher import launch_tui
from madison.exceptions import ConfigError
from madison.utils.setup import run_setup_wizard

# Setup logging to file
def _setup_file_logging():
    """Setup logging to ./.madison/madison.log (local to current directory)"""
    from pathlib import Path
    log_dir = Path(".madison")
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "madison.log"

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),
        ],
    )

_setup_file_logging()
logger = logging.getLogger(__name__)

app = typer.Typer(
    name="madison",
    help="A Python CLI for interacting with OpenRouter models",
    invoke_without_command=True,
)
console = Console()


def setup_logging(verbose: bool = False):
    """Setup logging level (verbose flag controls console output if needed)."""
    # Logging already goes to file at DEBUG level
    # This flag could be used for future console logging if desired
    if verbose:
        logging.getLogger("madison").setLevel(logging.DEBUG)
    else:
        logging.getLogger("madison").setLevel(logging.INFO)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    model: Optional[str] = typer.Option(
        None, "--model", "-m", help="OpenRouter model to use"
    ),
    ui: str = typer.Option(
        "tui",
        "--ui",
        help="UI mode: 'tui' for Textual TUI (default), 'cli' for command-line interface",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
):
    """Madison - OpenRouter CLI. Start an interactive chat session by default."""
    # If a subcommand was invoked, don't run chat
    if ctx.invoked_subcommand is not None:
        return

    # Otherwise, run chat
    setup_logging(verbose)

    # Validate UI option
    if ui not in ("cli", "tui"):
        console.print(f"[red]Invalid UI mode: {ui}[/red]")
        console.print("[dim]Available modes: cli, tui[/dim]")
        sys.exit(1)

    try:
        # Load configuration
        config = Config.load()
        model = model or config.default_model

        # Launch appropriate UI
        if ui == "tui":
            _launch_tui(config, model)
        else:
            # CLI mode (default)
            ui_handler = CLIUIHandler()
            app_instance = MadisonApplication(config, ui_handler, model)
            asyncio.run(_run_app(app_instance))

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


def _launch_tui(config: Config, model: Optional[str] = None) -> None:
    """Launch the Textual TUI mode.

    Args:
        config: Madison configuration
        model: Model to use
    """
    try:
        launch_tui(config, model)
    except ImportError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        # User interrupted - just exit cleanly
        pass
    except Exception as e:
        logger.exception("Error in TUI mode")
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


async def _run_app(app_instance: MadisonApplication) -> None:
    """Initialize and run the Madison application.

    Args:
        app_instance: The Madison application instance
    """
    await app_instance.initialize()
    await app_instance.run()


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
