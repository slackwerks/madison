"""Configuration management for Madison."""

import os
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from pydantic import BaseModel, Field, validator

from madison.core.model_registry import ModelRegistry
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
        """Get the Madison config directory (XDG_CONFIG_HOME compliant).

        Returns:
            Path: ~/.config/madison or $XDG_CONFIG_HOME/madison
        """
        xdg_config_home = os.getenv("XDG_CONFIG_HOME")
        if xdg_config_home:
            config_dir = Path(xdg_config_home) / "madison"
        else:
            config_dir = Path.home() / ".config" / "madison"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir

    @staticmethod
    def config_file() -> Path:
        """Get the Madison config file path."""
        return Config.config_dir() / "config.yaml"

    @staticmethod
    def _migrate_from_old_location() -> bool:
        """Migrate config from old ~/.madison location to XDG location.

        Returns:
            bool: True if migration was performed, False otherwise
        """
        old_config_file = Path.home() / ".madison" / "config.yaml"
        new_config_file = Config.config_file()

        # Only migrate if old location exists and new doesn't
        if old_config_file.exists() and not new_config_file.exists():
            try:
                with open(old_config_file, "r") as f:
                    old_data = f.read()
                new_config_file.parent.mkdir(parents=True, exist_ok=True)
                with open(new_config_file, "w") as f:
                    f.write(old_data)
                return True
            except Exception as e:
                # Log warning but don't fail - user can manually move file
                print(f"Warning: Could not migrate config from {old_config_file}: {e}")
                return False
        return False

    @classmethod
    def load(cls) -> "Config":
        """Load configuration from environment or file.

        Priority: Environment variable -> Config file -> Defaults
        Automatically migrates from old ~/.madison location to XDG ~/.config/madison

        Returns:
            Config: The loaded configuration

        Raises:
            ConfigError: If no API key is found
        """
        # Try migration from old location if needed
        cls._migrate_from_old_location()

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
                "or create ~/.config/madison/config.yaml with your api_key."
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

    @staticmethod
    def model_supports_tools(model: str) -> bool:
        """Check if a model supports tool calling.

        Args:
            model: Model identifier (e.g., 'openai/gpt-4')

        Returns:
            bool: True if model supports tool calling
        """
        return ModelRegistry.supports_tools(model)

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


class ProjectPermissions(BaseModel):
    """Project-specific permissions configuration."""

    file_operations: Dict[str, List[str]] = Field(
        default_factory=lambda: {"always_allow": ["."]},
        description="File operation permissions (always_allow paths)"
    )
    command_execution: Dict[str, List[str]] = Field(
        default_factory=lambda: {"allowed_paths": ["."]},
        description="Command execution permissions (allowed_paths)"
    )

    class Config:
        """Pydantic config."""
        validate_assignment = True


class ProjectConfig(BaseModel):
    """Project-scoped configuration stored in ./.madison/config.yaml"""

    permissions: ProjectPermissions = Field(
        default_factory=ProjectPermissions,
        description="Project-specific permissions"
    )

    class Config:
        """Pydantic config."""
        validate_assignment = True

    @staticmethod
    def project_dir() -> Path:
        """Get the project directory (.madison folder in current working directory).

        Returns:
            Path: Path to ./.madison directory

        Raises:
            ConfigError: If directory cannot be created
        """
        project_dir = Path.cwd() / ".madison"
        try:
            project_dir.mkdir(parents=True, exist_ok=True)
            return project_dir
        except Exception as e:
            # Don't raise error here - we'll retry on permission checks
            pass
        return project_dir

    @staticmethod
    def project_config_file() -> Path:
        """Get the project config file path.

        Returns:
            Path: Path to ./.madison/config.yaml
        """
        return ProjectConfig.project_dir() / "config.yaml"

    @classmethod
    def load(cls) -> "ProjectConfig":
        """Load project configuration from ./.madison/config.yaml

        Returns:
            ProjectConfig: Loaded configuration or defaults if file doesn't exist

        Raises:
            ConfigError: If config file exists but cannot be parsed
        """
        config_file = cls.project_config_file()

        if config_file.exists():
            try:
                with open(config_file, "r") as f:
                    file_data = yaml.safe_load(f) or {}
                    return cls(**file_data)
            except Exception as e:
                raise ConfigError(f"Failed to load project config {config_file}: {e}")

        # Return defaults if file doesn't exist
        return cls()

    def save(self) -> bool:
        """Save project configuration to ./.madison/config.yaml

        Returns:
            bool: True if save succeeded, False if directory/file cannot be created

        Raises:
            ConfigError: If write operation fails
        """
        try:
            config_file = self.project_config_file()
            config_file.parent.mkdir(parents=True, exist_ok=True)

            data = self.dict()
            with open(config_file, "w") as f:
                yaml.dump(data, f, default_flow_style=False)
            return True
        except PermissionError:
            # Directory/file not writable - will retry later
            return False
        except Exception as e:
            raise ConfigError(f"Failed to save project config: {e}")
