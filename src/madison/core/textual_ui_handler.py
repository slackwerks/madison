"""Textual UI handler implementation for Madison."""

from typing import Optional, TYPE_CHECKING, Dict
from datetime import datetime

from rich.text import Text as RichText

from madison.core.ui_interface import UIHandler
from madison.core.operation_tracker import OperationContext

if TYPE_CHECKING:
    from textual.app import App


class TextualUIHandler(UIHandler):
    """Textual-based UI handler for the Madison TUI."""

    def __init__(self, app: "App"):
        """Initialize the Textual UI handler.

        Args:
            app: The Textual application instance
        """
        self.app = app
        self.split_screen = getattr(app, "split_screen", None)
        self._streaming_active = False
        self._streaming_buffer = ""
        self._current_operations: Dict[str, OperationContext] = {}

    async def request_input(self) -> str:
        """Request user input from the Textual interface.

        This is handled asynchronously by the Textual app through action_submit_input().
        This method returns the next input when available.
        """
        # Create a future that will be resolved when input is submitted
        import asyncio

        # This is a placeholder - actual implementation depends on how the Textual app
        # communicates input to the handler. For now, we'll use the app's message queue
        if not hasattr(self.app, "_input_queue"):
            self.app._input_queue = asyncio.Queue()

        return await self.app._input_queue.get()

    def display_plain(self, content: str) -> None:
        """Display plain text without timestamp or labels."""
        if not self.split_screen:
            return

        self.split_screen.add_left_message(content)

    def display_message(
        self,
        role: str,
        content: str,
        metadata: Optional[dict] = None,
    ) -> None:
        """Display a conversation message."""
        if not self.split_screen:
            return

        timestamp = datetime.now().strftime("%H:%M:%S")
        message_parts = [f"[dim]{timestamp}[/dim]"]

        if role == "user":
            message_parts.append("[cyan]USER[/cyan]")
        elif role == "assistant":
            message_parts.append("[green]ASSISTANT[/green]")
        else:
            message_parts.append(f"[yellow]{role.upper()}[/yellow]")

        # Add metadata if provided
        if metadata:
            if "agent" in metadata:
                message_parts.append(f"({metadata['agent']})")
            if "model" in metadata:
                message_parts.append(f"— {metadata['model']}")

        # Add content preview
        content_preview = content[:100]
        if len(content) > 100:
            content_preview += "..."

        message = " ".join(message_parts) + f": {content_preview}"
        self.split_screen.add_left_message(message)

    def display_operation(
        self,
        operation_type: str,
        status: str,
        details: Optional[str] = None,
    ) -> None:
        """Display an operation status."""
        if not self.split_screen:
            return

        timestamp = datetime.now().strftime("%H:%M:%S")

        # Color code by operation type
        type_colors = {
            "exec": "[yellow]",
            "search": "[yellow]",
            "read": "[cyan]",
            "write": "[cyan]",
            "plan": "[magenta]",
            "complete": "[green]",
            "status": "[blue]",
            "model-list": "[blue]",
        }
        color = type_colors.get(operation_type, "[white]")
        close_color = "[/white]"
        if color != "[white]":
            close_color = color.replace("[", "[/")

        message = f"[dim]{timestamp}[/dim] {color}{operation_type.upper()}{close_color}: {status}"
        if details:
            message += f"\n[dim]  {details}[/dim]"

        self.split_screen.add_left_message(message)

    def start_operation(self, operation_type: str, description: str) -> OperationContext:
        """Start tracking an operation.

        Args:
            operation_type: Type of operation (read, exec, search, etc.)
            description: Human-readable description (file path, command, etc.)

        Returns:
            OperationContext: Context object to track this operation
        """
        op_id = f"{operation_type}:{description}"
        context = OperationContext(operation_type, description)
        self._current_operations[op_id] = context

        # Don't display yet - wait for complete_operation() to show the full result
        return context

    def complete_operation(self, context: OperationContext) -> None:
        """Complete and finalize an operation.

        Args:
            context: The OperationContext to complete
        """
        context.complete()
        op_id = f"{context.operation_type}:{context.description}"

        if op_id in self._current_operations:
            del self._current_operations[op_id]

        # Display the operation with all details once at the end
        if self.split_screen:
            self.split_screen.add_left_message(f"[cyan]{context.format()}[/cyan]")

    def display_error(self, error_message: str) -> None:
        """Display an error message."""
        if not self.split_screen:
            return

        timestamp = datetime.now().strftime("%H:%M:%S")
        message = f"[dim]{timestamp}[/dim] [red]ERROR[/red]: {error_message}"
        self.split_screen.add_left_message(message)

    def display_info(self, info_message: str) -> None:
        """Display an informational message."""
        if not self.split_screen:
            return

        timestamp = datetime.now().strftime("%H:%M:%S")
        message = f"[dim]{timestamp}[/dim] [cyan]INFO[/cyan]: {info_message}"
        self.split_screen.add_left_message(message)

    def display_warning(self, warning_message: str) -> None:
        """Display a warning message."""
        if not self.split_screen:
            return

        timestamp = datetime.now().strftime("%H:%M:%S")
        message = f"[dim]{timestamp}[/dim] [yellow]WARNING[/yellow]: {warning_message}"
        self.split_screen.add_left_message(message)

    def display_panel(self, content: str, title: str = "", style: str = "") -> None:
        """Display formatted content on the right pane (without panel wrapper)."""
        if not self.split_screen:
            return

        # Display content directly without wrapping in a panel
        self.split_screen.add_right_content(content)

    def start_streaming(self, header: str) -> None:
        """Start a streaming response block."""
        if not self.split_screen:
            return

        self._streaming_active = True
        self._streaming_buffer = ""

        # Display RESPONSE status in left pane
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.split_screen.add_left_message(f"[dim]{timestamp}[/dim] [green]RESPONSE[/green]")

        # Start streaming in right pane with header
        self.split_screen.start_streaming(header)

    def stream_token(self, token: str) -> None:
        """Write a token to the current streaming block."""
        if self._streaming_active:
            self._streaming_buffer += token
            # Stream token directly to right pane for real-time display
            if self.split_screen:
                self.split_screen.stream_token(token)

    def end_streaming(self) -> None:
        """End the current streaming block."""
        if self._streaming_active and self.split_screen:
            # End streaming in right pane
            self.split_screen.end_streaming()

            self._streaming_active = False
            self._streaming_buffer = ""

    async def prompt_user(self, prompt: str, options: Optional[list] = None) -> str:
        """Prompt user for confirmation or choice.

        For Textual, this displays a message and waits for input.
        """
        # Display prompt in both panes
        self.display_info(prompt)

        if options:
            self.display_info(f"Options: {', '.join(options)}")

        # For now, return empty string - in a full implementation,
        # this would wait for the next user input and validate against options
        return ""

    def clear_screen(self) -> None:
        """Clear the display."""
        if not self.split_screen:
            return

        self.split_screen.clear_left()
        self.split_screen.clear_right()

    def set_status(self, status: str) -> None:
        """Set status bar content.

        For Textual, this could update a status bar widget.
        """
        # Placeholder for status bar update
        pass

    async def shutdown(self) -> None:
        """Clean up and shutdown the UI handler."""
        if self.app:
            self.app.exit()
