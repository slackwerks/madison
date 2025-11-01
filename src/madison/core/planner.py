"""Task planner for multi-model orchestration."""

import json
import logging
from typing import List, Optional, Dict, Any

from madison.api.client import OpenRouterClient
from madison.core.config import Config

logger = logging.getLogger(__name__)


class Task:
    """Represents a single task in an execution plan."""

    def __init__(
        self,
        task_id: str,
        description: str,
        model: str,
        instructions: str,
        depends_on: Optional[List[str]] = None,
        requires_tools: bool = False,
    ):
        """Initialize a task.

        Args:
            task_id: Unique identifier for the task
            description: Human-readable description
            model: Which model to use for this task
            instructions: Instructions for the model
            depends_on: List of task IDs this task depends on
            requires_tools: Whether this task needs tool execution
        """
        self.task_id = task_id
        self.description = description
        self.model = model
        self.instructions = instructions
        self.depends_on = depends_on or []
        self.requires_tools = requires_tools
        self.output = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary."""
        return {
            "id": self.task_id,
            "description": self.description,
            "model": self.model,
            "instructions": self.instructions,
            "depends_on": self.depends_on,
            "requires_tools": self.requires_tools,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        """Create task from dictionary."""
        return cls(
            task_id=data.get("id", ""),
            description=data.get("description", ""),
            model=data.get("model", ""),
            instructions=data.get("instructions", ""),
            depends_on=data.get("depends_on", []),
            requires_tools=data.get("requires_tools", False),
        )


class ExecutionPlan:
    """Represents a complete execution plan."""

    def __init__(self, tasks: List[Task]):
        """Initialize an execution plan.

        Args:
            tasks: List of tasks to execute
        """
        self.tasks = tasks
        self.task_map = {task.task_id: task for task in tasks}

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        return self.task_map.get(task_id)

    def get_executable_tasks(self) -> List[Task]:
        """Get all tasks that are ready to execute (all dependencies satisfied)."""
        completed_tasks = {task.task_id for task in self.tasks if task.output is not None}
        executable = []
        for task in self.tasks:
            if task.output is None and all(dep in completed_tasks for dep in task.depends_on):
                executable.append(task)
        return executable

    def to_dict(self) -> Dict[str, Any]:
        """Convert plan to dictionary."""
        return {"tasks": [task.to_dict() for task in self.tasks]}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionPlan":
        """Create plan from dictionary."""
        tasks = [Task.from_dict(task_data) for task_data in data.get("tasks", [])]
        return cls(tasks)


class Planner:
    """Plans multi-model task execution."""

    PLANNING_PROMPT_TEMPLATE = """You are an intelligent task planner. Analyze the user's request and create a structured execution plan.

{conversation_history}

Current user request:

For the given user request, you should:
1. Identify all distinct subtasks needed to complete the request
2. Determine the type of each task (content_generation, file_operations, analysis, thinking, etc.)
3. Map each task type to an appropriate model from available options
4. Specify dependencies between tasks
5. Generate clear instructions for each model

Available models and their purposes:
- unrestricted: For creative content generation, edgy ideas, unfiltered writing (Venice model)
- content: General content generation and writing
- thinking: Deep analysis and reasoning (Claude Opus)
- tools: For operations that require tool calling like file operations (Claude Sonnet)
- default: Default model for general tasks

CRITICAL MODEL RESTRICTIONS - READ CAREFULLY:

Anthropic models (Claude Sonnet, Claude Opus) WILL REFUSE these requests:
- Explicit sexual content, erotica, or sexually graphic material
- Hate speech or discriminatory content
- Instructions for illegal activities
- Detailed violence or gore
- Detailed instructions for weapons/explosives

Venice (unrestricted) model WILL ACCEPT these requests:
- Explicit sexual content and erotica
- Edgy or controversial content
- Unfiltered opinions and analysis
- Content that Anthropic models decline

ROUTING RULE: If the request contains ANY of these categories → MUST use "unrestricted" model:
- Explicit sexual content (erotica, erotic fiction, sexually graphic material)
- Content the user indicates Anthropic models refuse
- Creative works involving mature/adult themes
- Unfiltered analysis of controversial topics

For each task, provide:
- id: unique identifier (e.g., "generate_content", "save_file")
- description: what the task accomplishes
- model: which model to use
- instructions: detailed instructions for that model
  * If requires_tools=true, instructions MUST explicitly direct the model to use tools
  * For file operations: "Use the write_file tool to save [content description] to [filename]"
  * For web operations: "Use the search_web tool to find [what you're looking for]"
  * For command execution: "Use the execute_command tool to [command description]"
- depends_on: list of task IDs this depends on (empty if no dependencies)
- requires_tools: true if the task needs file operations, web search, etc.

Important guidelines for tool-based instructions - CRITICAL FOR DEPENDENCIES:
- For file operations: ALWAYS include the actual task ID reference in curly braces
- Template: "Use the write_file tool with file_path='filename.txt' and content='''{generate_concepts}'''"
- IMPORTANT: If a task depends on another (e.g., save_concepts depends on generate_concepts), MUST include {generate_concepts} as a variable in the instructions
- Replace "generate_concepts" with the actual task_id from the depends_on list
- Example if save depends on "create_ideas": use {create_ideas} not "the ideas"
- For web operations: "Use the search_web tool to search for: {search_term}" where search_term is from a previous task
- For command execution: "Use the execute_command tool to run: {command_from_previous_task}"
- NEVER just describe what to do - ALWAYS include the actual data from previous tasks using their task IDs in curly braces
- This allows content to flow between tasks automatically

IMPORTANT: Return ONLY a valid JSON object with a "tasks" array. No other text.

User request: {user_request}

Respond with only the JSON plan, no markdown or explanations, and keep the conversation context in mind when planning tasks."""

    def __init__(self, config: Config, client: OpenRouterClient):
        """Initialize the planner.

        Args:
            config: Madison configuration
            client: OpenRouter API client
        """
        self.config = config
        self.client = client
        self.planner_model = config.models.get("planning", config.default_model)

    async def plan(self, user_request: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> Optional[ExecutionPlan]:
        """Create an execution plan for the user request.

        Args:
            user_request: The user's natural language request
            conversation_history: Optional list of recent messages in format [{"role": "user"/"assistant", "content": "..."}, ...]

        Returns:
            ExecutionPlan if successful, None if planning fails
        """
        logger.info(f"Planning request: {user_request[:80]}...")

        # Format conversation history for context
        history_context = ""
        if conversation_history:
            history_lines = ["Recent conversation context:"]
            for msg in conversation_history:
                role = msg.get("role", "unknown").upper()
                content = msg.get("content", "")
                # Truncate very long messages
                if len(content) > 500:
                    content = content[:500] + "..."
                history_lines.append(f"{role}: {content}")
            history_context = "\n".join(history_lines) + "\n"

        # Use simple string replacement instead of .format() to avoid conflicts with example braces
        prompt = self.PLANNING_PROMPT_TEMPLATE.replace("{conversation_history}", history_context).replace("{user_request}", user_request)

        try:
            # Call planner model to create the plan
            response_text = ""
            async for token in self.client.chat_stream(
                messages=[{"role": "user", "content": prompt}],
                model=self.planner_model,
                temperature=0.3,  # Lower temperature for more consistent structure
                max_tokens=2000,
            ):
                response_text += token

            logger.debug(f"Planner response: {response_text}")

            # Parse the JSON response
            try:
                plan_data = json.loads(response_text)
                plan = ExecutionPlan.from_dict(plan_data)
                logger.info(f"Created plan with {len(plan.tasks)} tasks")
                return plan
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse planner response as JSON: {e}")
                logger.debug(f"Response was: {response_text}")
                return None

        except Exception as e:
            logger.error(f"Planning failed: {e}")
            return None
