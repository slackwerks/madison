"""Abstract interface for UI implementations (CLI, TUI, etc.)."""

from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional


class UIHandler(ABC):
    """Abstract base class for UI implementations.

    Defines the interface that all UI implementations (CLI, Textual TUI, web, etc.)
    must implement to integrate with Madison's core application logic.
    """

    @abstractmethod
    async def request_input(self) -> str:
        """Request user input.

        Returns:
            str: User input string

        Raises:
            InterruptedError: If user signals EOF (Ctrl+D) or requests exit
        """
        pass

    @abstractmethod
    def display_message(
        self,
        role: str,
        content: str,
        metadata: Optional[dict] = None,
    ) -> None:
        """Display a message in the conversation.

        Args:
            role: Message role (user, assistant, system)
            content: Message content
            metadata: Optional metadata (agent info, model, etc.)
        """
        pass

    @abstractmethod
    def display_plain(self, content: str) -> None:
        """Display plain text without timestamp or labels.

        Args:
            content: Text to display
        """
        pass

    @abstractmethod
    def display_operation(
        self,
        operation_type: str,
        status: str,
        details: Optional[str] = None,
    ) -> None:
        """Display an operation status update.

        Args:
            operation_type: Type of operation (exec, search, read, write, plan, etc.)
            status: Status message or description
            details: Optional detailed information
        """
        pass

    @abstractmethod
    def display_error(self, error_message: str) -> None:
        """Display an error message.

        Args:
            error_message: Error message to display
        """
        pass

    @abstractmethod
    def display_info(self, info_message: str) -> None:
        """Display an informational message.

        Args:
            info_message: Info message to display
        """
        pass

    @abstractmethod
    def display_warning(self, warning_message: str) -> None:
        """Display a warning message.

        Args:
            warning_message: Warning message to display
        """
        pass

    @abstractmethod
    def display_panel(self, content: str, title: str = "", style: str = "") -> None:
        """Display formatted content in a panel.

        Args:
            content: Content to display
            title: Optional panel title
            style: Optional style (color scheme, etc.)
        """
        pass

    @abstractmethod
    def start_streaming(self, header: str) -> None:
        """Start a streaming response block.

        Args:
            header: Header to display before streaming content
        """
        pass

    @abstractmethod
    def stream_token(self, token: str) -> None:
        """Write a token to the current streaming block.

        Args:
            token: Token to write
        """
        pass

    @abstractmethod
    def end_streaming(self) -> None:
        """End the current streaming block."""
        pass

    @abstractmethod
    async def prompt_user(self, prompt: str, options: Optional[list] = None) -> str:
        """Prompt user for confirmation or choice.

        Args:
            prompt: Prompt message
            options: Optional list of options to choose from

        Returns:
            str: User's response
        """
        pass

    @abstractmethod
    def clear_screen(self) -> None:
        """Clear the display."""
        pass

    @abstractmethod
    def set_status(self, status: str) -> None:
        """Set status bar content.

        Args:
            status: Status message
        """
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Clean up and shutdown the UI handler."""
        pass
