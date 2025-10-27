# Madison - OpenRouter CLI

A pure Python CLI application for interacting with OpenRouter models, similar to Claude Code but focused on OpenRouter integration.

## Features

- **Interactive REPL chat** with streaming responses
- **Model selection** - Choose from available OpenRouter models
- **File operations** - Read and write files with `/read` and `/write` commands
- **Command execution** - Run shell commands with `/exec`
- **Web search** - Search the web with `/search`
- **Session persistence** - Save and resume conversations with `/save` and `/load`
- **Command history** - Full history tracking and retrieval
- **ESC key support** - Cancel input cleanly without breaking TTY
- **Arrow key history** - Navigate through command history with ↑/↓
- **Conversation history** - Maintain context across multiple messages
- **Configuration management** - Interactive setup wizard or YAML config files
- **Async-first design** - Fast streaming responses using asyncio and httpx

## Installation

```bash
# Clone or download the repository
cd madison

# Install in development mode
pip install -e .

# Or with dev dependencies
pip install -e ".[dev]"
```

## Configuration

Madison supports configuration through:

1. **Environment variable** (highest priority): `OPENROUTER_API_KEY`
2. **Configuration file**: `~/.config/madison/config.yaml` (XDG Base Directory)
3. **Built-in defaults**

### Setup

```bash
# Option 1: Set environment variable
export OPENROUTER_API_KEY="your-api-key-here"

# Option 2: Create config file
mkdir -p ~/.config/madison
cat > ~/.config/madison/config.yaml << EOF
api_key: "your-api-key-here"
default_model: "openrouter/auto"
system_prompt: "You are a helpful assistant."
temperature: 0.7
max_tokens: 2000
timeout: 30
history_size: 50
EOF
```

## Usage

### Start Interactive Chat

```bash
madison
```

The chat is the default command, so you can just run `madison` to start. You can also specify a different model with `madison --model "gpt-4"`.

Commands available in chat:

**Chat & Conversation:**
- `/quit`, `/exit` - Exit the chat
- `/clear` - Clear conversation history
- `/retry` - Resubmit the last prompt (useful after rate limit errors)
- `/history` - Show conversation history
- `/system` - Show/set system prompt
- `/model` - Show/set models registered for different strategies
- `/ask <strategy> <prompt>` - Send a prompt to a registered strategy (e.g., `/ask thinking "What is 2+2?"`)
- `/ask model=<MODEL> <prompt>` - Send a prompt to a specific model directly
- `/model-list <search_term>` - Search available OpenRouter models (e.g., `/model-list gpt` or `/model-list claude`)
- `/model-list series=<series>` - List models by series (e.g., `/model-list series=gpt` or `/model-list series=claude`)

**Agent Management:**
- `/agent` or `/agent list` - List all available agents
- `/agent list <category>` - List agents in a specific category (e.g., `/agent list analysis`)
- `/agent templates` - Show available agent templates
- `/agent create` - Interactive wizard to create a custom agent
- `/agent use <category> <name>` - Switch to a specific agent (e.g., `/agent use analysis Code-Reviewer`)
- `/agent view <category> <name>` - View details of a specific agent
- `/agent delete <category> <name>` - Delete a custom agent

**File Operations:**
- `/read <filepath>` - Read and display a file
- `/write <filepath>` - Write content to a file

**Execution & Search:**
- `/exec <command>` - Execute a shell command
- `/search <query>` - Search the web

**Session Management:**
- `/save [name]` - Save current conversation to JSON file (auto-names if no name provided)
- `/load <name>` - Resume a saved session
- `/sessions` - List all saved sessions

**Keyboard shortcuts:**
- `ESC` - Cancel input/exit prompt without submitting
- `Ctrl+C` - Interrupt/cancel the current operation (chat response, command execution, or search)
- `Ctrl+D` - Exit the application (EOF)
- Arrow keys - Navigate through input history (powered by prompt_toolkit)

### Manage Configuration

```bash
# Interactive setup wizard (first-time setup)
madison config setup

# Show current configuration
madison config show

# Set a configuration value
madison config set default_model "claude-3-sonnet"

# Reset to defaults
madison config reset
```

## Strategy-Based Model Registration

Madison uses a **strategy-based model system** to organize different models for different tasks. This allows you to register models for semantic strategies like "thinking", "planning", "analysis", etc., and then use them with the `/ask` command.

### Example Configuration

In your `~/.madison/config.yaml`:

```yaml
api_key: "your-api-key"
models:
  default: openrouter/auto           # Used for regular chat
  thinking: claude-opus              # Deep reasoning and analysis
  planning: gpt-4-turbo              # Strategic planning
  summarization: gpt-3.5-turbo       # Quick summaries (faster/cheaper)
  tools: claude-sonnet-4             # For agent tool execution
```

### Using Strategies with `/ask`

```bash
# Use the 'thinking' strategy (runs claude-opus)
/ask thinking "What are the implications of quantum computing?"

# Use the 'planning' strategy (runs gpt-4-turbo)
/ask planning "Create a project roadmap for 2025"

# Use the 'summarization' strategy (runs gpt-3.5-turbo)
/ask summarization "Condense this article into 3 bullet points"

# Direct model specification (bypasses strategy registration)
/ask model=gpt-4 "Quick question about syntax"
```

### Managing Strategies

```bash
# Show all registered strategies and their models
/model

# Register a new strategy (in chat)
/model thinking claude-3.5-sonnet

# Change default model (used for regular chat)
/model default gpt-4
```

**Benefits:**
- **Semantic clarity** - Commands express intent ("thinking", "planning") not implementation
- **Easy experimentation** - Swap models without changing commands
- **Cost optimization** - Use cheaper models for simple tasks, expensive ones for complex reasoning
- **Future-proof** - Ready for agent integration where agents can override these strategies

## Agent Management

Madison supports creating and using custom agents - specialized AI personas with custom prompts, model preferences, and tool restrictions.

### Built-in Agent Templates

Madison comes with 5 built-in agent templates covering common use cases:

1. **Code Reviewer** (analysis) - Reviews code for quality, security, and best practices
2. **Technical Writer** (writing) - Creates technical documentation and API documentation
3. **Security Auditor** (analysis) - Audits code and systems for security vulnerabilities
4. **Debugging Assistant** (development) - Helps debug code issues and solve programming problems
5. **Documentation Improver** (writing) - Improves existing documentation for clarity and completeness
6. **Feature Planner** (development) - Helps plan features and break down complex work

### Creating Custom Agents

```bash
# Start the interactive agent creation wizard
/agent create

# The wizard will guide you through:
# 1. Choose starting point (blank or template)
# 2. Enter agent name, category, and description
# 3. Set optional model, temperature, and max_tokens
# 4. Specify which tools the agent can use (optional)
# 5. Choose storage scope (user ~/.madison/agents or project ./.madison/agents)
# 6. Enter or edit the system prompt
```

### Using Agents

```bash
# List all available agents
/agent

# List agents in a specific category
/agent list writing

# View details of an agent
/agent view analysis "Code-Reviewer"

# Switch to an agent
/agent use analysis "Code-Reviewer"

# Once an agent is active, all subsequent requests use that agent's:
# - Custom system prompt
# - Model preference (if specified)
# - Temperature and max_tokens settings (if specified)
# - Restricted tool set (if specified)

# Clear the active agent and return to default behavior
/agent use default default  # Or just restart the session
```

### Agent Storage

- **User scope**: Agents stored in `~/.madison/agents/` are available globally
- **Project scope**: Agents stored in `./.madison/agents/` are only available in that project
- **File format**: Agents are stored as markdown files with YAML frontmatter for easy editing

Example agent file structure:
```yaml
---
name: My Custom Agent
category: analysis
description: Does custom analysis
version: 1.0
model: claude-opus
temperature: 0.8
max_tokens: 2000
tools:
  - read_file
  - search_web
---

You are a specialized analyst...
[Rest of the system prompt]
```

### Agent Features

**Custom Models**: Agents can specify a different model than the default:
```bash
/agent create
# Choose "2. Agent from template"
# Customize the model field to use a specific model
```

**Tool Restrictions**: Agents can be restricted to specific tools:
```bash
# During creation, specify tools as comma-separated list
# Example: read_file,search_web,execute_command
# Leave blank to allow all tools
```

**Temperature & Max Tokens**: Fine-tune model behavior per agent:
```bash
# Set custom temperature for creative agents (0.0-2.0)
# Set custom max_tokens for concise or verbose responses
```

## Project Scope and Security

Madison uses a **project scope** concept to restrict file and command operations by default:

- **Project Directory**: The directory where Madison is launched becomes the project scope
- **Scope Location**: `./.madison/config.yaml` (created in the launch directory)
- **Default Behavior**: All file and command operations are restricted by default
- **Whitelist Model**: Users must explicitly allow operations outside the project directory
- **User Prompting**: When an operation is denied, Madison prompts the user with three options:
  1. **Yes, this once** - Allow the operation for this request only
  2. **Yes, always** - Allow and save to `./.madison/config.yaml` for future requests
  3. **No** - Deny the operation

### Permission Rules

File and command operations are controlled by permission rules in `./.madison/config.yaml`:

```yaml
permissions:
  file_operations:
    always_allow:
      - .          # Current directory (always allowed)
      - ./src      # Example: allow src directory
  command_execution:
    allowed_paths:
      - .          # Current directory (always allowed)
      - ./scripts  # Example: allow scripts directory
```

### Project vs User Configuration

- **User Config** (`~/.madison/config.yaml`): Global settings (API key, models, temperature, etc.)
- **Project Config** (`./.madison/config.yaml`): Per-project security rules (permissions, file/command restrictions)

## Project Structure

```
madison/
├── src/
│   └── madison/
│       ├── api/
│       │   ├── client.py         # OpenRouter API client
│       │   └── models.py         # Data models
│       ├── core/
│       │   ├── config.py         # Configuration management
│       │   ├── permissions.py    # Permission checking and prompting
│       │   ├── session.py        # Conversation session
│       │   └── context.py        # Context management (future)
│       ├── tools/
│       │   ├── file_ops.py       # File operations (with permission checks)
│       │   ├── command_exec.py   # Command execution (with permission checks)
│       │   └── web_search.py     # Web search
│       ├── cli.py                # Main CLI interface
│       └── exceptions.py         # Custom exceptions
├── tests/                        # Test suite
├── .venv/                        # Virtual environment
├── README.md
├── PLAN.md                       # Implementation plan
└── pyproject.toml               # Project metadata
```

## Development

### Running Tests

```bash
pytest
pytest -v  # Verbose
pytest --cov  # With coverage
```

### Code Quality

```bash
# Format code
black madison tests

# Check imports
isort madison tests

# Lint
flake8 madison tests

# Type checking
mypy madison
```

## Dependencies

- **typer** - CLI framework
- **httpx** - Async HTTP client with streaming
- **pydantic** - Data validation
- **pyyaml** - Configuration parsing
- **rich** - Terminal formatting
- **ddgs** - Web search via DuckDuckGo

## Roadmap

### ✅ Phase 1 - MVP (Complete)
- Basic configuration system
- OpenRouter API client with streaming
- Interactive REPL with chat
- File operations (`/read`, `/write`)

### ✅ Phase 2 - Tools (Complete)
- `/exec` command for bash execution
- `/search` command for web search
- Tool orchestration

### ✅ Phase 3 - Polish (Complete)
- Session persistence with `/save` and `/load` commands
- Command and query history tracking
- Configuration wizard (`madison config setup`)
- `/sessions` command to list saved conversations

### ✅ Phase 4 - Agent Tool Calling (Complete)
- **Structured tool calling** instead of regex parsing
- **Multi-turn conversations** with automatic tool execution
- **Agent-based intent processing** with `Agent.process_intent()`
- **Tool executor** mapping calls to file operations, command execution, and web search
- **Provider-agnostic** using pure OpenAI format for OpenRouter
- **Permission system integration** with user prompting
- **Multi-step workflows** - agents can chain tool calls together
- **Tested and verified** with real tool execution (mkdir, ls, etc.)

**Key Improvements:**
- Model-generated structured tool calls (deterministic)
- Support for multi-step workflows where model understands results
- Robust error handling and validation
- Zero regex parsing fragility
- Works across all OpenRouter-compatible models

### ✅ Phase 5 - Agent Management System (Complete)
- **Agent Definitions** - `AgentDefinition` dataclass for structured agent storage
- **Agent Manager** - CRUD operations for creating, reading, updating, deleting agents
- **YAML Frontmatter** - Agent metadata and system prompts stored as markdown files
- **Built-in Templates** - 5 pre-configured agent templates (Code Reviewer, Technical Writer, Security Auditor, Debugging Assistant, Documentation Improver, Feature Planner)
- **Interactive Wizard** - `/agent create` command with template selection and configuration
- **Agent Listing** - `/agent list` with category filtering and details view
- **Agent Switching** - `/agent use` to load agents with custom prompt, model, temperature, max_tokens, and tools
- **Scope Management** - User-global or project-local agent storage
- **Tool Restrictions** - Agents can specify allowed tools to limit API capabilities
- **Model Override** - Agents can specify custom models different from default
- **Parameter Tuning** - Per-agent temperature and max_tokens settings

**Key Features:**
- Agent system integrated with existing `Agent` class for seamless tool calling
- Agents customize model selection, temperature, max_tokens, and tool access
- User and project scopes for agent storage
- Human-readable YAML frontmatter format for easy editing
- Full CRUD CLI support with intuitive commands
- Interactive creation wizard with template support

## License

**Slackwerks Software License** - "Steal Shamelessly and Give No Credit" Edition

Madison is released under the Slackwerks License. In short:

- ✅ Do whatever you want with this code (copy, modify, sell, etc.)
- ✅ No attribution required (but appreciated!)
- ✅ No warranty whatsoever
- ✅ Use it to get a promotion, impress your boss, build a startup
- ✅ We really don't care (in a friendly way)

For the full license terms, see [LICENSE.md](LICENSE.md).

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests. Under the Slackwerks License, you can also fork this code and claim it as your own (though we'd appreciate if you didn't 😄).
