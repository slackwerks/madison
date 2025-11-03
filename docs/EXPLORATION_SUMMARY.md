# Madison Codebase Exploration - Complete Summary

## What is Madison?

Madison is a **pure Python CLI for OpenRouter models** with sophisticated agent support and tool calling. It's a feature-complete application (all 5 phases complete) that provides:

- Interactive REPL chat with streaming responses
- Model selection and strategy-based routing
- Agent system with customizable prompts, model overrides, and tool restrictions
- Tool calling (file operations, command execution, web search)
- Session persistence and command history
- XDG Base Directory compliance for configuration

---

## 1. PROJECT STRUCTURE OVERVIEW

Madison has a clean, modular architecture:

```
src/madison/
├── api/              - OpenRouter API integration
│   ├── client.py     - HTTP client with tool calling (538 lines)
│   └── models.py     - API data models
├── core/             - Core business logic
│   ├── agent.py      - Agent class with intent processing (173 lines)
│   ├── agent_registry.py - Agent CRUD operations (478 lines)
│   ├── agent_commands.py - CLI commands for agents
│   ├── config.py     - Configuration management (289 lines)
│   ├── model_registry.py - Model capability tracking (138 lines)
│   ├── tools.py      - Tool definitions (164 lines)
│   ├── tool_executor.py - Tool execution mapper
│   └── permissions.py - Permission checking
├── tools/            - Tool implementations
│   ├── file_ops.py   - File operations with permissions
│   ├── command_exec.py - Command execution with permissions
│   └── web_search.py - Web search via DuckDuckGo
├── cli.py            - Main REPL interface (900+ lines)
└── utils/            - Input handling, setup wizard, etc.
```

---

## 2. HOW MODELS ARE CONFIGURED

Madison uses a **multi-level configuration system**:

### Level 1: User Configuration
Location: `~/.config/madison/config.yaml` (XDG compliant)

```yaml
api_key: "sk-or-v1-..."
default_model: "openrouter/auto"
models:
  default: "openrouter/auto"
  thinking: "claude-opus"
  planning: "gpt-4-turbo"
  summarization: "gpt-3.5-turbo"
  tools: "claude-sonnet-4"
```

### Level 2: Project Configuration
Location: `./.madison/config.yaml` (permissions only)

```yaml
permissions:
  file_operations:
    always_allow: ["."]
  command_execution:
    allowed_paths: ["."]
```

### Level 3: Agent Configuration
Location: `~/.config/madison/agents/` or `./.madison/agents/`

Agents can override model, temperature, max_tokens, and tool restrictions per-agent.

### Level 4: CLI Commands
Runtime configuration via `/model` and `/ask` commands (not persisted).

### Configuration Priority
1. Environment variable `OPENROUTER_API_KEY` (highest priority)
2. Config file `~/.config/madison/config.yaml`
3. Built-in defaults
4. XDG Base Directory support with auto-migration from old location

---

## 3. HOW AGENTS ARE DEFINED

### Agent Definition Structure
Agents are `AgentDefinition` dataclass instances with:
- `name`, `category`, `description` (metadata)
- `prompt` (system prompt / instructions)
- `model` (optional - overrides default for tool execution)
- `temperature`, `max_tokens` (optional - per-agent tuning)
- `tools` (optional list - restricts available tools)
- `scope` ("user" for global, "project" for local)

### Storage Format
Agents stored as markdown files with YAML frontmatter:

```yaml
---
name: Code Reviewer
category: analysis
model: claude-opus
temperature: 0.7
max_tokens: 4000
tools:
  - read_file
  - execute_command
  - search_web
---

You are an expert code reviewer...
[System prompt continues]
```

### Built-in Templates (6 included)
1. Code Reviewer (analysis)
2. Technical Writer (writing)
3. Security Auditor (analysis)
4. Debugging Assistant (development)
5. Documentation Improver (writing)
6. Feature Planner (development)

### Agent Scopes
- **User Scope**: `~/.config/madison/agents/` - available globally
- **Project Scope**: `./.madison/agents/` - only in that project directory

---

## 4. WHERE MODEL SELECTION HAPPENS

### Default Chat
Model: `config.default_model` (regular REPL chat)

### Strategy-Based Selection (/ask command)
```bash
/ask thinking "question"      # Uses config.models["thinking"]
/ask planning "prompt"        # Uses config.models["planning"]
/ask model=gpt-4 "prompt"     # Direct model specification
```

### Agent-Based Selection (Tool Execution)
When agent is active and processes intent:
1. Check if agent has custom `model` - use it
2. Check if default model supports tools - use it
3. Check if `tools` model configured - use it
4. Otherwise use default (may fail)

### Code Entry Points
- Default chat: `src/madison/cli.py:_handle_chat()` → `config.default_model`
- Strategy: `src/madison/cli.py:_handle_commands()` → `/ask` handler → `config.models[strategy]`
- Agent: `src/madison/core/agent.py:_get_tool_model()` → Fallback logic

---

## 5. MODEL ROUTING AND FALLBACK MECHANISMS

### Tool Calling Capability Registry
File: `src/madison/core/model_registry.py`

Tracks models in three categories:
- `TOOL_CALLING_MODELS` (50+ models including Claude, GPT-4, Gemini, Llama, etc.)
- `EXPERIMENTAL_TOOL_MODELS` (limited support)
- `NO_TOOL_MODELS` (legacy/unsupported)

### Fallback Logic for Tool Execution
```
Agent requests tool execution
  ↓
Check: Does selected model support tools?
  ├─ YES → Use selected model ✓
  └─ NO → Check "tools" model
       ├─ Configured → Use tools model ✓
       └─ Not configured → Warning + use default (may fail)
```

### API Error Handling
- Automatic retries: 3 attempts
- Retryable status codes: 429 (rate limit), 503, 504
- Exponential backoff: 1s → 2s → 4s

### Tool Calling Loop
Max 10 iterations to prevent infinite loops:
1. Send message + tools to model
2. Get response + tool calls
3. Execute tools locally
4. Send results back to model
5. Repeat until model returns final response (no tool calls)

---

## 6. CONFIGURATION MANAGEMENT COMMANDS

### User Configuration
```bash
madison config setup    # Interactive setup wizard
madison config show     # Display current config
madison config set key value  # Set specific value
madison config reset    # Reset to defaults
```

### Agent Management (in REPL)
```bash
/agent                          # List all agents
/agent list [category]          # List agents in category
/agent templates                # Show built-in templates
/agent create                   # Interactive creation wizard
/agent use <category> <name>   # Switch to agent
/agent view <category> <name>  # View agent details
/agent delete <category> <name># Delete agent
```

### Model Management (in REPL)
```bash
/model                          # Show all configured models
/model default <model>          # Set default model
/model <strategy> <model>       # Set model for strategy
/model-list [search_term]       # Search OpenRouter models
```

---

## 7. KEY CONFIGURATION PATTERNS

### Pattern 1: Multi-Strategy Model Configuration
Different models for different task types:
```yaml
models:
  default: "openrouter/auto"      # General chat
  thinking: "claude-opus"         # Complex reasoning
  planning: "gpt-4-turbo"         # Strategic planning
  summarization: "gpt-3.5-turbo"  # Quick summaries
  tools: "claude-sonnet-4"        # Tool execution
```

### Pattern 2: Agent Model Override
Agent specifies custom model for tool execution:
```yaml
---
name: Security Auditor
model: claude-opus    # Overrides default_model
---
```

### Pattern 3: Agent Tool Restrictions
Agent can restrict which tools it can use:
```yaml
---
tools:
  - read_file
  - search_web
---
```
(Agent won't have access to execute_command, write_file)

### Pattern 4: Temperature and Token Tuning
Per-agent customization:
```yaml
---
temperature: 0.3      # Low = deterministic security analysis
max_tokens: 3000      # More for detailed code review
---
```

---

## 8. ARCHITECTURE FLOW DIAGRAMS

### Regular Chat (No Agent)
```
User Input
    ↓
Session.add_message("user", input)
    ↓
client.chat_stream(model=config.default_model)
    ↓
Response → Display + Add to session
```

### Agent-Based with Tools
```
User Input
    ↓
agent.process_intent(input)
    ├─ Get tool-capable model
    ├─ Filter tools if restricted
    ├─ Call: client.call_with_tool_loop()
    │   ├─ Send: message + tools
    │   ├─ Loop: Get response + tool_calls
    │   ├─ Execute: tools locally
    │   ├─ Feed back: tool results
    │   └─ Until: no tool_calls
    └─ Return: final response
    ↓
Response → Display + Add to session
```

### Strategy-Based Selection (/ask)
```
/ask thinking "question"
    ↓
Parse strategy → Look up: config.models["thinking"]
    ↓
client.chat_stream(model=looked_up_model)
    ↓
Response → Display
```

---

## 9. CODE ENTRY POINTS FOR MODEL SELECTION

**Main Entry**: `src/madison/cli.py:main()`
- Loads Config
- Sets up REPL
- Creates Agent instance

**Default Chat**: `src/madison/cli.py:_handle_chat()`
- Calls `agent.process_intent()` if agent active
- Falls back to `client.chat_stream()` with default model

**Agent Logic**: `src/madison/core/agent.py:Agent.process_intent()`
- Calls `_get_tool_model()` for fallback selection
- Calls `client.call_with_tool_loop()` with selected model

**Model Fallback**: `src/madison/core/agent.py:Agent._get_tool_model()`
- Checks agent.model → config.default_model → config.models["tools"]

**Tool Capability**: `src/madison/core/model_registry.py:ModelRegistry.supports_tools()`
- Checks if model can do tool calling
- Used to decide if fallback "tools" model is needed

---

## 10. QUICK REFERENCE TABLE

| Aspect | Config Key | Location | Priority |
|--------|-----------|----------|----------|
| API Key | api_key | Env var or ~/.config/madison/config.yaml | Env > File |
| Default Model | default_model | ~/.config/madison/config.yaml | Config > Code |
| Strategy Models | models.thinking/planning/etc | ~/.config/madison/config.yaml | Config > Code |
| Tools Fallback | models.tools | ~/.config/madison/config.yaml | Config > Code |
| Agent Model | model | ~/.config/madison/agents/.../agent.md | Agent > Default |
| Temperature | temperature | Config or Agent | Agent > Config > Code |
| Max Tokens | max_tokens | Config or Agent | Agent > Config > Code |
| Tool Restrictions | tools | Agent | Agent only |
| Config Directory | $XDG_CONFIG_HOME | Environment or ~/.config | XDG > ~/.config |

---

## 11. WHAT'S COMPLETE (ALL 5 PHASES)

- Phase 1: Project scope & permissions
- Phase 2: Tool calling foundation
- Phase 3: Agent refactor with structured tool calling
- Phase 4: Tool calling polish & production ready
- Phase 5: Agent management system with CRUD, templates, and scopes

All features are **production-ready** with comprehensive error handling, logging, and fallbacks.

---

## FILE LOCATIONS (ABSOLUTE PATHS)

### Key Configuration Files
- `/home/user/work/madison/src/madison/core/config.py` - Configuration classes
- `/home/user/work/madison/src/madison/core/agent_registry.py` - Agent definitions and manager
- `/home/user/work/madison/src/madison/core/agent.py` - Agent class with model selection
- `/home/user/work/madison/src/madison/core/model_registry.py` - Model capability registry
- `/home/user/work/madison/src/madison/api/client.py` - OpenRouter API client
- `/home/user/work/madison/src/madison/cli.py` - Main CLI and REPL loop

### Key Documentation
- `/home/user/work/madison/README.md` - Feature documentation
- `/home/user/work/madison/CHECKPOINT.md` - Development progress
- `/home/user/work/madison/pyproject.toml` - Package configuration

### Project Structure Files
- `/home/user/work/madison/.madison/agents/` - Project-local agents
- `/home/user/work/madison/.madison/config.yaml` - Project permissions

---

## SUMMARY

Madison is a **well-architected, production-ready CLI** with:

1. **Flexible Configuration**: Environment variables, config files, CLI commands, agent overrides
2. **Intelligent Model Selection**: Strategy-based routing, agent overrides, tool-aware fallbacks
3. **Powerful Agent System**: 6 templates, CRUD operations, XDG-compliant storage, tool restrictions
4. **Robust Tool Calling**: Multi-turn conversation loops, automatic retries, error handling
5. **XDG Compliance**: Proper use of config directories with auto-migration

The architecture cleanly separates concerns (config, agents, models, tools, API) while providing sensible defaults and multiple fallback paths for production reliability.

