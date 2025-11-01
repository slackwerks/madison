"""Tool definitions for agent execution via OpenRouter tool calling."""

from typing import Any, Dict, List

from pydantic import BaseModel, Field


class ToolParameter(BaseModel):
    """A tool parameter definition."""

    type: str = Field(..., description="Parameter type: string, number, integer, boolean, etc.")
    description: str = Field(..., description="Human-readable parameter description")
    enum: List[str] = Field(default_factory=list, description="Allowed values for enum parameters")


class ToolParameters(BaseModel):
    """Tool parameters definition."""

    type: str = Field(default="object", description="Always 'object' for function parameters")
    properties: Dict[str, ToolParameter] = Field(default_factory=dict, description="Parameter definitions")
    required: List[str] = Field(default_factory=list, description="Required parameter names")


class ToolFunction(BaseModel):
    """Tool function definition for OpenRouter API."""

    name: str = Field(..., description="Function name (snake_case)")
    description: str = Field(..., description="What the function does and when to use it")
    parameters: ToolParameters = Field(default_factory=ToolParameters, description="Function parameters")


class Tool(BaseModel):
    """Complete tool definition for OpenRouter API."""

    type: str = Field(default="function", description="Always 'function' for function tools")
    function: ToolFunction = Field(..., description="Function definition")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to OpenRouter API format."""
        return {
            "type": self.type,
            "function": {
                "name": self.function.name,
                "description": self.function.description,
                "parameters": {
                    "type": self.function.parameters.type,
                    "properties": {
                        name: {
                            "type": param.type,
                            "description": param.description,
                            **({"enum": param.enum} if param.enum else {})
                        }
                        for name, param in self.function.parameters.properties.items()
                    },
                    "required": self.function.parameters.required,
                },
            },
        }


# Define available tools
EXECUTE_COMMAND_TOOL = Tool(
    function=ToolFunction(
        name="execute_command",
        description="Execute a shell command in the project directory. Use for: running scripts, creating directories, managing files, etc.",
        parameters=ToolParameters(
            properties={
                "command": ToolParameter(
                    type="string",
                    description="The shell command to execute (e.g., 'mkdir foo', 'ls -la', 'python script.py')",
                )
            },
            required=["command"],
        ),
    )
)

READ_FILE_TOOL = Tool(
    function=ToolFunction(
        name="read_file",
        description="Read the contents of a file in the project directory. Use for: viewing files, reading configuration, checking contents, etc.",
        parameters=ToolParameters(
            properties={
                "file_path": ToolParameter(
                    type="string",
                    description="Path to the file to read (relative to project root, e.g., 'README.md', 'src/main.py')",
                )
            },
            required=["file_path"],
        ),
    )
)

WRITE_FILE_TOOL = Tool(
    function=ToolFunction(
        name="write_file",
        description="Write content to a file in the project directory. Use for: creating files, updating configuration, writing code, etc.",
        parameters=ToolParameters(
            properties={
                "file_path": ToolParameter(
                    type="string",
                    description="Path to the file to write (relative to project root, e.g., 'config.yaml', 'src/new_file.py')",
                ),
                "content": ToolParameter(
                    type="string",
                    description="The content to write to the file",
                ),
            },
            required=["file_path", "content"],
        ),
    )
)

SEARCH_WEB_TOOL = Tool(
    function=ToolFunction(
        name="search_web",
        description="Search the web for information. Use for: finding documentation, researching topics, getting current information, etc.",
        parameters=ToolParameters(
            properties={
                "query": ToolParameter(
                    type="string",
                    description="Search query (e.g., 'python documentation', 'how to create REST API')",
                )
            },
            required=["query"],
        ),
    )
)

# List of all available tools
ALL_TOOLS = [
    EXECUTE_COMMAND_TOOL,
    READ_FILE_TOOL,
    WRITE_FILE_TOOL,
    SEARCH_WEB_TOOL,
]


def get_tool_by_name(name: str) -> Tool:
    """Get a tool definition by name.

    Args:
        name: Tool name (e.g., 'execute_command', 'read_file')

    Returns:
        Tool definition

    Raises:
        ValueError: If tool not found
    """
    tool_map = {tool.function.name: tool for tool in ALL_TOOLS}
    if name not in tool_map:
        raise ValueError(f"Unknown tool: {name}")
    return tool_map[name]


def get_tools_as_dicts() -> List[Dict[str, Any]]:
    """Get all tools in OpenRouter API format.

    Returns:
        List of tool definitions as dictionaries
    """
    return [tool.to_dict() for tool in ALL_TOOLS]
