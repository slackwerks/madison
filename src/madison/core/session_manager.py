"""Session persistence and management."""

import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from madison.api.models import Message
from madison.core.session import Session
from madison.exceptions import MadisonError

logger = logging.getLogger(__name__)


def _get_data_dir() -> Path:
    """Get XDG data directory for Madison.

    Returns:
        Path: ~/.local/share/madison or $XDG_DATA_HOME/madison
    """
    xdg_data_home = os.getenv("XDG_DATA_HOME")
    if xdg_data_home:
        data_dir = Path(xdg_data_home) / "madison"
    else:
        data_dir = Path.home() / ".local" / "share" / "madison"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


class SessionManager:
    """Manage session persistence with JSON storage."""

    def __init__(self):
        """Initialize session manager."""
        self.sessions_dir = _get_data_dir() / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self._migrate_from_old_location()

    @staticmethod
    def _migrate_from_old_location() -> None:
        """Migrate sessions from old ~/.madison/sessions location to XDG location."""
        old_sessions_dir = Path.home() / ".madison" / "sessions"
        new_sessions_dir = _get_data_dir() / "sessions"

        # Only migrate if old location exists and new is empty
        if old_sessions_dir.exists() and not list(new_sessions_dir.glob("*.json")):
            try:
                # Copy all session files
                for session_file in old_sessions_dir.glob("*.json"):
                    shutil.copy2(session_file, new_sessions_dir / session_file.name)
                logger.info(f"Migrated sessions from {old_sessions_dir} to {new_sessions_dir}")
            except Exception as e:
                logger.warning(f"Could not migrate sessions: {e}")

    def save_session(self, session: Session, name: Optional[str] = None) -> str:
        """Save a session to disk.

        Args:
            session: Session to save
            name: Optional session name (auto-generated if not provided)

        Returns:
            str: Session filename

        Raises:
            MadisonError: If save fails
        """
        try:
            # Generate filename
            if not name:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                name = f"session_{timestamp}"
            else:
                # Sanitize name
                name = "".join(c for c in name if c.isalnum() or c in "-_")

            filename = f"{name}.json"
            filepath = self.sessions_dir / filename

            # Prepare session data
            session_data = {
                "name": name,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "system_prompt": session.system_prompt,
                "messages": [
                    {"role": msg.role, "content": msg.content}
                    for msg in session.messages
                ],
            }

            # Write to file
            with open(filepath, "w") as f:
                json.dump(session_data, f, indent=2)

            logger.info(f"Session saved to {filepath}")
            return filename

        except Exception as e:
            logger.error(f"Failed to save session: {e}")
            raise MadisonError(f"Failed to save session: {e}") from e

    def load_session(self, filename: str) -> Session:
        """Load a session from disk.

        Args:
            filename: Session filename (with or without .json extension)

        Returns:
            Session: Loaded session

        Raises:
            MadisonError: If load fails
        """
        try:
            # Ensure .json extension
            if not filename.endswith(".json"):
                filename = f"{filename}.json"

            filepath = self.sessions_dir / filename

            if not filepath.exists():
                raise MadisonError(f"Session not found: {filename}")

            # Read from file
            with open(filepath, "r") as f:
                session_data = json.load(f)

            # Reconstruct session
            system_prompt = session_data.get("system_prompt", "You are a helpful assistant.")
            session = Session(system_prompt=system_prompt)

            # Clear default system message and rebuild from data
            session.messages = [
                Message(role=msg["role"], content=msg["content"])
                for msg in session_data.get("messages", [])
            ]

            logger.info(f"Session loaded from {filepath}")
            return session

        except MadisonError:
            raise
        except Exception as e:
            logger.error(f"Failed to load session: {e}")
            raise MadisonError(f"Failed to load session: {e}") from e

    def list_sessions(self) -> List[dict]:
        """List all saved sessions.

        Returns:
            List[dict]: List of session info dicts
        """
        try:
            sessions = []
            for filepath in sorted(self.sessions_dir.glob("*.json"), reverse=True):
                try:
                    with open(filepath, "r") as f:
                        data = json.load(f)
                        sessions.append(
                            {
                                "filename": filepath.name,
                                "name": data.get("name", filepath.stem),
                                "created_at": data.get("created_at"),
                                "updated_at": data.get("updated_at"),
                                "message_count": len(data.get("messages", [])),
                            }
                        )
                except Exception as e:
                    logger.warning(f"Failed to read session {filepath.name}: {e}")
                    continue

            return sessions

        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
            return []

    def delete_session(self, filename: str) -> None:
        """Delete a saved session.

        Args:
            filename: Session filename

        Raises:
            MadisonError: If delete fails
        """
        try:
            # Ensure .json extension
            if not filename.endswith(".json"):
                filename = f"{filename}.json"

            filepath = self.sessions_dir / filename

            if not filepath.exists():
                raise MadisonError(f"Session not found: {filename}")

            filepath.unlink()
            logger.info(f"Session deleted: {filename}")

        except MadisonError:
            raise
        except Exception as e:
            logger.error(f"Failed to delete session: {e}")
            raise MadisonError(f"Failed to delete session: {e}") from e
