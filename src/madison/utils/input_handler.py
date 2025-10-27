"""Enhanced input handling with prompt_toolkit for ESC support."""

import atexit
import logging
import os
import signal
import sys
from typing import Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.patch_stdout import patch_stdout

logger = logging.getLogger(__name__)

# ANSI escape sequences for mouse control
DISABLE_MOUSE_TRACKING = "\x1b[?1000l\x1b[?1002l\x1b[?1003l\x1b[?1006l"
ENABLE_MOUSE_TRACKING = "\x1b[?1000h\x1b[?1002h\x1b[?1003h\x1b[?1006h"

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

        # Disable mouse tracking in the terminal to prevent escape sequences
        # when mouse events occur in other windows
        self._disable_terminal_mouse()

        # Register cleanup on exit
        atexit.register(self._cleanup_terminal)

        # Set up signal handler for suspend (Ctrl+Z)
        try:
            signal.signal(signal.SIGTSTP, signal.SIG_DFL)
        except (ValueError, RuntimeError):
            # Some environments don't support SIGTSTP
            pass

    def _disable_terminal_mouse(self) -> None:
        """Disable mouse tracking in the terminal."""
        try:
            sys.stdout.write(DISABLE_MOUSE_TRACKING)
            sys.stdout.flush()
        except Exception as e:
            logger.debug(f"Could not disable mouse tracking: {e}")

    def _cleanup_terminal(self) -> None:
        """Clean up terminal state on exit."""
        try:
            sys.stdout.write(DISABLE_MOUSE_TRACKING)
            sys.stdout.flush()
        except Exception as e:
            logger.debug(f"Could not clean up terminal: {e}")

    def _setup_key_bindings(self) -> None:
        """Setup key bindings for ESC and Ctrl+Z.

        We add custom handlers for:
        - ESC: Cancel input and exit prompt
        - Ctrl+Z: Send SIGTSTP signal to suspend the process
        """
        bindings = KeyBindings()

        @bindings.add("escape")
        def _(event):
            """Handle ESC key press."""
            self.interrupted = True
            event.app.current_buffer.reset()
            event.app.exit()

        @bindings.add("c-z")
        def _(event):
            """Handle Ctrl+Z to suspend the process."""
            # Exit the prompt first
            event.app.exit()

            # Print suspend message
            print()
            print("Madison has been suspended. Run `fg` to bring Madison back.")
            print("Note: ctrl + z now suspends Madison, ctrl + _ undoes input.")

            # Flush output to ensure message is printed before suspend
            sys.stdout.flush()
            sys.stderr.flush()

            # Send SIGTSTP signal to suspend the process
            os.kill(os.getpid(), signal.SIGTSTP)

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

            # Check if input is None (happens when Ctrl+Z exits the prompt)
            if user_input is None:
                raise InterruptedError("Prompt exited")

            # Filter out incomplete escape sequences that leak from terminal events
            # (e.g., mouse focus events that appear as '[' or 'I')
            user_input = self._filter_escape_sequences(user_input)

            # Show bottom bar with commands
            if show_commands:
                print("─" * TERM_WIDTH)
                print("[Commands] /read /write /exec /search /ask /clear /retry /history /save /load /sessions /model /model-list /system /quit /exit")

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

    @staticmethod
    def _filter_escape_sequences(text: str) -> str:
        """Filter out incomplete escape sequences that leak from terminal events.

        Terminal focus/mouse events can send incomplete escape sequences like:
        - ESC [ (incomplete SGR sequence)
        - ESC I (focus in event)
        - ESC O (SS3 sequence)
        These appear as bare '[', 'I', 'O' characters in input.

        Args:
            text: Input text potentially containing escape sequence artifacts

        Returns:
            Cleaned text with escape sequence artifacts removed
        """
        # If the input is just a single escape-like character, filter it
        cleaned = text.strip()

        # Remove common escape sequence remnants that appear as single characters
        # These are typically incomplete sequences from terminal events
        escape_artifacts = {"[", "I", "O", "M", "]"}
        if cleaned in escape_artifacts:
            logger.debug(f"Filtered terminal escape artifact: {repr(cleaned)}")
            return ""

        return text

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

            # Check if input is None (happens when Ctrl+Z exits the prompt)
            if user_input is None:
                raise InterruptedError("Prompt exited")

            # Filter out incomplete escape sequences that leak from terminal events
            # (e.g., mouse focus events that appear as '[' or 'I')
            user_input = self._filter_escape_sequences(user_input)

            # Show bottom bar with commands
            if show_commands:
                print("─" * TERM_WIDTH)
                print("[Commands] /read /write /exec /search /ask /clear /retry /history /save /load /sessions /model /model-list /system /quit /exit")

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
