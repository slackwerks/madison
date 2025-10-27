"""Command and chat history management."""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

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


class HistoryManager:
    """Manage command and chat history with JSON storage."""

    def __init__(self):
        """Initialize history manager."""
        self.history_file = _get_data_dir() / "history.json"
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        self._migrate_from_old_location()
        self._ensure_history_file()

    @staticmethod
    def _migrate_from_old_location() -> None:
        """Migrate history from old ~/.madison location to XDG location."""
        old_history_file = Path.home() / ".madison" / "history.json"
        new_history_file = _get_data_dir() / "history.json"

        # Only migrate if old location exists and new doesn't
        if old_history_file.exists() and not new_history_file.exists():
            try:
                with open(old_history_file, "r") as f:
                    old_data = f.read()
                with open(new_history_file, "w") as f:
                    f.write(old_data)
                logger.info(f"Migrated history from {old_history_file} to {new_history_file}")
            except Exception as e:
                logger.warning(f"Could not migrate history: {e}")

    def _ensure_history_file(self) -> None:
        """Ensure history file exists."""
        if not self.history_file.exists():
            self._write_history([])

    def _read_history(self) -> List[dict]:
        """Read history from file."""
        try:
            with open(self.history_file, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read history: {e}")
            return []

    def _write_history(self, history: List[dict]) -> None:
        """Write history to file."""
        try:
            with open(self.history_file, "w") as f:
                json.dump(history, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to write history: {e}")

    def add_entry(self, content: str, entry_type: str = "command") -> None:
        """Add an entry to history.

        Args:
            content: Entry content (command or chat message)
            entry_type: Type of entry ('command', 'query', 'response')
        """
        try:
            history = self._read_history()
            entry = {
                "timestamp": datetime.now().isoformat(),
                "type": entry_type,
                "content": content,
            }
            history.append(entry)

            # Keep last 1000 entries
            if len(history) > 1000:
                history = history[-1000:]

            self._write_history(history)
            logger.debug(f"Added history entry: {entry_type}")

        except Exception as e:
            logger.error(f"Failed to add history entry: {e}")

    def get_recent(self, count: int = 50, entry_type: Optional[str] = None) -> List[dict]:
        """Get recent history entries.

        Args:
            count: Number of entries to return
            entry_type: Filter by entry type (optional)

        Returns:
            List[dict]: Recent history entries
        """
        try:
            history = self._read_history()

            if entry_type:
                history = [h for h in history if h.get("type") == entry_type]

            return history[-count:]

        except Exception as e:
            logger.error(f"Failed to get history: {e}")
            return []

    def search(self, query: str, limit: int = 50) -> List[dict]:
        """Search history for entries matching a query.

        Args:
            query: Search query
            limit: Maximum entries to return

        Returns:
            List[dict]: Matching history entries
        """
        try:
            query = query.lower()
            history = self._read_history()
            results = [
                h
                for h in history
                if query in h.get("content", "").lower()
            ]
            return results[-limit:]

        except Exception as e:
            logger.error(f"Failed to search history: {e}")
            return []

    def clear(self) -> None:
        """Clear all history."""
        try:
            self._write_history([])
            logger.info("History cleared")
        except Exception as e:
            logger.error(f"Failed to clear history: {e}")
            raise MadisonError(f"Failed to clear history: {e}") from e

    def get_stats(self) -> dict:
        """Get history statistics.

        Returns:
            dict: History stats
        """
        try:
            history = self._read_history()
            type_counts = {}
            for entry in history:
                entry_type = entry.get("type", "unknown")
                type_counts[entry_type] = type_counts.get(entry_type, 0) + 1

            return {
                "total_entries": len(history),
                "by_type": type_counts,
                "first_entry": history[0].get("timestamp") if history else None,
                "last_entry": history[-1].get("timestamp") if history else None,
            }

        except Exception as e:
            logger.error(f"Failed to get history stats: {e}")
            return {}
