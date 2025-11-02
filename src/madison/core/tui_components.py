"""
Textual-based split-screen UI components for Madison.

Left pane: Scrollable message log + input field
Right pane: Scrollable generated content
"""

from typing import List
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import TextArea, Static
from rich.text import Text as RichText
from rich.console import RenderableType


class InputTextArea(TextArea):
    """Custom TextArea that handles Enter for submission and Ctrl+Enter for newlines."""

    def set_text_safe(self, text: str) -> None:
        """Safely set the text content of the input area.

        Sets text safely by replacing the entire document content.
        """
        try:
            # Clear current content and set new text
            self.text = text
        except Exception:
            # If that fails, try to select all and replace
            try:
                self.select_all()
                if self.selected_text is not None:
                    # Delete selected text
                    self.delete_line()
                self.text = text
            except Exception:
                # Last resort: just try to set it anyway
                pass

    async def _on_key(self, event):
        """Override to intercept Enter for submission and Ctrl+Enter for newlines."""
        if event.key == "enter":
            # Submit the input
            self.app.action_submit_input()
            event.prevent_default()
        elif event.key == "ctrl+j":
            # Ctrl+Enter inserts a newline
            self.insert("\n")
            event.prevent_default()
        elif event.key == "up":
            # Navigate to previous history item
            if hasattr(self.app, "navigate_history"):
                self.app.navigate_history(-1)
                event.prevent_default()
            else:
                await super()._on_key(event)
        elif event.key == "down":
            # Navigate to next history item
            if hasattr(self.app, "navigate_history"):
                self.app.navigate_history(1)
                event.prevent_default()
            else:
                await super()._on_key(event)
        else:
            # Let parent handle all other keys
            await super()._on_key(event)


class DividerWidget(Static):
    """A vertical divider between panes."""

    def render(self) -> RenderableType:
        # Get the widget's height
        height = self.size.height if self.size else 1
        # Create a vertical line of the appropriate height
        lines = ["│"] * height
        return RichText("\n".join(lines), style="dim")


class MessageLog(Static):
    """Container for messages in the left pane."""

    def __init__(self, id: str = "message_log"):
        super().__init__(id=id)
        self.messages: List[str] = []

    def add_message(self, content: str) -> None:
        """Add a message to the log."""
        self.messages.append(content)
        self.update_display()

    def update_display(self) -> None:
        """Update the display with all messages."""
        output = "\n".join(self.messages)
        # Parse Rich markup in the output
        text = RichText.from_markup(output)
        self.update(text)

    def clear(self) -> None:
        """Clear all messages."""
        self.messages.clear()
        self.update("")

    def render(self) -> RenderableType:
        """Render the message log."""
        return RichText.from_markup("\n".join(self.messages))


class ContentPane(Static):
    """Container for generated content in the right pane."""

    def __init__(self, id: str = "content_pane"):
        super().__init__(id=id)
        self.content_items: List[RenderableType] = []
        self._current_streaming: Optional[str] = None

    def add_content(self, content: RenderableType) -> None:
        """Add a content item to the pane."""
        self.content_items.append(content)
        self._current_streaming = None  # Clear streaming mode when adding static content
        self.update_display()

    def start_streaming(self, header: str = "") -> None:
        """Start a streaming response block.

        Args:
            header: Optional header text to display before streaming content
        """
        self._current_streaming = header if header else ""
        self.update_display()

    def stream_token(self, token: str) -> None:
        """Add a token to the current streaming block.

        Args:
            token: Token to add
        """
        if self._current_streaming is not None:
            self._current_streaming += token
            self.update_display()

    def end_streaming(self) -> None:
        """End the current streaming block and save it as content."""
        if self._current_streaming is not None:
            # Save the streaming content as a regular content item
            self.content_items.append(self._current_streaming)
            self._current_streaming = None
            self.update_display()

    def update_display(self) -> None:
        """Update the display with all content."""
        if not self.content_items and self._current_streaming is None:
            self.update("")
            return

        output_parts = []

        # Add regular content items
        for item in self.content_items:
            output_parts.append(str(item))

        # Add streaming content if active (with indicator)
        if self._current_streaming is not None:
            if output_parts:
                output_parts.append("")  # Blank line separator
            # Add streaming indicator
            output_parts.append("[dim]⏳ Generating...[/dim]")
            output_parts.append(self._current_streaming)

        output = "\n\n".join(output_parts) if output_parts else ""
        self.update(output)

    def clear(self) -> None:
        """Clear all content."""
        self.content_items.clear()
        self._current_streaming = None
        self.update("")

    def render(self) -> RenderableType:
        """Render the content pane."""
        if not self.content_items:
            return ""
        return self.content_items[-1]  # Show the last item


class LeftPane(Vertical):
    """Left pane containing message log and input field."""

    def __init__(self):
        super().__init__(id="left_pane")
        self.message_log = MessageLog(id="message_log")
        # Use InputTextArea for multi-line input that grows
        self.input_field = InputTextArea(id="input", language="")
        # Track if we should auto-scroll (true unless user manually scrolled up)
        self._auto_scroll = True

    def compose(self) -> ComposeResult:
        # Wrap message log in a scrollable container
        with VerticalScroll(id="message_log_scroll"):
            yield self.message_log
        yield self.input_field

    def add_message(self, content: str) -> None:
        """Add a message to the log and auto-scroll to bottom."""
        self.message_log.add_message(content)
        # Auto-scroll to bottom when new message is added
        if self._auto_scroll:
            self._scroll_to_bottom()

    def _scroll_to_bottom(self) -> None:
        """Scroll the message log to the bottom."""
        scroll_view = self.query_one("#message_log_scroll", VerticalScroll)
        # Scroll to the end
        scroll_view.scroll_end(animate=False)

    def clear_messages(self) -> None:
        """Clear all messages."""
        self.message_log.clear()


class RightPane(Vertical):
    """Right pane containing generated content."""

    def __init__(self):
        super().__init__(id="right_pane")
        self.content_pane = ContentPane(id="content_pane")

    def compose(self) -> ComposeResult:
        # Wrap content pane in a scrollable container
        with VerticalScroll(id="content_pane_scroll"):
            yield self.content_pane

    def add_content(self, content: RenderableType) -> None:
        """Add content to the pane and scroll to top."""
        self.content_pane.add_content(content)
        # Scroll to the top when new content is added
        self._scroll_to_top()

    def _scroll_to_top(self) -> None:
        """Scroll the content pane to the top."""
        scroll_view = self.query_one("#content_pane_scroll", VerticalScroll)
        scroll_view.scroll_home(animate=False)

    def start_streaming(self, header: str = "") -> None:
        """Start a streaming response."""
        self.content_pane.start_streaming(header)
        # Scroll to top when streaming starts
        self._scroll_to_top()

    def stream_token(self, token: str) -> None:
        """Add a token to the streaming response."""
        self.content_pane.stream_token(token)

    def end_streaming(self) -> None:
        """End the streaming response."""
        self.content_pane.end_streaming()

    def clear_content(self) -> None:
        """Clear all content."""
        self.content_pane.clear()


class SplitScreenContainer(Horizontal):
    """Main split-screen container."""

    def __init__(self):
        super().__init__(id="split_screen")
        self.left_pane = LeftPane()
        self.right_pane = RightPane()

    def compose(self) -> ComposeResult:
        yield self.left_pane
        yield DividerWidget(id="divider")
        yield self.right_pane

    def add_left_message(self, content: str) -> None:
        """Add a message to the left pane."""
        self.left_pane.add_message(content)

    def add_right_content(self, content: RenderableType) -> None:
        """Add content to the right pane."""
        self.right_pane.add_content(content)

    def start_streaming(self, header: str = "") -> None:
        """Start streaming response in right pane."""
        self.right_pane.start_streaming(header)

    def stream_token(self, token: str) -> None:
        """Add a token to the streaming response."""
        self.right_pane.stream_token(token)

    def end_streaming(self) -> None:
        """End the streaming response."""
        self.right_pane.end_streaming()

    def clear_left(self) -> None:
        """Clear left pane."""
        self.left_pane.clear_messages()

    def clear_right(self) -> None:
        """Clear right pane."""
        self.right_pane.clear_content()

    def get_input_field(self) -> InputTextArea:
        """Get the input field from the left pane."""
        return self.left_pane.input_field
