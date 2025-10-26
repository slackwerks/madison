"""Configuration management for Madison."""

import os
from pathlib import Path
from typing import Dict, Optional

import yaml
from pydantic import BaseModel, Field, validator

from madison.exceptions import ConfigError


class Config(BaseModel):
    """Madison configuration."""

    api_key: str = Field(..., description="OpenRouter API key")
    default_model: str = Field(
        "openrouter/auto", description="Default OpenRouter model to use"
    )
    models: Dict[str, str] = Field(
        default_factory=lambda: {"default": "openrouter/auto", "thinking": "openrouter/auto"},
        description="Models for different task types",
    )
    system_prompt: str = Field(
        default="You are a helpful assistant.",
        description="System prompt for the model",
    )
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, description="Max tokens per response")
    timeout: int = Field(default=30, ge=1, description="Request timeout in seconds")
    history_size: int = Field(default=50, ge=1, description="Conversation history size")
    max_retries: int = Field(default=3, ge=0, description="Maximum number of retries for failed requests")
    retry_initial_delay: float = Field(default=1.0, ge=0.1, description="Initial delay in seconds before first retry")
    retry_backoff_factor: float = Field(default=2.0, ge=1.0, description="Multiply delay by this factor after each retry")

    class Config:
        """Pydantic config."""

        validate_assignment = True

    @validator("api_key")
    def validate_api_key(cls, v: str) -> str:
        """Validate API key is not empty."""
        if not v or not v.strip():
            raise ValueError("API key cannot be empty")
        return v.strip()

    @staticmethod
    def config_dir() -> Path:
        """Get the Madison config directory."""
        config_dir = Path.home() / ".madison"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir

    @staticmethod
    def config_file() -> Path:
        """Get the Madison config file path."""
        return Config.config_dir() / "config.yaml"

    @classmethod
    def load(cls) -> "Config":
        """Load configuration from environment or file.

        Priority: Environment variable -> Config file -> Defaults

        Returns:
            Config: The loaded configuration

        Raises:
            ConfigError: If no API key is found
        """
        api_key = os.getenv("OPENROUTER_API_KEY")

        config_data = {}

        # Try to load from config file
        config_file = cls.config_file()
        if config_file.exists():
            try:
                with open(config_file, "r") as f:
                    file_data = yaml.safe_load(f) or {}
                    config_data.update(file_data)
            except Exception as e:
                raise ConfigError(f"Failed to load config file {config_file}: {e}")

        # Environment variable takes priority
        if api_key:
            config_data["api_key"] = api_key
        elif "api_key" not in config_data:
            raise ConfigError(
                "No OpenRouter API key found. Set OPENROUTER_API_KEY environment variable "
                "or create ~/.madison/config.yaml with your api_key."
            )

        try:
            return cls(**config_data)
        except Exception as e:
            raise ConfigError(f"Failed to parse configuration: {e}")

    def get_model(self, task_type: str = "default") -> str:
        """Get model for a specific task type.

        Args:
            task_type: Type of task (default, thinking, etc.)

        Returns:
            str: Model name for the task type
        """
        return self.models.get(task_type, self.default_model)

    def set_model(self, model: str, task_type: str = "default") -> None:
        """Set model for a specific task type.

        Args:
            model: Model name to set
            task_type: Type of task (default, thinking, etc.)
        """
        self.models[task_type] = model
        # Also update default_model if setting default task type
        if task_type == "default":
            self.default_model = model

    def save(self) -> None:
        """Save configuration to file."""
        config_file = self.config_file()
        config_file.parent.mkdir(parents=True, exist_ok=True)

        data = self.dict()
        with open(config_file, "w") as f:
            yaml.dump(data, f, default_flow_style=False)

    def to_dict(self) -> dict:
        """Convert config to dictionary."""
        return self.dict()
