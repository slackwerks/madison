"""
Textual application for Madison's split-screen TUI interface.

This is the main application class that integrates Madison's core
functionality with the Textual UI framework.
"""

import asyncio
import logging
from typing import Optional, List
from textual.app import ComposeResult, App as TextualApp
from textual.events import MouseScrollDown, MouseScrollUp, Key

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
        scrollbar-size: 0 1;
    }

    #message_log {
        width: 1fr;
        border: none;
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
        scrollbar-size: 0 1;
    }

    #content_pane {
        width: 1fr;
        border: none;
    }

    /* Pane focus styling */
    #message_log_scroll.focus {
        border: heavy $accent;
        background: $boost;
    }

    #content_pane_scroll.focus {
        border: heavy $accent;
        background: $boost;
    }
    """

    BINDINGS = [
        ("ctrl+n", "toggle_pane_focus", "Toggle pane focus"),
        ("up", "scroll_focused_pane('up')", "Scroll up"),
        ("down", "scroll_focused_pane('down')", "Scroll down"),
        ("pageup", "scroll_focused_pane('pageup')", "Page up"),
        ("pagedown", "scroll_focused_pane('pagedown')", "Page down"),
        ("alt+up", "history_previous", "Previous history"),
        ("alt+down", "history_next", "Next history"),
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
        # Pane focus management: 'input' = input box, 'left' = left pane, 'right' = right pane
        self._focus_state: str = 'left'  # Default to left pane focus

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

    async def on_key(self, event: Key) -> None:
        """Handle key events at app level, before they reach widgets."""
        logger.debug(f"on_key called: key={event.key}, focus_state={self._focus_state}")
        # If focus is on a pane (not input), handle scroll keys here
        if self._focus_state in ('left', 'right'):
            logger.debug(f"Pane has focus, checking scroll key: {event.key}")
            if event.key == "up":
                logger.debug("Handling up arrow for pane scroll")
                self.action_scroll_focused_pane('up')
                event.prevent_default()
            elif event.key == "down":
                logger.debug("Handling down arrow for pane scroll")
                self.action_scroll_focused_pane('down')
                event.prevent_default()
            elif event.key == "pageup":
                logger.debug("Handling pageup for pane scroll")
                self.action_scroll_focused_pane('pageup')
                event.prevent_default()
            elif event.key == "pagedown":
                logger.debug("Handling pagedown for pane scroll")
                self.action_scroll_focused_pane('pagedown')
                event.prevent_default()

    def action_history_previous(self) -> None:
        """Navigate to previous input history."""
        if hasattr(self, "navigate_history"):
            self.navigate_history(-1)

    def action_history_next(self) -> None:
        """Navigate to next input history."""
        if hasattr(self, "navigate_history"):
            self.navigate_history(1)

    def action_toggle_pane_focus(self) -> None:
        """Cycle focus between input box, left pane, and right pane."""
        try:
            # Get the widgets
            input_field = self.split_screen.get_input_field()
            message_log_scroll = self.query_one("#message_log_scroll")
            content_pane_scroll = self.query_one("#content_pane_scroll")

            # Cycle through focus states: left -> right -> input -> left ...
            if self._focus_state == 'left':
                next_state = 'right'
            elif self._focus_state == 'right':
                next_state = 'input'
            else:  # 'input'
                next_state = 'left'

            self._focus_state = next_state
            logger.debug(f"Cycled pane focus to: {self._focus_state}")

            # Update visual indicators (focus class) and widget focus
            message_log_scroll.remove_class("focus")
            content_pane_scroll.remove_class("focus")

            if self._focus_state == 'input':
                logger.debug("Focus -> input box")
                input_field.focus()
            elif self._focus_state == 'left':
                logger.debug("Focus -> left pane")
                message_log_scroll.add_class("focus")
                message_log_scroll.focus()
            elif self._focus_state == 'right':
                logger.debug("Focus -> right pane")
                content_pane_scroll.add_class("focus")
                content_pane_scroll.focus()
        except Exception as e:
            logger.exception(f"Error toggling pane focus: {e}")

    def action_scroll_focused_pane(self, direction: str) -> None:
        """Scroll the focused pane in the specified direction.

        Args:
            direction: 'up', 'down', 'pageup', or 'pagedown'
        """
        try:
            logger.debug(f"action_scroll_focused_pane called: direction={direction}, focus_state={self._focus_state}")

            # Get the appropriate scroll container based on focus state
            if self._focus_state == 'left':
                scroll_view = self.query_one("#message_log_scroll")
                logger.debug(f"Got left scroll view: {scroll_view}")
            elif self._focus_state == 'right':
                scroll_view = self.query_one("#content_pane_scroll")
                logger.debug(f"Got right scroll view: {scroll_view}")
            else:  # 'input' - don't scroll if focus is on input
                logger.debug("Skipping scroll - input has focus")
                return

            # Perform the scroll action
            if direction == "up":
                logger.debug("Calling scroll_up")
                scroll_view.scroll_up(animate=False)
            elif direction == "down":
                logger.debug("Calling scroll_down")
                scroll_view.scroll_down(animate=False)
            elif direction == "pageup":
                logger.debug("Calling scroll_page_up")
                scroll_view.scroll_page_up()
            elif direction == "pagedown":
                logger.debug("Calling scroll_page_down")
                scroll_view.scroll_page_down()
            logger.debug("Scroll action completed")
        except Exception as e:
            logger.exception(f"Error scrolling focused pane: {e}")

    def on_mouse_scroll_down(self, event: MouseScrollDown) -> None:
        """Handle mouse scroll down in the focused pane."""
        try:
            if self._focus_state == 'left':
                scroll_view = self.query_one("#message_log_scroll")
            elif self._focus_state == 'right':
                scroll_view = self.query_one("#content_pane_scroll")
            else:  # 'input' - don't scroll
                return

            scroll_view.scroll_down(animate=False)
            event.prevent_default()
        except Exception as e:
            logger.exception(f"Error handling mouse scroll down: {e}")

    def on_mouse_scroll_up(self, event: MouseScrollUp) -> None:
        """Handle mouse scroll up in the focused pane."""
        try:
            if self._focus_state == 'left':
                scroll_view = self.query_one("#message_log_scroll")
            elif self._focus_state == 'right':
                scroll_view = self.query_one("#content_pane_scroll")
            else:  # 'input' - don't scroll
                return

            scroll_view.scroll_up(animate=False)
            event.prevent_default()
        except Exception as e:
            logger.exception(f"Error handling mouse scroll up: {e}")

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
