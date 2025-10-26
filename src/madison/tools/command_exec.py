"""Command execution for Madison."""

import asyncio
import logging
import subprocess
from typing import Tuple

from madison.exceptions import CommandExecutionError

logger = logging.getLogger(__name__)

# Maximum output size (10 MB)
MAX_OUTPUT_SIZE = 10 * 1024 * 1024


class CommandExecutor:
    """Execute shell commands safely."""

    def __init__(self, timeout: int = 30):
        """Initialize command executor.

        Args:
            timeout: Command timeout in seconds
        """
        self.timeout = timeout

    async def execute(self, command: str) -> Tuple[str, str, int]:
        """Execute a shell command asynchronously.

        Args:
            command: Shell command to execute

        Returns:
            Tuple[str, str, int]: (stdout, stderr, returncode)

        Raises:
            CommandExecutionError: If execution fails
        """
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=self.timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise CommandExecutionError(
                    f"Command timed out after {self.timeout} seconds"
                )

            stdout_str = stdout.decode("utf-8", errors="replace")
            stderr_str = stderr.decode("utf-8", errors="replace")

            # Check output size
            if len(stdout_str) > MAX_OUTPUT_SIZE:
                stdout_str = (
                    stdout_str[: MAX_OUTPUT_SIZE // 2]
                    + f"\n... (output truncated, exceeded {MAX_OUTPUT_SIZE} bytes) ...\n"
                    + stdout_str[-MAX_OUTPUT_SIZE // 2 :]
                )

            if len(stderr_str) > MAX_OUTPUT_SIZE:
                stderr_str = (
                    stderr_str[: MAX_OUTPUT_SIZE // 2]
                    + f"\n... (error output truncated, exceeded {MAX_OUTPUT_SIZE} bytes) ...\n"
                    + stderr_str[-MAX_OUTPUT_SIZE // 2 :]
                )

            logger.info(f"Command executed: {command} (exit code: {process.returncode})")

            return stdout_str, stderr_str, process.returncode

        except CommandExecutionError:
            raise
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            raise CommandExecutionError(f"Command execution failed: {e}") from e

    async def execute_safe(self, command: str) -> str:
        """Execute a command and return formatted output.

        Args:
            command: Shell command to execute

        Returns:
            str: Formatted output

        Raises:
            CommandExecutionError: If execution fails
        """
        stdout, stderr, returncode = await self.execute(command)

        output = ""
        if stdout:
            output += f"[bold]Output:[/bold]\n{stdout}\n"
        if stderr:
            output += f"[bold]Errors:[/bold]\n{stderr}\n"
        if returncode != 0:
            output += f"[yellow]Exit code: {returncode}[/yellow]"

        return output or "[dim]Command completed with no output[/dim]"
