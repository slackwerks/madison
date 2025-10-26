# Madison - Implementation Plan

## 1. Project Structure

```
madison/
├── madison/
│   ├── __init__.py
│   ├── cli.py                 # Main CLI entry point & REPL
│   ├── api/
│   │   ├── client.py          # OpenRouter API client
│   │   └── models.py          # Data models for API
│   ├── core/
│   │   ├── config.py          # Configuration management
│   │   ├── session.py         # Conversation session management
│   │   └── context.py         # Context/state management
│   ├── tools/
│   │   ├── file_ops.py        # File reading/writing
│   │   ├── command_exec.py    # Bash command execution
│   │   └── web_search.py      # Web search integration
│   ├── utils/
│   │   ├── logger.py          # Logging utilities
│   │   └── prompts.py         # System prompts & templates
│   └── exceptions.py          # Custom exceptions
├── tests/
│   ├── test_api.py
│   ├── test_cli.py
│   └── test_tools.py
├── setup.py / pyproject.toml
├── README.md
└── .gitignore
```

## 2. Tech Stack

- **CLI Framework**: `Typer` (modern, intuitive, with async support)
- **HTTP Client**: `httpx` (async-first, good streaming support)
- **Config**: `pydantic` (validation) + `pyyaml`
- **Terminal UI**: `rich` (for formatted output)
- **Web Search**: `duckduckgo-search` (no API key required, lightweight)

## 3. Core Components

### Configuration System
- Priority: Environment variable → Config file → Defaults
- Config file: `~/.madison/config.yaml`
- Settings: API key, default model, system prompt, behavior flags

### OpenRouter API Client
- Authentication via headers
- Support streaming responses (for better UX)
- Model enumeration
- Error handling & retries
- Request/response logging

### CLI Interface
- Interactive REPL mode (default)
- Commands: `@read`, `@write`, `@exec`, `@search`, `@model`, `@history`, `@clear`
- Multi-line input support
- Syntax highlighting

### Conversation Management
- Maintain message history (current session)
- System prompt injection
- Token counting (optional, for budget awareness)
- Session persistence (optional)

### Tool Integration
- File ops with safety checks (no dangerous paths)
- Command execution with timeout & error capture
- Web search via DuckDuckGo API
- Tool calls parsed from model responses

## 4. Implementation Phases

### Phase 1 - MVP
- Basic configuration system
- OpenRouter API client with streaming
- Simple REPL with chat
- `@read` and `@write` file commands

### Phase 2 - Tools
- `@exec` for bash commands
- `@search` for web search
- Tool calling orchestration

### Phase 3 - Polish
- Session persistence
- Command history
- Better error messages
- Configuration wizard

## 5. OpenRouter Integration Details

- Use `https://openrouter.ai/api/v1/chat/completions`
- Send `Authorization: Bearer YOUR_API_KEY`
- Include app metadata in headers
- Parse streaming tokens vs complete responses
- Handle rate limits gracefully

## 6. Key Design Decisions

- **Async throughout**: Better for streaming and tool execution
- **Tool-as-commands**: Users use `@command` syntax instead of natural language
- **Session-based**: Maintain context for multi-turn conversations
- **Safe defaults**: Restrict file ops to project directory unless explicit
