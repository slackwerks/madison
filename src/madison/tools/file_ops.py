"""File operations for Madison."""

import logging
from pathlib import Path
from typing import Optional

from madison.core.permissions import PermissionManager
from madison.exceptions import FileOperationError

logger = logging.getLogger(__name__)

# Maximum file size to read (100 MB)
MAX_FILE_SIZE = 100 * 1024 * 1024


class FileOperations:
    """Handle file read and write operations."""

    def __init__(self, base_dir: Optional[Path] = None):
        """Initialize file operations.

        Args:
            base_dir: Base directory for file operations (defaults to current working directory)
        """
        self.base_dir = base_dir or Path.cwd()
        self.permission_manager = PermissionManager()

    def _resolve_path(self, file_path: str) -> Path:
        """Resolve and validate file path.

        Args:
            file_path: Path to resolve

        Returns:
            Path: Resolved path

        Raises:
            FileOperationError: If path is invalid or outside base directory
        """
        try:
            # Handle both absolute and relative paths
            if Path(file_path).is_absolute():
                target = Path(file_path)
            else:
                target = (self.base_dir / file_path).resolve()

            # Ensure path is under base_dir (security check)
            try:
                target.relative_to(self.base_dir)
            except ValueError:
                raise FileOperationError(
                    f"Access denied: {file_path} is outside allowed directory {self.base_dir}"
                )

            return target
        except Exception as e:
            if isinstance(e, FileOperationError):
                raise
            raise FileOperationError(f"Invalid path: {file_path}") from e

    def read(self, file_path: str, encoding: str = "utf-8") -> str:
        """Read a file.

        Args:
            file_path: Path to file
            encoding: File encoding (default: utf-8)

        Returns:
            str: File contents

        Raises:
            FileOperationError: If read fails or permission denied
        """
        try:
            # Check permissions
            if not self.permission_manager.can_read_file(file_path, prompt_user=True):
                raise FileOperationError(f"Permission denied: {file_path}")

            target = self._resolve_path(file_path)

            if not target.exists():
                raise FileOperationError(f"File not found: {file_path}")

            if not target.is_file():
                raise FileOperationError(f"Not a file: {file_path}")

            if target.stat().st_size > MAX_FILE_SIZE:
                raise FileOperationError(
                    f"File too large: {file_path} exceeds {MAX_FILE_SIZE} bytes"
                )

            with open(target, "r", encoding=encoding) as f:
                return f.read()

        except FileOperationError:
            raise
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            raise FileOperationError(f"Failed to read file {file_path}: {e}") from e

    def write(
        self, file_path: str, content: str, encoding: str = "utf-8", create_dirs: bool = True
    ) -> None:
        """Write to a file.

        Args:
            file_path: Path to file
            content: Content to write
            encoding: File encoding (default: utf-8)
            create_dirs: Whether to create parent directories (default: True)

        Raises:
            FileOperationError: If write fails or permission denied
        """
        try:
            # Check permissions
            if not self.permission_manager.can_write_file(file_path, prompt_user=True):
                raise FileOperationError(f"Permission denied: {file_path}")

            target = self._resolve_path(file_path)

            if create_dirs:
                target.parent.mkdir(parents=True, exist_ok=True)

            with open(target, "w", encoding=encoding) as f:
                f.write(content)

            logger.info(f"Wrote {len(content)} bytes to {file_path}")

        except FileOperationError:
            raise
        except Exception as e:
            logger.error(f"Failed to write file {file_path}: {e}")
            raise FileOperationError(f"Failed to write file {file_path}: {e}") from e

    def append(
        self, file_path: str, content: str, encoding: str = "utf-8", create_dirs: bool = True
    ) -> None:
        """Append to a file.

        Args:
            file_path: Path to file
            content: Content to append
            encoding: File encoding (default: utf-8)
            create_dirs: Whether to create parent directories (default: True)

        Raises:
            FileOperationError: If append fails or permission denied
        """
        try:
            # Check permissions
            if not self.permission_manager.can_write_file(file_path, prompt_user=True):
                raise FileOperationError(f"Permission denied: {file_path}")

            target = self._resolve_path(file_path)

            if create_dirs:
                target.parent.mkdir(parents=True, exist_ok=True)

            with open(target, "a", encoding=encoding) as f:
                f.write(content)

            logger.info(f"Appended {len(content)} bytes to {file_path}")

        except FileOperationError:
            raise
        except Exception as e:
            logger.error(f"Failed to append to file {file_path}: {e}")
            raise FileOperationError(f"Failed to append to file {file_path}: {e}") from e

    def exists(self, file_path: str) -> bool:
        """Check if a file exists.

        Args:
            file_path: Path to check

        Returns:
            bool: Whether file exists
        """
        try:
            target = self._resolve_path(file_path)
            return target.exists()
        except FileOperationError:
            return False

    def delete(self, file_path: str) -> None:
        """Delete a file.

        Args:
            file_path: Path to file

        Raises:
            FileOperationError: If delete fails or permission denied
        """
        try:
            # Check permissions
            if not self.permission_manager.can_write_file(file_path, prompt_user=True):
                raise FileOperationError(f"Permission denied: {file_path}")

            target = self._resolve_path(file_path)

            if not target.exists():
                raise FileOperationError(f"File not found: {file_path}")

            if not target.is_file():
                raise FileOperationError(f"Not a file: {file_path}")

            target.unlink()
            logger.info(f"Deleted {file_path}")

        except FileOperationError:
            raise
        except Exception as e:
            logger.error(f"Failed to delete file {file_path}: {e}")
            raise FileOperationError(f"Failed to delete file {file_path}: {e}") from e
