"""Enhanced input handling with prompt_toolkit for ESC support."""

import logging
from typing import Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.patch_stdout import patch_stdout

logger = logging.getLogger(__name__)

# Terminal width for bar display
TERM_WIDTH = 80


class InterruptedError(Exception):
    """Raised when user presses ESC to interrupt input."""

    pass


class MadisonPrompt:
    """Enhanced prompt with ESC key support for interruption."""

    def __init__(self):
        """Initialize the Madison prompt."""
        # Disable mouse support to prevent spurious characters when mouse exits terminal
        self.session = PromptSession(mouse_support=False)
        self.interrupted = False
        self._setup_key_bindings()

    def _setup_key_bindings(self) -> None:
        """Setup key bindings for ESC and other shortcuts.

        Note: We only bind ESC and let prompt_toolkit handle all other keys,
        including Ctrl+Z for suspend and Ctrl+C for interrupt.
        """
        bindings = KeyBindings()

        @bindings.add("escape")
        def _(event):
            """Handle ESC key press."""
            self.interrupted = True
            # Clear the current line buffer
            event.app.current_buffer.reset()
            # Exit the prompt
            event.app.exit()

        self.session.key_bindings = bindings

    async def prompt_async(self, prompt_text: str = "> ", show_commands: bool = True) -> Optional[str]:
        """Get input from user asynchronously.

        Args:
            prompt_text: The prompt text to display
            show_commands: Whether to show command help bar

        Returns:
            str: User input, or None if interrupted by ESC

        Raises:
            InterruptedError: If user presses ESC
        """
        try:
            self.interrupted = False

            # Show command help bar if requested
            if show_commands:
                print()  # Blank line
                print("─" * TERM_WIDTH)

            # Use patch_stdout to properly handle Rich console output
            with patch_stdout():
                user_input = await self.session.prompt_async(prompt_text)

            if self.interrupted:
                raise InterruptedError("User pressed ESC")

            # Show bottom bar with commands
            if show_commands:
                print("─" * TERM_WIDTH)
                print("[Commands] /read /write /exec /search /ask /clear /history /save /load /sessions /model /model-list /system /quit /exit")

            return user_input.strip()

        except InterruptedError:
            raise
        except EOFError:
            # Ctrl+D pressed
            raise InterruptedError("EOF")
        except KeyboardInterrupt:
            # Ctrl+C pressed
            raise InterruptedError("Keyboard interrupt")
        except Exception as e:
            logger.debug(f"Error in prompt: {e}")
            raise

    def prompt_sync(self, prompt_text: str = "> ", show_commands: bool = True) -> Optional[str]:
        """Get input from user synchronously.

        Args:
            prompt_text: The prompt text to display
            show_commands: Whether to show command help bar

        Returns:
            str: User input, or None if interrupted by ESC

        Raises:
            InterruptedError: If user presses ESC
        """
        try:
            self.interrupted = False

            # Show command help bar if requested
            if show_commands:
                print()  # Blank line
                print("─" * TERM_WIDTH)

            # Use patch_stdout to properly handle Rich console output
            with patch_stdout():
                user_input = self.session.prompt(prompt_text)

            if self.interrupted:
                raise InterruptedError("User pressed ESC")

            # Show bottom bar with commands
            if show_commands:
                print("─" * TERM_WIDTH)
                print("[Commands] /read /write /exec /search /ask /clear /history /save /load /sessions /model /model-list /system /quit /exit")

            return user_input.strip()

        except InterruptedError:
            raise
        except EOFError:
            # Ctrl+D pressed
            raise InterruptedError("EOF")
        except KeyboardInterrupt:
            # Ctrl+C pressed
            raise InterruptedError("Keyboard interrupt")
        except Exception as e:
            logger.debug(f"Error in prompt: {e}")
            raise
