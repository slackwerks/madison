"""
Textual application for Madison's split-screen TUI interface.

This is the main application class that integrates Madison's core
functionality with the Textual UI framework.
"""

import asyncio
import logging
from typing import Optional, List
from textual.app import ComposeResult, App as TextualApp

from madison.core.application import MadisonApplication
from madison.core.textual_ui_handler import TextualUIHandler
from madison.core.config import Config
from madison.core.tui_components import SplitScreenContainer

logger = logging.getLogger(__name__)


class MadisonTUIApp(TextualApp):
    """Textual application for split-screen Madison interface."""

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
        border: none;
    }

    #message_log_scroll {
        height: 1fr;
        border: none;
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

    #content_pane_scroll {
        height: 1fr;
        border: none;
    }

    #content_pane {
        height: 1fr;
        border: none;
    }

    /* Pane focus styling */
    #message_log_scroll.focus {
        border: solid blue;
    }

    #content_pane_scroll.focus {
        border: solid blue;
    }
    """

    BINDINGS = [
        ("ctrl+tab", "toggle_pane_focus", "Toggle pane focus"),
    ]

    def __init__(self, config: Optional[Config] = None, model: Optional[str] = None):
        """Initialize the Madison TUI application.

        Args:
            config: Madison configuration (will be loaded if not provided)
            model: Optional model override
        """
        super().__init__()
        self.title = "Madison"
        self.config = config
        self.model = model
        self.split_screen: Optional[SplitScreenContainer] = None
        self.ui_handler: Optional[TextualUIHandler] = None
        self.app_instance: Optional[MadisonApplication] = None
        self._input_queue: Optional[asyncio.Queue] = None
        self._app_task: Optional[asyncio.Task] = None
        self.input_history: List[str] = []
        self.history_index: int = -1
        # Pane focus management (True = left pane has scroll focus, False = right pane)
        self._left_pane_focused: bool = True

    def compose(self) -> ComposeResult:
        """Compose the app layout."""
        self.split_screen = SplitScreenContainer()
        yield self.split_screen

    async def on_mount(self) -> None:
        """Setup the app after mount."""
        try:
            # Initialize configuration if not provided
            if not self.config:
                self.config = Config.load()
            if not self.model:
                self.model = self.config.default_model

            # Create input queue for user input
            self._input_queue = asyncio.Queue()

            # Create UI handler
            self.ui_handler = TextualUIHandler(self)

            # Create Madison application instance
            self.app_instance = MadisonApplication(
                self.config,
                self.ui_handler,
                self.model,
            )

            # Initialize the Madison app
            await self.app_instance.initialize()

            # Focus the input field
            input_field = self.split_screen.get_input_field()
            input_field.focus()

            # Start the Madison REPL in the background
            self._app_task = asyncio.create_task(self._run_madison_app())

        except Exception as e:
            logger.exception("Error during app initialization")
            if self.split_screen:
                self.split_screen.add_left_message(f"[red]Initialization Error:[/red] {str(e)}")

    async def _run_madison_app(self) -> None:
        """Run the Madison application in the background."""
        try:
            if self.app_instance:
                await self.app_instance.run()
        except asyncio.CancelledError:
            logger.debug("Madison app task cancelled")
        except Exception as e:
            logger.exception("Error in Madison app")
            if self.split_screen:
                self.split_screen.add_left_message(f"[red]Error in Madison app:[/red] {str(e)}")

    def navigate_history(self, direction: int) -> None:
        """Navigate through input history.

        Args:
            direction: -1 for previous, 1 for next
        """
        if not self.split_screen:
            return

        input_field = self.split_screen.get_input_field()

        # If no history, do nothing
        if not self.input_history:
            return

        # First navigation: start from the end
        if self.history_index == -1:
            if direction == -1:
                self.history_index = len(self.input_history) - 1
            else:
                return  # Can't go forward from start
        else:
            # Navigate within history
            new_index = self.history_index + direction
            if 0 <= new_index < len(self.input_history):
                self.history_index = new_index
            elif new_index == len(self.input_history):
                # Gone past the end, show empty
                self.history_index = -1
                try:
                    input_field.set_text_safe("")
                except Exception as e:
                    logger.exception("Error clearing input field")
                    self.split_screen.add_left_message(f"[red]Error clearing input:[/red] {str(e)}")
                return
            else:
                # Can't go further back
                return

        # Set input field to history item
        if 0 <= self.history_index < len(self.input_history):
            try:
                input_field.set_text_safe(self.input_history[self.history_index])
            except Exception as e:
                logger.exception(f"Error setting input field to history item: {e}")
                self.split_screen.add_left_message(f"[red]Error loading history:[/red] {str(e)}")

    def action_submit_input(self) -> None:
        """Handle input submission via Enter."""
        if not self.split_screen or not self._input_queue:
            return

        input_field = self.split_screen.get_input_field()
        user_input = input_field.text.strip()

        if not user_input:
            return

        # Add to history
        self.input_history.append(user_input)
        self.history_index = -1  # Reset history index

        # Add input to left pane
        self.split_screen.add_left_message(f"[cyan]>[/cyan] {user_input}")

        # Clear the input field
        input_field.text = ""

        # Queue the input for the Madison app
        try:
            self._input_queue.put_nowait(user_input)
        except Exception as e:
            logger.exception("Error queuing input")
            self.split_screen.add_left_message(f"[red]Error queuing input:[/red] {str(e)}")

    def action_toggle_pane_focus(self) -> None:
        """Toggle scroll focus between left and right panes."""
        try:
            # Get the scroll containers
            message_log_scroll = self.query_one("#message_log_scroll")
            content_pane_scroll = self.query_one("#content_pane_scroll")

            # Toggle focus state
            self._left_pane_focused = not self._left_pane_focused

            # Update visual indicator (focus class)
            if self._left_pane_focused:
                message_log_scroll.add_class("focus")
                content_pane_scroll.remove_class("focus")
            else:
                message_log_scroll.remove_class("focus")
                content_pane_scroll.add_class("focus")
        except Exception as e:
            logger.exception(f"Error toggling pane focus: {e}")

    async def action_quit(self) -> None:
        """Quit the application."""
        try:
            if self._app_task and not self._app_task.done():
                self._app_task.cancel()
                try:
                    await self._app_task
                except asyncio.CancelledError:
                    pass

            if self.ui_handler:
                await self.ui_handler.shutdown()
        except Exception as e:
            logger.exception("Error during shutdown")
        finally:
            # Force exit the Textual app
            self.exit()

    async def on_shutdown(self) -> None:
        """Handle application shutdown with proper cleanup."""
        try:
            logger.debug("Starting Madison app shutdown")

            # Cancel the Madison app task if running
            if self._app_task and not self._app_task.done():
                self._app_task.cancel()
                try:
                    await self._app_task
                except asyncio.CancelledError:
                    logger.debug("Madison app task cancelled")

            # Clean up UI handler
            if self.ui_handler:
                await self.ui_handler.shutdown()

            logger.debug("Madison app shutdown complete")
        except Exception as e:
            logger.exception("Error during on_shutdown cleanup")

    def on_exit(self) -> None:
        """Handle final cleanup when app exits."""
        try:
            logger.debug("Cleaning up terminal state")
            # Force cancel any running tasks
            if self._app_task and not self._app_task.done():
                self._app_task.cancel()
        except Exception as e:
            logger.exception("Error during on_exit cleanup")
