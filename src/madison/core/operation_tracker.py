"""Operation tracking for Claude Code style logging."""

from typing import Optional, List
from datetime import datetime


class OperationDetail:
    """Represents a single detail line in an operation."""

    def __init__(self, text: str, success: bool = True):
        """Initialize an operation detail.

        Args:
            text: Detail text to display
            success: Whether this is a success (green) or failure (red)
        """
        self.text = text
        self.success = success

    def format(self, indent: int = 0) -> str:
        """Format the detail as a string.

        Args:
            indent: Number of spaces to indent

        Returns:
            Formatted detail string
        """
        prefix = " " * indent
        color = "[green]" if self.success else "[red]"
        close_color = "[/green]" if self.success else "[/red]"
        return f"{prefix}  ↳ {color}{self.text}{close_color}"


class OperationContext:
    """Tracks a single operation and its results."""

    def __init__(self, operation_type: str, description: str):
        """Initialize an operation context.

        Args:
            operation_type: Type of operation (read, exec, search, etc.)
            description: Human-readable description (e.g., file path, command)
        """
        self.operation_type = operation_type
        self.description = description
        self.details: List[OperationDetail] = []
        self.start_time = datetime.now()
        self.end_time: Optional[datetime] = None

    def add_detail(self, text: str, success: bool = True) -> None:
        """Add a detail line to the operation.

        Args:
            text: Detail text
            success: Whether this is success (green) or failure (red)
        """
        self.details.append(OperationDetail(text, success))

    def complete(self) -> None:
        """Mark operation as complete."""
        self.end_time = datetime.now()

    def format(self) -> str:
        """Format the operation as a string with all details.

        Returns:
            Formatted operation string
        """
        # Format operation header
        op_header = f"{self.operation_type.title()}({self.description})"

        # Format all details
        formatted_details = [detail.format() for detail in self.details]

        # Combine header and details
        output = op_header
        if formatted_details:
            output += "\n" + "\n".join(formatted_details)

        return output
