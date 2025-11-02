"""
Textual-based split-screen UI for Madison UX Experiment.

Left pane: Scrollable message log + input field
Right pane: Scrollable generated content
"""

from typing import List
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import TextArea, Static
from textual.document import Document
from rich.text import Text as RichText
from rich.console import RenderableType


class InputTextArea(TextArea):
    """Custom TextArea that handles Enter for submission and Ctrl+Enter for newlines."""

    def set_text_safe(self, text: str) -> None:
        """Safely set the text content of the input area.

        Uses the proper Document API to avoid JSON serialization issues.
        """
        try:
            # Use the Document API to set text properly
            self.document = Document(text=text)
        except Exception:
            # Fallback: try direct assignment
            try:
                self.text = text
            except Exception:
                # If both fail, just clear it
                self.text = ""

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
        return RichText("│", style="dim")


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

    def add_content(self, content: RenderableType) -> None:
        """Add a content item to the pane."""
        self.content_items.append(content)
        self.update_display()

    def update_display(self) -> None:
        """Update the display with all content."""
        if not self.content_items:
            self.update("")
            return
        # Convert all items to strings and join them
        output = "\n\n".join(
            str(item) for item in self.content_items
        )
        self.update(output)

    def clear(self) -> None:
        """Clear all content."""
        self.content_items.clear()
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

    def compose(self) -> ComposeResult:
        yield self.message_log
        yield self.input_field

    def add_message(self, content: str) -> None:
        """Add a message to the log."""
        self.message_log.add_message(content)

    def clear_messages(self) -> None:
        """Clear all messages."""
        self.message_log.clear()


class RightPane(Vertical):
    """Right pane containing generated content."""

    def __init__(self):
        super().__init__(id="right_pane")
        self.content_pane = ContentPane(id="content_pane")

    def compose(self) -> ComposeResult:
        yield self.content_pane

    def add_content(self, content: RenderableType) -> None:
        """Add content to the pane."""
        self.content_pane.add_content(content)

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

    def clear_left(self) -> None:
        """Clear left pane."""
        self.left_pane.clear_messages()

    def clear_right(self) -> None:
        """Clear right pane."""
        self.right_pane.clear_content()

    def get_input_field(self) -> InputTextArea:
        """Get the input field from the left pane."""
        return self.left_pane.input_field
