"""Orchestrator for executing multi-model task plans."""

import logging
import re
from pathlib import Path
from typing import Dict, Any, Optional

from rich.console import Console

from madison.api.client import OpenRouterClient
from madison.api.models import ToolLoopResult
from madison.core.config import Config
from madison.core.planner import ExecutionPlan, Task
from madison.core.tool_executor import ToolExecutor
from madison.core.tools import get_tools_as_dicts

logger = logging.getLogger(__name__)
console = Console()


class Orchestrator:
    """Executes task plans with model routing and tool execution."""

    def __init__(self, config: Config, client: OpenRouterClient, tool_executor: Optional[ToolExecutor] = None):
        """Initialize the orchestrator.

        Args:
            config: Madison configuration
            client: OpenRouter API client
            tool_executor: Tool executor for file operations, etc.
        """
        self.config = config
        self.client = client
        self.tool_executor = tool_executor or ToolExecutor()

        # Model name to config strategy mapping
        self.model_mapping = {
            "unrestricted": config.models.get("unrestricted", config.default_model),
            "content": config.models.get("default", config.default_model),
            "thinking": config.models.get("thinking", config.default_model),
            "tools": config.models.get("tools", config.default_model),
            "default": config.default_model,
        }

    def _resolve_model(self, model_name: str) -> str:
        """Resolve a model name to an actual model identifier.

        Args:
            model_name: The model strategy name (unrestricted, tools, etc.)

        Returns:
            The actual model identifier
        """
        # If it's already a full model path, use it as-is
        if "/" in model_name:
            return model_name
        # Otherwise, map it through our model mapping
        return self.model_mapping.get(model_name, model_name)

    def _substitute_variables(self, text: str, task_outputs: Dict[str, Any]) -> str:
        """Substitute task output variables into text.

        Args:
            text: Text with {variable_name} placeholders
            task_outputs: Dictionary of task_id -> output

        Returns:
            Text with variables substituted
        """
        result = text
        for task_id, output in task_outputs.items():
            if output is not None:
                # Handle both string and dict outputs
                if isinstance(output, dict):
                    output_str = str(output)
                else:
                    output_str = str(output)
                result = result.replace(f"{{{task_id}}}", output_str)
        return result

    def _get_written_file_contents(self, result: ToolLoopResult) -> str:
        """Extract written file contents from tool execution results.

        After write_file tool executes, read the actual file and return its contents.
        This ensures file contents are available in the conversation context.

        The ToolExecutionResult includes the arguments passed to write_file, which contain
        the path. We use that to read the file back instead of regex pattern matching.

        Args:
            result: ToolLoopResult containing tool execution metadata and arguments

        Returns:
            String containing file contents with headers, or empty string if no files written
        """
        file_contents = []

        logger.debug(f"_get_written_file_contents: checking {len(result.tool_executions)} tool executions")

        # Look through all tool executions for write_file operations
        for i, execution in enumerate(result.tool_executions):
            logger.debug(f"  Execution {i}: tool={execution.tool_name}, success={execution.success}, args={execution.arguments}")

            if execution.tool_name == "write_file" and execution.success:
                # Extract the file path from the tool arguments
                # write_file expects: {"file_path": "filename.txt", "content": "..."}
                file_path_str = execution.arguments.get("file_path")
                logger.debug(f"    write_file found, file_path={file_path_str}")

                if file_path_str:
                    try:
                        file_path = Path(file_path_str)
                        logger.debug(f"    checking if {file_path} exists: {file_path.exists()}")
                        if file_path.exists() and file_path.is_file():
                            with open(file_path, "r") as f:
                                content = f.read()
                            file_contents.append(f"\n--- Contents of {file_path_str} ---\n{content}\n")
                            logger.info(f"Read written file: {file_path_str}")
                    except Exception as e:
                        logger.debug(f"Could not read file {file_path_str}: {e}")
                else:
                    logger.debug(f"    No path in arguments: {execution.arguments}")

        logger.debug(f"  Result: {len(file_contents)} file(s) read")
        return "".join(file_contents)

    async def execute(self, plan: ExecutionPlan) -> str:
        """Execute an execution plan.

        Args:
            plan: The execution plan to execute

        Returns:
            Final result or error message
        """
        logger.info(f"Starting orchestration of {len(plan.tasks)} tasks")
        task_outputs: Dict[str, Any] = {}

        # Keep executing while there are executable tasks
        while True:
            executable_tasks = plan.get_executable_tasks()
            if not executable_tasks:
                break

            # Execute each ready task
            for task in executable_tasks:
                logger.info(f"Executing task: {task.task_id} - {task.description}")
                console.print(f"\n[cyan]→ {task.description}[/cyan]")

                # Resolve the actual model to use
                actual_model = self._resolve_model(task.model)
                console.print(f"  [dim]Model: {task.model} ({actual_model})[/dim]")

                # Substitute variables in instructions
                instructions = self._substitute_variables(task.instructions, task_outputs)

                try:
                    if task.requires_tools:
                        # Execute with tool calling
                        result = await self._execute_with_tools(task, instructions, actual_model)
                    else:
                        # Execute as simple text generation
                        result = await self._execute_text_generation(instructions, actual_model)

                    task.output = result
                    task_outputs[task.task_id] = result
                    logger.info(f"Task {task.task_id} completed")

                except Exception as e:
                    error_msg = f"Task {task.task_id} failed: {e}"
                    logger.error(error_msg)
                    console.print(f"  [red]Error: {e}[/red]")
                    task.output = None
                    return error_msg

        # Return the output of the last task
        if plan.tasks:
            last_task = plan.tasks[-1]
            final_output = task_outputs.get(last_task.task_id, "")
            logger.info("Orchestration complete")
            return final_output or "Task execution completed"
        return "No tasks to execute"

    async def _execute_text_generation(self, instructions: str, model: str) -> str:
        """Execute a text generation task.

        Args:
            instructions: Instructions for the model
            model: Model to use

        Returns:
            Generated text
        """
        logger.debug(f"Text generation with model {model}")
        response_text = ""

        async for token in self.client.chat_stream(
            messages=[{"role": "user", "content": instructions}],
            model=model,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        ):
            response_text += token
            # Print tokens for real-time feedback
            console.file.write(token)
            console.file.flush()

        console.print()  # Newline after streaming
        return response_text

    async def _execute_with_tools(self, task: Task, instructions: str, model: str) -> str:
        """Execute a task with tool calling support.

        Args:
            task: The task being executed
            instructions: Instructions for the model
            model: Model to use

        Returns:
            Result of tool execution including tool execution metadata
        """
        logger.debug(f"Tool execution with model {model}")

        # Get available tools
        all_tools = get_tools_as_dicts()

        # Wrap instructions to ensure tool execution is clear
        tool_names = ", ".join([tool["function"]["name"] for tool in all_tools])
        explicit_instructions = f"""You have access to the following tools: {tool_names}

{instructions}

Remember: You MUST use the appropriate tools to complete this task. Do not just describe what you would do - actually call the tools with the correct parameters."""

        try:
            # Execute with tool calling loop
            # Use lower temperature for tool execution (more deterministic)
            tool_temperature = min(self.config.temperature, 0.3)
            result: ToolLoopResult = await self.client.call_with_tool_loop(
                initial_message=explicit_instructions,
                model=model,
                tools=all_tools,
                tool_executor=self.tool_executor.execute,
                temperature=tool_temperature,
                max_tokens=self.config.max_tokens,
            )

            # Build final response with tool execution metadata (like Claude Code does)
            full_response = result.response_text or "Tools executed successfully"

            # Add tool execution summary
            tool_summary = result.format_summary()
            if tool_summary:
                full_response += tool_summary

            # After tool execution, try to read back any files that were created
            # This captures the actual file contents for context (like Claude Code does with Write())
            file_contents = self._get_written_file_contents(result)
            if file_contents:
                full_response += file_contents

            return full_response
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            raise
