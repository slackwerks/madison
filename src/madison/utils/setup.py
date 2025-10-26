"""Interactive setup wizard for Madison configuration."""

import logging
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from madison.core.config import Config

logger = logging.getLogger(__name__)
console = Console()


def run_setup_wizard() -> Config:
    """Run interactive configuration setup wizard.

    Returns:
        Config: Configured settings
    """
    console.print(
        Panel(
            "[bold cyan]Madison Setup Wizard[/bold cyan]\n\n"
            "Let's configure Madison for OpenRouter integration.",
            expand=False,
        )
    )

    # API Key
    console.print()
    console.print("[bold]Step 1: OpenRouter API Key[/bold]")
    console.print(
        "[dim]Get your API key from https://openrouter.ai/keys[/dim]"
    )
    api_key = Prompt.ask(
        "Enter your OpenRouter API key",
        password=True,
    )

    # Model selection
    console.print()
    console.print("[bold]Step 2: Model Configuration[/bold]")
    console.print(
        "[dim]Common options: openrouter/auto, gpt-4, gpt-3.5-turbo, claude-3-sonnet[/dim]"
    )
    default_model = Prompt.ask(
        "Enter default model",
        default="openrouter/auto",
    )

    # Task-specific models
    models = {"default": default_model}
    console.print()
    if Confirm.ask(
        "Would you like to configure task-specific models (e.g., thinking)?",
        default=False,
    ):
        thinking_model = Prompt.ask(
            "Enter thinking model (or press Enter for same as default)",
            default=default_model,
        )
        if thinking_model:
            models["thinking"] = thinking_model

    # System prompt
    console.print()
    console.print("[bold]Step 3: System Prompt[/bold]")
    console.print("[dim]The system prompt defines how the AI behaves[/dim]")
    system_prompt = Prompt.ask(
        "Enter system prompt",
        default="You are a helpful assistant.",
    )

    # Temperature
    console.print()
    console.print("[bold]Step 4: Temperature[/bold]")
    console.print(
        "[dim]Lower values are more deterministic, higher are more creative (0-2)[/dim]"
    )
    while True:
        try:
            temp_str = Prompt.ask("Enter temperature", default="0.7")
            temperature = float(temp_str)
            if not (0 <= temperature <= 2):
                console.print("[red]Temperature must be between 0 and 2[/red]")
                continue
            break
        except ValueError:
            console.print("[red]Please enter a valid number[/red]")

    # Timeout
    console.print()
    console.print("[bold]Step 5: Request Timeout[/bold]")
    console.print("[dim]How long to wait for API responses (seconds)[/dim]")
    while True:
        try:
            timeout_str = Prompt.ask("Enter timeout", default="30")
            timeout = int(timeout_str)
            if timeout < 1:
                console.print("[red]Timeout must be at least 1 second[/red]")
                continue
            break
        except ValueError:
            console.print("[red]Please enter a valid number[/red]")

    # History size
    console.print()
    console.print("[bold]Step 6: Conversation History Size[/bold]")
    console.print("[dim]How many messages to keep in conversation (for context)[/dim]")
    while True:
        try:
            history_str = Prompt.ask("Enter history size", default="50")
            history_size = int(history_str)
            if history_size < 1:
                console.print("[red]History size must be at least 1[/red]")
                continue
            break
        except ValueError:
            console.print("[red]Please enter a valid number[/red]")

    # Create config
    config = Config(
        api_key=api_key,
        default_model=default_model,
        models=models,
        system_prompt=system_prompt,
        temperature=temperature,
        timeout=timeout,
        history_size=history_size,
    )

    # Save config
    console.print()
    if Confirm.ask("Save configuration?", default=True):
        try:
            config.save()
            config_file = Config.config_file()
            console.print(
                f"[green]✓ Configuration saved to {config_file}[/green]"
            )
        except Exception as e:
            console.print(f"[red]Failed to save configuration: {e}[/red]")
            return config

    # Summary
    console.print()
    models_summary = "\n".join(
        f"  {task}: {model}" for task, model in sorted(config.models.items())
    )
    console.print(
        Panel(
            "[bold green]Setup Complete![/bold green]\n\n"
            f"Models:\n{models_summary}\n"
            f"Temperature: {config.temperature}\n"
            f"Timeout: {config.timeout}s\n"
            f"History Size: {config.history_size}\n\n"
            "[dim]You can now run 'madison' to start chatting![/dim]",
            expand=False,
        )
    )

    return config
