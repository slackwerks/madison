"""
Textual application for Madison UX Experiment split-screen interface.
"""

import asyncio
from typing import Optional, Callable
from textual.app import ComposeResult, on
from textual.app import App as TextualApp
from rich.text import Text as RichText
from .textual_ui import SplitScreenContainer, InputTextArea


class MadisonTUIApp(TextualApp):
    """Textual application for split-screen Madison UX."""

    CSS = """
    Screen {
        layout: vertical;
    }

    #split_screen {
        width: 1fr;
        height: 1fr;
    }

    #left_pane {
        width: 1fr;
        height: 1fr;
    }

    #right_pane {
        width: 1fr;
        height: 1fr;
    }

    #divider {
        width: 1;
        height: 100%;
        content-align: center middle;
    }

    #message_log {
        height: 1fr;
        border: none;
        overflow: auto;
    }

    #input {
        height: auto;
        min-height: 3;
        max-height: 10;
        border: solid green;
        overflow: auto;
    }

    #content_pane {
        height: 1fr;
        border: none;
    }
    """

    def __init__(self):
        super().__init__()
        self.title = "Madison UX Experiment"
        self.split_screen: Optional[SplitScreenContainer] = None

    def compose(self) -> ComposeResult:
        """Compose the app layout."""
        self.split_screen = SplitScreenContainer()
        yield self.split_screen

    def on_mount(self) -> None:
        """Setup the app after mount."""
        if self.split_screen:
            # Add startup messages
            self.split_screen.add_left_message("Madison UX Experiment — Split-screen interface")
            self.split_screen.add_left_message("Commands: /demo | /clear | /quit")

            # Focus the input field
            input_field = self.split_screen.get_input_field()
            input_field.focus()


    def action_submit_input(self) -> None:
        """Handle input submission via Enter."""
        if not self.split_screen:
            return

        input_field = self.split_screen.get_input_field()
        user_input = input_field.text.strip()

        if not user_input:
            return

        # Add input to left pane
        self.split_screen.add_left_message(f"> {user_input}")

        # Clear the input field
        input_field.text = ""

        # Handle commands
        if user_input.lower() == "/quit":
            self.exit()
        elif user_input.lower() == "/clear":
            self.split_screen.clear_left()
            self.split_screen.clear_right()
        elif user_input.lower() == "/demo":
            # Run demo asynchronously
            self.run_worker(self._demo_task())
        else:
            # Echo the input to demonstrate the UI
            self.split_screen.add_left_message("Processing request...")
            self.run_worker(self._echo_task(user_input))

    async def _echo_task(self, user_input: str) -> None:
        """Handle echo response asynchronously."""
        if not self.split_screen:
            return

        await asyncio.sleep(0.2)
        self.split_screen.add_right_content(
            RichText(
                f"Echo: {user_input}\n\n"
                "(In a real implementation, this would be the model response)"
            )
        )
        self.split_screen.add_left_message("Response complete")

    async def _demo_task(self) -> None:
        """Run the demo interaction asynchronously."""
        if not self.split_screen:
            return

        self.split_screen.clear_left()
        self.split_screen.clear_right()
        self.split_screen.add_left_message("Explain quantum computing")

        await asyncio.sleep(0.3)
        self.split_screen.add_left_message("Processing request...")

        await asyncio.sleep(0.2)
        self.split_screen.add_left_message("Creating execution plan...")

        await asyncio.sleep(0.2)
        self.split_screen.add_left_message("Step 1: Research quantum fundamentals")

        await asyncio.sleep(0.2)
        self.split_screen.add_left_message("Step 2: Compile information")

        await asyncio.sleep(0.2)
        self.split_screen.add_left_message("Calling model: claude-sonnet-4")

        await asyncio.sleep(0.5)
        self.split_screen.add_right_content(
            RichText(
                "Quantum computing represents a fundamental shift in computation, "
                "leveraging quantum mechanical phenomena like superposition and entanglement "
                "to process information in fundamentally different ways than classical computers.\n\n"
                "[bold]Key Concepts:[/bold]\n"
                "• Qubits: Unlike classical bits, qubits can exist in superposition\n"
                "• Entanglement: Qubits can be correlated in ways impossible classically\n"
                "• Quantum Gates: Operations that manipulate quantum states\n\n"
                "This enables solving certain problems exponentially faster than classical approaches."
            )
        )

        await asyncio.sleep(0.2)
        self.split_screen.add_left_message("Response received")
