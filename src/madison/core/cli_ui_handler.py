"""CLI UI handler implementation for Madison."""

import sys
from typing import Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax

from madison.core.ui_interface import UIHandler
from madison.utils.input_handler import InterruptedError, MadisonPrompt


class CLIUIHandler(UIHandler):
    """Console-based UI handler using Rich for formatting."""

    def __init__(self):
        """Initialize the CLI UI handler."""
        self.console = Console()
        self.prompt = MadisonPrompt()
        self._streaming_active = False

    async def request_input(self) -> str:
        """Request user input from the console."""
        return await self.prompt.prompt_async()

    def display_plain(self, content: str) -> None:
        """Display plain text without formatting."""
        self.console.print(content)

    def display_message(
        self,
        role: str,
        content: str,
        metadata: Optional[dict] = None,
    ) -> None:
        """Display a conversation message."""
        role_formatted = f"[cyan]{role.upper()}[/cyan]"
        self.console.print(f"{role_formatted}: {content[:100]}")

    def display_operation(
        self,
        operation_type: str,
        status: str,
        details: Optional[str] = None,
    ) -> None:
        """Display an operation status."""
        op_formatted = f"[yellow]{operation_type.upper()}[/yellow]"
        self.console.print(f"{op_formatted}: {status}")
        if details:
            self.console.print(f"[dim]{details}[/dim]")

    def start_operation(self, operation_type: str, description: str):
        """Start tracking an operation (CLI stub - just returns None)."""
        from madison.core.operation_tracker import OperationContext
        return OperationContext(operation_type, description)

    def complete_operation(self, context) -> None:
        """Complete an operation (CLI stub - prints the operation)."""
        self.console.print(context.format())

    def display_error(self, error_message: str) -> None:
        """Display an error message."""
        self.console.print(f"[red]Error:[/red] {error_message}")

    def display_info(self, info_message: str) -> None:
        """Display an informational message."""
        self.console.print(f"[dim]{info_message}[/dim]")

    def display_warning(self, warning_message: str) -> None:
        """Display a warning message."""
        self.console.print(f"[yellow]{warning_message}[/yellow]")

    def display_panel(self, content: str, title: str = "", style: str = "") -> None:
        """Display formatted content in a panel."""
        # Try to detect if content is code and highlight it
        panel_content = content
        if content.startswith("```"):
            # Extract code block
            try:
                language = content[3:content.index("\n")]
                code = content[content.index("\n") + 1 : content.rindex("```")]
                panel_content = Syntax(code, language, theme="monokai", line_numbers=True)
            except Exception:
                panel_content = content
        else:
            panel_content = Markdown(content)

        panel = Panel(panel_content, title=title, expand=False)
        self.console.print(panel)

    def start_streaming(self, header: str) -> None:
        """Start a streaming response block."""
        self.console.print(header, end=" ")
        self._streaming_active = True

    def stream_token(self, token: str) -> None:
        """Write a token to the current streaming block."""
        if self._streaming_active:
            self.console.file.write(token)
            self.console.file.flush()

    def end_streaming(self) -> None:
        """End the current streaming block."""
        if self._streaming_active:
            self.console.print()
            self._streaming_active = False

    async def prompt_user(self, prompt: str, options: Optional[list] = None) -> str:
        """Prompt user for confirmation or choice."""
        if options:
            options_str = "/".join(options)
            return self.console.input(f"{prompt} [{options_str}]: ").strip()
        else:
            return self.console.input(f"{prompt}: ").strip()

    def clear_screen(self) -> None:
        """Clear the console screen."""
        self.console.clear()

    def set_status(self, status: str) -> None:
        """Set status bar content."""
        # CLI doesn't have a persistent status bar
        pass

    async def shutdown(self) -> None:
        """Clean up and shutdown the UI handler."""
        # Nothing special needed for CLI
        pass
