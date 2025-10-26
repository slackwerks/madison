"""Permission management for project scope."""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Set

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from madison.core.config import ProjectConfig

logger = logging.getLogger(__name__)
console = Console()


class PermissionManager:
    """Manages file and command execution permissions with user prompting."""

    def __init__(self):
        """Initialize permission manager."""
        self.project_config = ProjectConfig.load()
        self.permission_cache: Dict[str, bool] = {}  # Cache user decisions
        self.cwd = Path.cwd()

    def _normalize_path(self, path: str) -> Path:
        """Normalize a path relative to cwd.

        Args:
            path: Path to normalize

        Returns:
            Path: Normalized absolute path
        """
        p = Path(path)
        if p.is_absolute():
            return p.resolve()
        else:
            return (self.cwd / p).resolve()

    def _is_within_project(self, path: Path) -> bool:
        """Check if a path is within the project directory.

        Args:
            path: Path to check

        Returns:
            bool: True if path is within or equal to cwd
        """
        try:
            path.resolve().relative_to(self.cwd.resolve())
            return True
        except ValueError:
            return False

    def _is_path_allowed(self, path: Path, allowed_paths: List[str]) -> bool:
        """Check if a path matches the allowed paths list.

        Args:
            path: Path to check
            allowed_paths: List of allowed paths (relative to cwd)

        Returns:
            bool: True if path is in allowed list
        """
        path_abs = path.resolve()
        cwd_abs = self.cwd.resolve()

        for allowed in allowed_paths:
            allowed_path = self._normalize_path(allowed).resolve()
            try:
                # Check if path is under allowed path or is the allowed path
                path_abs.relative_to(allowed_path)
                return True
            except ValueError:
                # Not under this allowed path
                continue

        return False

    def can_read_file(self, file_path: str, prompt_user: bool = False) -> bool:
        """Check if a file can be read.

        Args:
            file_path: Path to file
            prompt_user: If True, prompt user when permission denied

        Returns:
            bool: True if file can be read
        """
        path = self._normalize_path(file_path)

        # Check cache first
        cache_key = f"read:{path}"
        if cache_key in self.permission_cache:
            return self.permission_cache[cache_key]

        # Check if within project
        if not self._is_within_project(path):
            if prompt_user:
                return self.prompt_for_permission(file_path, "file_read")
            logger.warning(f"File operation denied (outside project): {file_path}")
            return False

        # Check allowed paths
        allowed_paths = self.project_config.permissions.file_operations.get("always_allow", ["."])
        if self._is_path_allowed(path, allowed_paths):
            self.permission_cache[cache_key] = True
            return True

        # Permission denied - prompt if requested
        if prompt_user:
            return self.prompt_for_permission(file_path, "file_read")

        logger.warning(f"File operation denied (not in allowed paths): {file_path}")
        return False

    def can_write_file(self, file_path: str, prompt_user: bool = False) -> bool:
        """Check if a file can be written.

        Args:
            file_path: Path to file
            prompt_user: If True, prompt user when permission denied

        Returns:
            bool: True if file can be written
        """
        path = self._normalize_path(file_path)

        # Check cache first
        cache_key = f"write:{path}"
        if cache_key in self.permission_cache:
            return self.permission_cache[cache_key]

        # Check if within project
        if not self._is_within_project(path):
            if prompt_user:
                return self.prompt_for_permission(file_path, "file_write")
            logger.warning(f"File operation denied (outside project): {file_path}")
            return False

        # Check allowed paths
        allowed_paths = self.project_config.permissions.file_operations.get("always_allow", ["."])
        if self._is_path_allowed(path, allowed_paths):
            self.permission_cache[cache_key] = True
            return True

        # Permission denied - prompt if requested
        if prompt_user:
            return self.prompt_for_permission(file_path, "file_write")

        logger.warning(f"File operation denied (not in allowed paths): {file_path}")
        return False

    def can_execute_command(self, command: str, cwd: Optional[str] = None, prompt_user: bool = False) -> bool:
        """Check if a command can be executed.

        Args:
            command: Command to execute
            cwd: Working directory for command (optional)
            prompt_user: If True, prompt user when permission denied

        Returns:
            bool: True if command can be executed
        """
        # Check cache first
        cache_key = f"exec:{command}:{cwd}"
        if cache_key in self.permission_cache:
            return self.permission_cache[cache_key]

        # Get working directory
        exec_cwd = self._normalize_path(cwd) if cwd else self.cwd

        # Check if within project
        if not self._is_within_project(exec_cwd):
            if prompt_user:
                return self.prompt_for_permission(command, "command_exec")
            logger.warning(f"Command execution denied (outside project): {command}")
            return False

        # Check allowed paths
        allowed_paths = self.project_config.permissions.command_execution.get("allowed_paths", ["."])
        if self._is_path_allowed(exec_cwd, allowed_paths):
            self.permission_cache[cache_key] = True
            return True

        # Permission denied - prompt if requested
        if prompt_user:
            return self.prompt_for_permission(command, "command_exec")

        logger.warning(f"Command execution denied (not in allowed directory): {command}")
        return False

    def _add_path_to_whitelist(self, path: Path, operation: str) -> bool:
        """Add a path to the whitelist and save config.

        Args:
            path: Path to add to whitelist
            operation: Type of operation ("file_read", "file_write", or "command_exec")

        Returns:
            bool: True if successfully added and saved, False otherwise
        """
        try:
            # Get relative path from cwd for storage
            try:
                rel_path = str(path.relative_to(self.cwd.resolve()))
            except ValueError:
                # If path is not relative to cwd, use absolute path
                rel_path = str(path)

            # Add to appropriate whitelist
            if operation in ("file_read", "file_write"):
                allowed_list = self.project_config.permissions.file_operations.get("always_allow", [])
                if rel_path not in allowed_list:
                    allowed_list.append(rel_path)
                    self.project_config.permissions.file_operations["always_allow"] = allowed_list
            elif operation == "command_exec":
                allowed_list = self.project_config.permissions.command_execution.get("allowed_paths", [])
                if rel_path not in allowed_list:
                    allowed_list.append(rel_path)
                    self.project_config.permissions.command_execution["allowed_paths"] = allowed_list

            # Save config
            return self.project_config.save()
        except Exception as e:
            logger.error(f"Failed to add path to whitelist: {e}")
            return False

    def prompt_for_permission(self, path: str, operation: str) -> bool:
        """Prompt user for permission to perform an operation.

        Args:
            path: Path or operation being requested
            operation: Type of operation ("file_read", "file_write", or "command_exec")

        Returns:
            bool: True if user grants permission (once or always), False otherwise
        """
        # Display the permission request
        console.print()
        request_type = {
            "file_read": "Read file",
            "file_write": "Write file",
            "command_exec": "Execute command"
        }.get(operation, "Operation")

        panel_content = f"{request_type}: [cyan]{path}[/cyan]\n\n"
        panel_content += "This operation is outside your project permissions.\n"
        panel_content += "What would you like to do?\n\n"
        panel_content += "1. Yes, this once\n"
        panel_content += "2. Yes, always (save to .madison/config.yaml)\n"
        panel_content += "3. No, deny this operation"

        console.print(Panel(panel_content, title="Permission Request", expand=False))

        # Prompt for user choice
        choice = Prompt.ask("Enter choice", choices=["1", "2", "3"], default="3")

        if choice == "1":
            # Yes once - allow this operation without saving
            logger.info(f"Permission granted once for {operation}: {path}")
            return True
        elif choice == "2":
            # Yes always - add to whitelist and save
            normalized_path = self._normalize_path(path)
            if self._add_path_to_whitelist(normalized_path, operation):
                console.print(f"[green]✓[/green] Permission saved to .madison/config.yaml")
                logger.info(f"Permission granted and saved for {operation}: {path}")
                return True
            else:
                console.print(f"[red]✗[/red] Failed to save permission. Allowing this once anyway.")
                return True
        else:
            # No - deny permission
            logger.info(f"Permission denied for {operation}: {path}")
            console.print("[red]Operation denied.[/red]")
            return False

    def reload_config(self) -> None:
        """Reload project configuration from disk.

        Called when retrying operations after permissions may have changed.
        """
        try:
            self.project_config = ProjectConfig.load()
            logger.info("Project configuration reloaded")
        except Exception as e:
            logger.warning(f"Failed to reload project config: {e}")
