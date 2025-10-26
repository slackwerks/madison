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
2. **Configuration file**: `~/.madison/config.yaml`
3. **Built-in defaults**

### Setup

```bash
# Option 1: Set environment variable
export OPENROUTER_API_KEY="your-api-key-here"

# Option 2: Create config file
mkdir -p ~/.madison
cat > ~/.madison/config.yaml << EOF
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
- `/model` - Show/set models registered for different functions
- `/ask <function> <prompt>` - Send a prompt to a registered function (e.g., `/ask thinking "What is 2+2?"`)
- `/ask model=<MODEL> <prompt>` - Send a prompt to a specific model directly
- `/model-list <search_term>` - Search available OpenRouter models (e.g., `/model-list gpt` or `/model-list claude`)
- `/model-list series=<series>` - List models by series (e.g., `/model-list series=gpt` or `/model-list series=claude`)

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

## Function-Based Model Registration

Madison uses a **function-based model system** to organize different models for different tasks. This allows you to register models for semantic functions like "thinking", "planning", "analysis", etc., and then use them with the `/ask` command.

### Example Configuration

In your `~/.madison/config.yaml`:

```yaml
api_key: "your-api-key"
models:
  default: openrouter/auto           # Used for regular chat
  thinking: claude-opus              # Deep reasoning and analysis
  planning: gpt-4-turbo              # Strategic planning
  summarization: gpt-3.5-turbo       # Quick summaries (faster/cheaper)
  bork: dolphin-mistral              # Custom function for your workflow
```

### Using Functions with `/ask`

```bash
# Use the 'thinking' function (runs claude-opus)
/ask thinking "What are the implications of quantum computing?"

# Use the 'planning' function (runs gpt-4-turbo)
/ask planning "Create a project roadmap for 2025"

# Use the 'summarization' function (runs gpt-3.5-turbo)
/ask summarization "Condense this article into 3 bullet points"

# Direct model specification (bypasses function registration)
/ask model=gpt-4 "Quick question about syntax"
```

### Managing Functions

```bash
# Show all registered functions and their models
/model

# Register a new function (in chat)
/model thinking claude-3.5-sonnet

# Change default model (used for regular chat)
/model default gpt-4
```

**Benefits:**
- **Semantic clarity** - Commands express intent ("thinking", "planning") not implementation
- **Easy experimentation** - Swap models without changing commands
- **Cost optimization** - Use cheaper models for simple tasks, expensive ones for complex reasoning
- **Future-proof** - Ready for agent integration where agents can override these functions

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

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.
