"""Madison - A Python CLI for interacting with OpenRouter models."""

__version__ = "0.1.0"
__author__ = "Madison Contributors"

from madison.api.client import OpenRouterClient
from madison.core.config import Config
from madison.core.session import Session

__all__ = ["OpenRouterClient", "Config", "Session"]
