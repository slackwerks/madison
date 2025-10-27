"""Tool executor for handling tool calls from the agent."""

import logging
from typing import Any, Dict

from madison.core.permissions import PermissionManager
from madison.tools.command_exec import CommandExecutor
from madison.tools.file_ops import FileOperations
from madison.tools.web_search import WebSearcher

logger = logging.getLogger(__name__)


class ToolExecutor:
    """Executes tool calls and manages permissions."""

    def __init__(self):
        """Initialize the tool executor."""
        self.permission_manager = PermissionManager()
        self.file_ops = FileOperations()
        self.command_executor = CommandExecutor()
        self.web_searcher = WebSearcher()

    async def execute(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Execute a tool call.

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments

        Returns:
            Result of the tool execution as a string

        Raises:
            ValueError: If tool not found
            Exception: If execution fails
        """
        if tool_name == "execute_command":
            return await self._execute_command(arguments)
        elif tool_name == "read_file":
            return self._read_file(arguments)
        elif tool_name == "write_file":
            return self._write_file(arguments)
        elif tool_name == "search_web":
            return await self._search_web(arguments)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    async def _execute_command(self, arguments: Dict[str, Any]) -> str:
        """Execute a shell command.

        Args:
            arguments: Must contain 'command' key

        Returns:
            Command output or error message
        """
        command = arguments.get("command")
        if not command:
            return "Error: command parameter is required"

        try:
            logger.info(f"Executing command: {command}")
            stdout, stderr, returncode = await self.command_executor.execute(command)

            if returncode == 0:
                return stdout or "(command executed successfully)"
            else:
                error_msg = stderr or f"Command failed with exit code {returncode}"
                return f"Error: {error_msg}"

        except Exception as e:
            error_msg = f"Failed to execute command: {str(e)}"
            logger.error(error_msg)
            return f"Error: {error_msg}"

    def _read_file(self, arguments: Dict[str, Any]) -> str:
        """Read a file.

        Args:
            arguments: Must contain 'file_path' key

        Returns:
            File contents or error message
        """
        file_path = arguments.get("file_path")
        if not file_path:
            return "Error: file_path parameter is required"

        try:
            logger.info(f"Reading file: {file_path}")
            content = self.file_ops.read(file_path)
            return content

        except FileNotFoundError:
            return f"Error: File not found: {file_path}"
        except Exception as e:
            error_msg = f"Failed to read file: {str(e)}"
            logger.error(error_msg)
            return f"Error: {error_msg}"

    def _write_file(self, arguments: Dict[str, Any]) -> str:
        """Write to a file.

        Args:
            arguments: Must contain 'file_path' and 'content' keys

        Returns:
            Success message or error message
        """
        file_path = arguments.get("file_path")
        content = arguments.get("content", "")

        if not file_path:
            return "Error: file_path parameter is required"

        try:
            logger.info(f"Writing to file: {file_path}")
            self.file_ops.write(file_path, content)
            return f"Successfully wrote {len(content)} bytes to {file_path}"

        except Exception as e:
            error_msg = f"Failed to write file: {str(e)}"
            logger.error(error_msg)
            return f"Error: {error_msg}"

    async def _search_web(self, arguments: Dict[str, Any]) -> str:
        """Search the web.

        Args:
            arguments: Must contain 'query' key

        Returns:
            Search results or error message
        """
        query = arguments.get("query")
        if not query:
            return "Error: query parameter is required"

        try:
            logger.info(f"Searching web: {query}")
            results = await self.web_searcher.search(query)
            return results

        except Exception as e:
            error_msg = f"Failed to search web: {str(e)}"
            logger.error(error_msg)
            return f"Error: {error_msg}"
