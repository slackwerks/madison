"""Custom exceptions for Madison."""


class MadisonError(Exception):
    """Base exception for Madison."""

    pass


class ConfigError(MadisonError):
    """Configuration-related errors."""

    pass


class APIError(MadisonError):
    """OpenRouter API-related errors."""

    pass


class FileOperationError(MadisonError):
    """File operation errors."""

    pass


class CommandExecutionError(MadisonError):
    """Command execution errors."""

    pass


class InvalidToolCall(MadisonError):
    """Invalid tool call errors."""

    pass
