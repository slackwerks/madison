"""
Split-screen UI layout for Madison.

Left pane: Prompt input + control/operation messages
Right pane: Generated content and responses
"""

from dataclasses import dataclass
from typing import List, Optional
from rich.console import Console, RenderableType
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.live import Live
from datetime import datetime


@dataclass
class Message:
    """Represents a message in the split-screen UI."""
    timestamp: str
    message_type: str  # "control", "operation", "input", "output"
    content: str
    category: Optional[str] = None  # e.g., "plan", "exec", "search", "response"


class SplitScreenUI:
    """
    Split-screen UI manager.

    Left pane shows:
    - User input (marked with ">")
    - Control messages (plans, confirmations, status)
    - Operation messages (command execution, search queries)

    Right pane shows:
    - Generated content
    - Streaming responses
    - File contents
    - Search results
    """

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.layout = Layout()
        self.left_messages: List[Message] = []
        self.right_content: List[RenderableType] = []
        self.input_prompt: str = "> "
        self.setup_layout()

    def setup_layout(self):
        """Initialize the split-screen layout."""
        self.layout.split_row(
            Layout(name="left", ratio=1),
            Layout(name="divider", size=1),
            Layout(name="right", ratio=1),
        )

    def render_header(self) -> None:
        """Render the header with title and current model info."""
        header_text = Text.assemble(
            ("Madison UX Experiment", "bold cyan"),
            " — ",
            ("Split-Screen Mode", "dim"),
        )
        header = Panel(
            header_text,
            expand=False,
            style="blue",
        )
        self.layout["header"].update(header)

    def add_left_message(
        self,
        content: str,
        message_type: str = "control",
        category: Optional[str] = None,
    ) -> None:
        """
        Add a message to the left pane.

        Args:
            content: Message content
            message_type: "control", "operation", or "input"
            category: Message category for styling (e.g., "plan", "exec")
        """
        msg = Message(
            timestamp=datetime.now().strftime("%H:%M:%S"),
            message_type=message_type,
            content=content,
            category=category,
        )
        self.left_messages.append(msg)
        self.render_left_pane()

    def add_right_content(self, content: RenderableType) -> None:
        """
        Add content to the right pane.

        Args:
            content: Rich-renderable content (Text, Panel, Table, etc.)
        """
        self.right_content.append(content)
        self.render_right_pane()

    def clear_right_content(self) -> None:
        """Clear all content from the right pane."""
        self.right_content.clear()
        self.render_right_pane()

    def render_left_pane(self) -> None:
        """Render the left pane with all messages and input prompt."""
        from rich.text import Text as RichText

        # Build a list of text lines
        text_obj = RichText()

        for msg in self.left_messages[-25:]:  # Show last 25 messages (one less to make room)
            text_obj.append(msg.content)
            text_obj.append("\n")

        self.layout["left"].update(text_obj)

    def render_right_pane(self) -> None:
        """Render the right pane with all content."""
        if not self.right_content:
            self.layout["right"].update("")
            return

        # Create a vertical layout for right pane content
        content_layout = Layout()
        content_layout.split_column(
            *[Layout(content) for content in self.right_content[-5:]]  # Show last 5 items
        )

        self.layout["right"].update(content_layout)

    def refresh(self) -> None:
        """Refresh and render the entire UI."""
        self.render_left_pane()
        self.render_right_pane()
        # Update the divider with full-height vertical line
        divider_text = Text("\n".join(["│"] * 50), style="dim")
        self.layout["divider"].update(divider_text)
        self.console.print(self.layout)

    def clear(self) -> None:
        """Clear all content."""
        self.left_messages.clear()
        self.right_content.clear()
        self.refresh()

    @staticmethod
    def _get_type_style(message_type: str, category: Optional[str]) -> str:
        """Get the style for a message type."""
        styles = {
            "input": "bold cyan",
            "control": "cyan",
            "operation": "yellow",
            "output": "green",
        }
        return styles.get(message_type, "white")


# Example usage
if __name__ == "__main__":
    console = Console()
    ui = SplitScreenUI(console)

    # Add some example messages
    ui.add_left_message("User asked: Explain quantum computing", "input")
    ui.add_left_message("Loading execution plan...", "control", "plan")
    ui.add_left_message("Task 1: Research quantum basics", "control", "plan")
    ui.add_left_message("Executing with claude-sonnet-4...", "operation", "exec")

    # Add some example output
    ui.add_right_content(
        Panel("Quantum computing is a paradigm shift...", title="[bold]Response[/bold]")
    )

    ui.refresh()
