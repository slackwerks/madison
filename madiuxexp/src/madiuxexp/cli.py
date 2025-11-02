"""
CLI entry point for Madison UX Experiment with integrated Textual TUI
"""

import logging
import typer
from typing import Optional

from madison.core.config import Config
from madison.exceptions import ConfigError
from madiuxexp.ui.integrated_app import IntegratedMadisonApp

# Setup logging
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = typer.Typer()


@app.command()
def main(
    model: Optional[str] = typer.Option(
        None, "--model", "-m", help="OpenRouter model to use"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
) -> None:
    """Madison UX Experiment - Split-screen Textual interface with real Madison backend"""
    if verbose:
        logging.getLogger("madison").setLevel(logging.DEBUG)
        logging.getLogger("madiuxexp").setLevel(logging.DEBUG)
    else:
        logging.getLogger("madison").setLevel(logging.WARNING)
        logging.getLogger("madiuxexp").setLevel(logging.WARNING)

    try:
        # Load configuration
        config = Config.load()
        model = model or config.default_model

        # Create and run the integrated app
        tui_app = IntegratedMadisonApp(config=config, model=model)
        tui_app.run()
    except ConfigError as e:
        logger.error(f"Configuration Error: {e}")
        raise typer.Exit(1)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.exception("Error running Madison TUI")
        if verbose:
            raise
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
