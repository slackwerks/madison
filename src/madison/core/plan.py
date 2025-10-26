"""Plan and action models for agent execution."""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ActionType(str, Enum):
    """Types of actions that can be planned."""

    EXEC = "exec"  # Execute shell command
    READ = "read"  # Read a file
    WRITE = "write"  # Write a file
    SEARCH = "search"  # Web search


class PlanAction(BaseModel):
    """A single action in a plan."""

    type: ActionType = Field(..., description="Type of action")
    description: str = Field(..., description="Human-readable description of what this action does")

    # Command execution
    command: Optional[str] = Field(None, description="Shell command to execute (for exec actions)")

    # File operations
    file_path: Optional[str] = Field(None, description="File path (for read/write actions)")
    content: Optional[str] = Field(None, description="Content to write (for write actions)")

    # Web search
    query: Optional[str] = Field(None, description="Search query (for search actions)")

    # Execution result
    executed: bool = Field(default=False, description="Whether this action has been executed")
    result: Optional[str] = Field(None, description="Result of execution")
    error: Optional[str] = Field(None, description="Error message if execution failed")

    class Config:
        """Pydantic config."""
        use_enum_values = False


class Plan(BaseModel):
    """A plan consisting of multiple actions."""

    reasoning: str = Field(..., description="Why this plan is needed")
    description: str = Field(..., description="High-level summary of the plan")
    actions: List[PlanAction] = Field(default_factory=list, description="Actions to execute")

    class Config:
        """Pydantic config."""
        validate_assignment = True

    def can_execute_all(self) -> bool:
        """Check if all actions have been approved for execution."""
        return all(action.executed or action.error is None for action in self.actions)

    def get_pending_actions(self) -> List[PlanAction]:
        """Get actions that haven't been executed yet."""
        return [action for action in self.actions if not action.executed and action.error is None]

    def get_failed_actions(self) -> List[PlanAction]:
        """Get actions that failed."""
        return [action for action in self.actions if action.error is not None]

    def summary(self) -> str:
        """Get a summary of the plan."""
        lines = [f"Plan: {self.description}"]
        lines.append(f"Reasoning: {self.reasoning}")
        lines.append("\nActions:")
        for i, action in enumerate(self.actions, 1):
            status = "✓" if action.executed else "○"
            lines.append(f"  {status} {i}. {action.description}")
            if action.type == ActionType.EXEC and action.command:
                lines.append(f"     Command: {action.command}")
            elif action.type == ActionType.READ and action.file_path:
                lines.append(f"     File: {action.file_path}")
            elif action.type == ActionType.WRITE and action.file_path:
                lines.append(f"     File: {action.file_path}")
            elif action.type == ActionType.SEARCH and action.query:
                lines.append(f"     Query: {action.query}")
        return "\n".join(lines)
