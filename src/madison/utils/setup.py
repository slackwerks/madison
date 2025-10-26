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
    console.print("[bold]Step 2: Function-Based Model Configuration[/bold]")
    console.print(
        "[dim]Madison uses 'functions' to organize different models for different tasks.[/dim]"
    )
    console.print(
        "[dim]For example, you might use gpt-4 for 'thinking' and gpt-3.5 for 'summarization'.[/dim]"
    )
    console.print(
        "[dim]Common options: openrouter/auto, gpt-4, gpt-3.5-turbo, claude-3-sonnet, claude-opus[/dim]"
    )

    default_model = Prompt.ask(
        "Enter default model (used when no specific function is requested)",
        default="openrouter/auto",
    )

    # Function-specific models
    models = {"default": default_model}
    console.print()
    console.print("[dim]You can now register additional functions with specific models.[/dim]")
    console.print("[dim]For example: 'thinking' for deep reasoning, 'planning' for strategy, etc.[/dim]")

    # Add some common function suggestions
    suggested_functions = ["thinking", "planning", "summarization", "analysis"]
    for suggested_func in suggested_functions:
        if Confirm.ask(
            f"Configure a '{suggested_func}' function?",
            default=suggested_func == "thinking",  # thinking is suggested by default
        ):
            func_model = Prompt.ask(
                f"Enter model for '{suggested_func}' (or press Enter for same as default)",
                default=default_model,
            )
            if func_model and func_model != default_model:
                models[suggested_func] = func_model
            elif func_model:
                models[suggested_func] = func_model

    # Allow adding custom functions
    console.print()
    while Confirm.ask("Add a custom function?", default=False):
        custom_func = Prompt.ask("Function name (e.g., 'bork', 'analysis')")
        if custom_func and custom_func not in models:
            custom_model = Prompt.ask(
                f"Enter model for '{custom_func}'",
                default=default_model,
            )
            if custom_model:
                models[custom_func] = custom_model
        elif custom_func in models:
            console.print(f"[yellow]Function '{custom_func}' already configured.[/yellow]")

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

    # Retry configuration
    console.print()
    console.print("[bold]Step 7: Retry Configuration[/bold]")
    console.print("[dim]For handling rate limits and temporary API errors[/dim]")

    while True:
        try:
            max_retries_str = Prompt.ask(
                "Max retries on transient errors (429, 503, 504)",
                default="3"
            )
            max_retries = int(max_retries_str)
            if max_retries < 0:
                console.print("[red]Max retries must be >= 0[/red]")
                continue
            break
        except ValueError:
            console.print("[red]Please enter a valid number[/red]")

    while True:
        try:
            delay_str = Prompt.ask("Initial retry delay in seconds", default="1.0")
            retry_initial_delay = float(delay_str)
            if retry_initial_delay < 0.1:
                console.print("[red]Initial delay must be >= 0.1 seconds[/red]")
                continue
            break
        except ValueError:
            console.print("[red]Please enter a valid number[/red]")

    while True:
        try:
            backoff_str = Prompt.ask(
                "Retry backoff factor (delay multiplier per attempt)",
                default="2.0"
            )
            retry_backoff_factor = float(backoff_str)
            if retry_backoff_factor < 1.0:
                console.print("[red]Backoff factor must be >= 1.0[/red]")
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
        max_retries=max_retries,
        retry_initial_delay=retry_initial_delay,
        retry_backoff_factor=retry_backoff_factor,
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
        f"  [cyan]{func}[/cyan] → {model}" for func, model in sorted(config.models.items())
    )
    console.print(
        Panel(
            "[bold green]Setup Complete![/bold green]\n\n"
            f"Registered Functions:\n{models_summary}\n"
            f"Temperature: {config.temperature}\n"
            f"Timeout: {config.timeout}s\n"
            f"History Size: {config.history_size}\n"
            f"Retry Config: max={config.max_retries}, delay={config.retry_initial_delay}s, backoff={config.retry_backoff_factor}x\n\n"
            "[dim]Try: /ask thinking 'What is 2+2?' to test![/dim]\n"
            "[dim]Or: madison to start chatting[/dim]",
            expand=False,
        )
    )

    return config
