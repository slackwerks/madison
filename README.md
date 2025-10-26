# Madison - OpenRouter CLI

A pure Python CLI application for interacting with OpenRouter models, similar to Claude Code but focused on OpenRouter integration.

## Features

- **Interactive REPL chat** with streaming responses
- **Model selection** - Choose from available OpenRouter models
- **File operations** - Read and write files with `@read` and `@write` commands
- **Conversation history** - Maintain context across multiple messages
- **Configuration management** - Environment variables or YAML config files
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
- `/history` - Show conversation history
- `/system` - Show/set system prompt
- `/model` - Show current model

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
- `ESC` - Cancel the current operation (chat response, command execution, or search)

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
│       │   ├── session.py        # Conversation session
│       │   └── context.py        # Context management (future)
│       ├── tools/
│       │   ├── file_ops.py       # File operations
│       │   ├── command_exec.py   # Command execution
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
