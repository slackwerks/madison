"""Cancellation support for operations."""

import asyncio
import logging
import sys
import threading
from typing import Optional

logger = logging.getLogger(__name__)


class CancellationToken:
    """Token for cancelling async operations."""

    def __init__(self):
        """Initialize cancellation token."""
        self._cancelled = False
        self._event = asyncio.Event()

    def cancel(self) -> None:
        """Signal cancellation."""
        self._cancelled = True
        try:
            self._event.set()
        except RuntimeError:
            # Event loop might be closed
            pass

    @property
    def is_cancelled(self) -> bool:
        """Check if cancelled."""
        return self._cancelled

    async def wait_for_cancellation(self) -> None:
        """Wait until cancellation is signalled."""
        try:
            await self._event.wait()
        except RuntimeError:
            pass


class ESCKeyMonitor:
    """Monitor for ESC key presses and handle cancellation."""

    def __init__(self):
        """Initialize ESC key monitor."""
        self._token: Optional[CancellationToken] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False

    def start(self, token: CancellationToken) -> None:
        """Start monitoring for ESC key.

        Args:
            token: Cancellation token to signal when ESC is pressed
        """
        if self._running:
            return

        self._token = token
        self._running = True
        self._thread = threading.Thread(target=self._monitor_esc, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop monitoring for ESC key."""
        self._running = False

    def _monitor_esc(self) -> None:
        """Monitor for ESC key in a background thread.

        NOTE: ESC monitoring has been disabled because it interferes with
        terminal input handling (breaks arrow keys, leaves TTY in bad state).
        Use Ctrl+C for interruption instead.
        """
        # ESC monitoring disabled - use Ctrl+C instead
        logger.debug("ESC monitoring disabled - use Ctrl+C to interrupt")


# Global ESC monitor instance
_esc_monitor = ESCKeyMonitor()


def start_esc_monitor(token: CancellationToken) -> None:
    """Start the global ESC key monitor.

    Args:
        token: Cancellation token to signal
    """
    _esc_monitor.start(token)


def stop_esc_monitor() -> None:
    """Stop the global ESC key monitor."""
    _esc_monitor.stop()
