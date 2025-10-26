"""Conversation session management."""

import logging
from datetime import datetime
from typing import List, Optional

from madison.api.models import Message

logger = logging.getLogger(__name__)


class Session:
    """Manages a conversation session."""

    def __init__(self, system_prompt: str, history_size: int = 50):
        """Initialize a session.

        Args:
            system_prompt: System prompt for the conversation
            history_size: Maximum number of messages to keep in history
        """
        self.system_prompt = system_prompt
        self.history_size = history_size
        self.messages: List[Message] = [
            Message(role="system", content=system_prompt)
        ]
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    def add_message(self, role: str, content: str) -> None:
        """Add a message to the session.

        Args:
            role: Message role (user, assistant, system)
            content: Message content
        """
        self.messages.append(Message(role=role, content=content))
        self.updated_at = datetime.now()

        # Trim history if needed (keep system message)
        if len(self.messages) > self.history_size + 1:
            self.messages = [self.messages[0]] + self.messages[-(self.history_size) :]

    def get_messages(self) -> List[Message]:
        """Get all messages in the session.

        Returns:
            List[Message]: All messages except system message
        """
        # Return all messages including system for API calls
        return self.messages

    def get_history(self) -> List[Message]:
        """Get conversation history excluding system message.

        Returns:
            List[Message]: Conversation history
        """
        return self.messages[1:]  # Exclude system message

    def clear(self) -> None:
        """Clear conversation history but keep system prompt."""
        system_msg = self.messages[0]
        self.messages = [system_msg]
        self.updated_at = datetime.now()

    def get_context(self) -> str:
        """Get a human-readable context summary.

        Returns:
            str: Context summary
        """
        history = self.get_history()
        if not history:
            return "No conversation history yet."

        summary_lines = []
        for msg in history:
            role = msg.role.upper()
            content = msg.content[:100]
            if len(msg.content) > 100:
                content += "..."
            summary_lines.append(f"{role}: {content}")

        return "\n".join(summary_lines)

    def __len__(self) -> int:
        """Get the number of messages (excluding system)."""
        return len(self.get_history())

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"Session(messages={len(self)}, created_at={self.created_at}, "
            f"updated_at={self.updated_at})"
        )
