"""TUI launcher for Madison."""

import logging
from typing import Optional

from madison.core.config import Config
from madison.core.tui_app import MadisonTUIApp

logger = logging.getLogger(__name__)


def launch_tui(
    config: Config,
    model: Optional[str] = None,
) -> None:
    """Launch the Textual TUI application.

    Args:
        config: Madison configuration
        model: Optional model override

    Raises:
        ImportError: If textual is not installed
        Exception: If TUI initialization fails
    """
    try:
        # Import here to make Textual optional
        import textual  # noqa: F401
    except ImportError as e:
        raise ImportError(
            "Textual TUI requires the 'textual' package. "
            "Install with: pip install textual"
        ) from e

    tui_app = None
    try:
        # Create and run the TUI app
        logger.debug("Launching Textual TUI")
        tui_app = MadisonTUIApp(config=config, model=model)
        tui_app.run()
        logger.debug("Textual TUI exited normally")
    except KeyboardInterrupt:
        logger.debug("Textual TUI interrupted by user")
    except Exception as e:
        logger.exception("Error launching TUI")
        raise
    finally:
        # Ensure cleanup happens even if app crashes
        try:
            if tui_app:
                logger.debug("Performing final TUI cleanup")
                # Ensure the app is fully shut down
                if hasattr(tui_app, '_app_task') and tui_app._app_task:
                    if not tui_app._app_task.done():
                        tui_app._app_task.cancel()
        except Exception as cleanup_error:
            logger.exception("Error during TUI cleanup")
            # Don't raise cleanup errors - the app is already exiting
