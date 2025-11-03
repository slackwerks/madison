# Madison Project - Model/Agent Architecture Summary

## Project Overview

**Madison** is an OpenRouter CLI application with integrated agent support and tool calling capabilities. It's a feature-complete system for interacting with various LLM models through OpenRouter API, with sophisticated configuration options for model selection and agent-based task execution.

**Current Version:** Phase 5 Complete (Agent Management System Fully Implemented)

---

## 1. PROJECT STRUCTURE

```
madison/
├── src/madison/
│   ├── api/
│   │   ├── client.py              # OpenRouter API client with tool calling
│   │   ├── models.py              # API data models (Message, ToolCall, etc.)
│   │   └── tool_caller.py         # (Reference) Provider-specific handlers
│   │
│   ├── core/
│   │   ├── agent.py               # Agent class for intent processing & tool execution
│   │   ├── agent_registry.py      # AgentManager & AgentDefinition for CRUD ops
│   │   ├── agent_commands.py      # CLI commands for agent management
│   │   ├── config.py              # Config & ProjectConfig (XDG Base Directory)
│   │   ├── model_registry.py      # ModelRegistry for tool-calling capability tracking
│   │   ├── tools.py               # Tool definitions (execute_command, read_file, write_file, search_web)
│   │   ├── tool_executor.py       # ToolExecutor - maps tool calls to operations
│   │   ├── permissions.py         # PermissionManager for access control
│   │   ├── session.py             # Session - conversation state management
│   │   ├── session_manager.py     # SessionManager for saving/loading conversations
│   │   └── history.py             # HistoryManager for command history
│   │
│   ├── tools/
│   │   ├── file_ops.py            # File operations with permission checks
│   │   ├── command_exec.py        # Command execution with permission checks
│   │   └── web_search.py          # Web search via DuckDuckGo
│   │
│   ├── cli.py                     # Main CLI interface (REPL loop)
│   ├── exceptions.py              # Custom exceptions
│   └── utils/                     # Input handling, setup wizard, etc.
│
├── .madison/                      # Project-scoped configuration
│   ├── config.yaml                # Project permissions
│   └── agents/                    # Project-local agents
│
├── README.md                      # Feature documentation
├── CHECKPOINT.md                  # Development progress (all phases complete)
└── pyproject.toml                 # Package configuration
```

---

## 2. HOW MODELS ARE CURRENTLY CONFIGURED

### A. Configuration Sources (Priority Order)

1. **Environment Variable** (highest priority): `OPENROUTER_API_KEY`
2. **Config File**: `~/.config/madison/config.yaml` (XDG Base Directory)
   - Can also be in `$XDG_CONFIG_HOME/madison/config.yaml` if XDG_CONFIG_HOME set
   - Auto-migrates from old `~/.madison/config.yaml` location
3. **Built-in Defaults**: Fallback values in Config class

### B. Configuration Files

**User-Level Config** (`~/.config/madison/config.yaml`):
```yaml
api_key: "your-openrouter-api-key"
default_model: "openrouter/auto"
models:
  default: "openrouter/auto"              # Regular chat
  thinking: "claude-opus"                 # Deep reasoning
  planning: "gpt-4-turbo"                 # Strategic planning
  summarization: "gpt-3.5-turbo"         # Quick summaries
  tools: "claude-sonnet-4"                # Tool execution (fallback if needed)
system_prompt: "You are a helpful assistant."
temperature: 0.7
max_tokens: 2000
timeout: 30
history_size: 50
max_retries: 3
retry_initial_delay: 1.0
retry_backoff_factor: 2.0
```

**Project-Level Config** (`./.madison/config.yaml`):
```yaml
permissions:
  file_operations:
    always_allow:
      - .                # Current directory (always allowed)
      - ./src            # Example: allow src directory
  command_execution:
    allowed_paths:
      - .                # Current directory (always allowed)
      - ./scripts        # Example: allow scripts directory
```

### C. Model Configuration Code

**File**: `src/madison/core/config.py`

```python
class Config(BaseModel):
    api_key: str                          # Required - from env or file
    default_model: str = "openrouter/auto"
    models: Dict[str, str]                # Maps task types to model names
    system_prompt: str
    temperature: float = 0.7              # 0.0-2.0
    max_tokens: Optional[int] = None
    timeout: int = 30
    history_size: int = 50
    max_retries: int = 3
    retry_initial_delay: float = 1.0
    retry_backoff_factor: float = 2.0

    # Methods:
    def get_model(task_type: str = "default") -> str
    def set_model(model: str, task_type: str = "default") -> None
    @staticmethod
    def model_supports_tools(model: str) -> bool
    def save() -> None
```

### D. Environment Variable Handling

- `OPENROUTER_API_KEY`: API authentication key (highest priority)
- `XDG_CONFIG_HOME`: Override default config directory (respects XDG Base Directory Standard)
- If `XDG_CONFIG_HOME` not set, uses `~/.config/madison/`

---

## 3. HOW AGENTS ARE DEFINED AND CONFIGURED

### A. Agent Definition Structure

**File**: `src/madison/core/agent_registry.py`

```python
@dataclass
class AgentDefinition:
    name: str                         # "Code Reviewer"
    category: str                     # "analysis", "writing", "development"
    description: str                  # Human-readable description
    prompt: str                       # System prompt / instructions
    version: str = "1.0"
    model: Optional[str] = None       # Optional model override (e.g., "claude-opus")
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    tools: Optional[List[str]] = None # ["read_file", "search_web"] or None for all
    scope: str = "user"               # "user" or "project"
    
    @property
    def id -> str: "{category}/{name.lower()}"
    @property
    def file_path -> Path: Based on scope
    def to_markdown() -> str: YAML frontmatter + prompt
    def save() -> Path: Writes to markdown file
    @classmethod
    def from_file(Path) -> AgentDefinition: Parses markdown file
```

### B. Built-in Agent Templates

Six pre-configured agents available via `AGENT_TEMPLATES`:

1. **Code Reviewer** (analysis)
   - Reviews code for quality, security, and best practices
   - Tools: read_file, execute_command, search_web

2. **Technical Writer** (writing)
   - Creates technical documentation and API docs
   - Tools: read_file, write_file, search_web

3. **Security Auditor** (analysis)
   - Audits code and systems for vulnerabilities
   - Tools: read_file, execute_command, search_web

4. **Debugging Assistant** (development)
   - Helps debug code issues and solve problems
   - Tools: read_file, execute_command, write_file

5. **Documentation Improver** (writing)
   - Improves existing documentation for clarity
   - Tools: read_file, write_file, search_web

6. **Feature Planner** (development)
   - Plans features and breaks down complex work
   - Tools: read_file, search_web, write_file

### C. Agent Manager (CRUD Operations)

**File**: `src/madison/core/agent_registry.py`

```python
class AgentManager:
    def __init__(self):
        # XDG-compliant user agents directory
        self.user_agents_dir = Path.home() / ".config" / "madison" / "agents"
        # Project-local agents directory
        self.project_agents_dir = Path.cwd() / ".madison" / "agents"
    
    def list_agents(scope=None, category=None) -> List[AgentDefinition]
    def get_agent(category: str, name: str, scope=None) -> Optional[AgentDefinition]
    def create_agent(agent: AgentDefinition) -> Path
    def update_agent(agent: AgentDefinition) -> Path
    def delete_agent(category: str, name: str, scope: str) -> bool
    def get_categories(scope=None) -> List[str]
```

### D. Agent Storage Format

Agents stored as markdown files with YAML frontmatter:

```yaml
---
name: My Custom Agent
category: analysis
description: Custom analysis agent
version: 1.0
scope: user
model: claude-opus              # Optional
temperature: 0.8                # Optional
max_tokens: 2000                # Optional
tools:                          # Optional - restrict to specific tools
  - read_file
  - search_web
---

You are a specialized analyst...
[Rest of the system prompt goes here]
```

### E. Agent Scopes

- **User Scope**: `~/.config/madison/agents/` (XDG-compliant)
  - Available globally across all Madison sessions
  - Stored in XDG Base Directory location
  
- **Project Scope**: `./.madison/agents/` (relative to current directory)
  - Only available when Madison is run from that project directory
  - Useful for project-specific agents

---

## 4. WHERE MODEL SELECTION HAPPENS

### A. Default Chat Flow

**File**: `src/madison/cli.py` - `_handle_chat()` function

```
User Input
    ↓
Session.add_message("user", input)
    ↓
agent.process_intent(input) [if agent is NOT active]
    OR
client.chat_stream(..., model=config.default_model) [if NO agent active]
    ↓
Response displayed to user
```

Model used: `config.default_model` or from agent config

### B. Strategy-Based Model Selection

**File**: `src/madison/cli.py` - `/ask` command handler

```
/ask <strategy|model=MODEL> <prompt>
    ↓
If "model=gpt-4": Use specified model directly
If "thinking": Use config.models["thinking"]
    ↓
client.chat_stream(..., model=specific_model)
    ↓
Response displayed to user
```

Available strategies configured in `config.models`:
- default
- thinking
- planning
- summarization
- tools
- custom (user-defined)

### C. Agent-Based Model Selection

**File**: `src/madison/core/agent.py` - `_get_tool_model()` method

```python
def _get_tool_model(self) -> str:
    """Fallback logic for tool execution model selection:"""
    1. If active agent has custom model → Use agent's model
    2. If default model supports tools → Use default model
    3. If 'tools' model configured → Use tools model
    4. Otherwise → Use default model anyway (may fail)
    
    Returns: Model identifier string
```

### D. Tool Execution Model Selection

When agent executes tools via `process_intent()`:

1. **Get Tool Model** (via `_get_tool_model()`)
   - Check agent-specific model first
   - Check ModelRegistry for tool support
   - Fall back to "tools" model if configured
   - Fall back to default model

2. **Call with Tool Loop**
   ```
   client.call_with_tool_loop(
       initial_message=user_prompt,
       model=tool_model,  # Selected model
       tools=[...],
       tool_executor=executor.execute,
       temperature=agent.temperature,  # If agent-specific
       max_tokens=agent.max_tokens,    # If agent-specific
   )
   ```

### E. CLI Command for Model Management

**File**: `src/madison/cli.py` - `/model` command

```
/model                              # Show all configured models
/model default <model>              # Set default model
/model <strategy> <model>           # Set model for strategy
/model thinking claude-opus         # Set thinking model
/model tools gpt-4                  # Set tools fallback model
```

Changes are reflected in `config.models` dict (not persisted to file unless /config save is used).

---

## 5. EXISTING MODEL ROUTING AND FALLBACK MECHANISMS

### A. Model Capability Registry

**File**: `src/madison/core/model_registry.py`

Maintains three categories of models:

```python
class ModelRegistry:
    TOOL_CALLING_MODELS: Set[str]          # Known to support tools
    EXPERIMENTAL_TOOL_MODELS: Set[str]     # Limited/experimental support
    NO_TOOL_MODELS: Set[str]               # Known NOT to support tools
    
    @classmethod
    def supports_tools(model: str) -> bool:
        # Returns: True if model supports tool calling
        # Strategy: 
        # 1. Check exact match
        # 2. Check prefix match (e.g., "openai/gpt-4" matches "openai/gpt-4-turbo")
        # 3. Check experimental list
        # 4. Check NO_TOOL list (return False)
        # 5. Default: Assume tools supported (optimistic)
    
    @classmethod
    def register_model(model: str, supports_tools: bool) -> None:
        # Register/update a model's tool calling capability
```

**Supported Tool-Calling Models**:
- OpenAI: gpt-4, gpt-4-turbo, gpt-3.5-turbo, etc.
- Anthropic Claude: claude-3-opus, claude-3-sonnet, claude-3.5-sonnet, claude-sonnet-4, etc.
- Google: gemini-pro, palm-2
- Meta Llama: llama-2-70b-chat, llama-2-13b-chat, etc.
- Mistral: mistral-7b-instruct, mistral-medium, mistral-large
- Others: Nous Hermes, DBRX, etc.

### B. Tool Model Fallback Logic

When agent needs to execute tools:

```
Tool Execution Model Selection
├── Agent has custom model?
│   └─→ Use agent's model ✓
├── Default model supports tools?
│   └─→ Use default model ✓
├── "tools" model configured in config?
│   └─→ Use tools model (if it supports tools) ✓
└── Default model doesn't support tools?
    ├─→ Log warning
    └─→ Try anyway (may fail gracefully)
```

### C. Retry and Error Handling

**File**: `src/madison/api/client.py`

API client has automatic retry logic:

```python
max_retries: int = 3                    # Default 3 retries
retry_initial_delay: float = 1.0        # Start with 1 second
retry_backoff_factor: float = 2.0       # Double delay each retry
_is_retryable_error(status_code) -> bool:
    return status_code in (429, 503, 504)  # Rate limit, service unavailable, gateway timeout
```

### D. Tool Calling Loop Implementation

**File**: `src/madison/api/client.py` - `call_with_tool_loop()` method

```
Tool Calling Loop (max 10 iterations)
├─ Iteration 1:
│  ├─ Send: [initial user message] + tools
│  ├─ Get: Response + tool_calls (if any)
│  └─ If no tools → Return response
├─ Iteration 2+:
│  ├─ Execute tools locally
│  ├─ Add tool results to messages
│  ├─ Send: [conversation history] + [tool results] + tools
│  ├─ Get: Response + tool_calls (if any)
│  └─ If no tools → Return response
└─ If max iterations reached:
   └─ Return last response (safety limit)
```

**Message Format**: Pure OpenAI format (OpenRouter handles provider conversion)

### E. Permission-Based Fallback

**File**: `src/madison/core/permissions.py`

When tool execution is restricted:

```
Tool Execution Request
├─ Check permission for operation
├─ If ALLOWED:
│  └─→ Execute tool
├─ If DENIED (default):
│  ├─ Prompt user: "Yes once" / "Yes always" / "No"
│  ├─ If "Yes once":
│  │  └─→ Execute and continue
│  ├─ If "Yes always":
│  │  ├─→ Save to ./.madison/config.yaml
│  │  └─→ Execute and continue
│  └─ If "No":
│     └─→ Return error to model
```

---

## 6. CONFIGURATION MANAGEMENT COMMANDS

### A. Config Subcommands

```bash
madison config setup    # Interactive setup wizard
madison config show     # Display current configuration
madison config set <key> <value>  # Set specific value
madison config reset    # Reset to defaults
```

### B. Agent Management Commands (in REPL)

```bash
/agent                          # List all agents
/agent list [category]          # List agents in category
/agent templates                # Show built-in templates
/agent create                   # Interactive wizard
/agent use <category> <name>   # Switch to agent
/agent view <category> <name>  # View agent details
/agent delete <category> <name># Delete agent
```

### C. Model Management Commands (in REPL)

```bash
/model                          # Show all configured models
/model default <model>          # Set default model
/model thinking <model>         # Set thinking model
/model <strategy> <model>       # Set model for strategy
/model-list [search_term]       # Search available OpenRouter models
/model-list series=<series>     # List models by series
```

---

## 7. KEY PATTERNS AND FLOW DIAGRAMS

### A. Regular Chat Flow (No Agent Active)

```
User Input
    ↓
Session.add_message("user", input)
    ↓
client.chat_stream(
    messages=[...],
    model=config.default_model,  ← DEFAULT MODEL
    temperature=config.temperature,
    max_tokens=config.max_tokens,
)
    ↓
Response → Display + Add to session
```

### B. Agent-Based Flow (Agent Active)

```
User Input
    ↓
Session.add_message("user", input)
    ↓
agent.process_intent(input)
    ├─ Get tool-capable model via _get_tool_model()
    ├─ Filter agent-restricted tools (if any)
    ├─ Call client.call_with_tool_loop(
    │   model=tool_model,  ← AGENT OR TOOLS MODEL
    │   tools=[...],       ← AGENT-FILTERED OR ALL
    │   temperature=agent.temperature if set,  ← AGENT-SPECIFIC
    │   max_tokens=agent.max_tokens if set,    ← AGENT-SPECIFIC
    ├─ Loop:
    │  ├─ Get response + tool_calls
    │  ├─ Execute tools (ToolExecutor)
    │  ├─ Feed results back to model
    │  └─ Repeat until response (no tools)
    └─ Return final response
    ↓
Response → Display + Add to session
```

### C. Strategy-Based Model Selection (/ask command)

```
/ask <strategy|model=MODEL> <prompt>
    ↓
Parse strategy or direct model spec
    ↓
If "model=gpt-4":
    specific_model = "gpt-4"
Else:
    specific_model = config.models[strategy]  ← STRATEGY LOOKUP
    ↓
client.chat_stream(
    messages=[...],
    model=specific_model,  ← STRATEGY-SELECTED OR DIRECT MODEL
)
    ↓
Response → Display
```

---

## 8. SUMMARY TABLE: MODEL CONFIGURATION SOURCES

| Context | Source | Config Key | Priority |
|---------|--------|-----------|----------|
| Default Chat | Config file | `default_model` | 2 |
| Tool Execution | Agent config OR Config file | `agent.model` or `config.models["tools"]` | 1 |
| Strategy-based (/ask) | Config file | `config.models[strategy]` | 2 |
| Temperature | Agent OR Config | `agent.temperature` or `config.temperature` | 1 |
| Max Tokens | Agent OR Config | `agent.max_tokens` or `config.max_tokens` | 1 |
| Tool Restrictions | Agent config | `agent.tools` (list or None) | 1 |
| API Key | Environment OR Config file | `OPENROUTER_API_KEY` or `config.api_key` | 1 |

---

## 9. CODE ENTRY POINTS

### Main CLI Entry
- **File**: `src/madison/cli.py:main()`
- **Loads**: Config → Creates Agent → Starts REPL

### Agent Processing
- **File**: `src/madison/core/agent.py:Agent.process_intent()`
- **Called from**: `src/madison/cli.py:_handle_chat()`
- **Does**: Selects model, executes tools, returns response

### Model Selection Logic
- **Agent Model**: `src/madison/core/agent.py:_get_tool_model()`
- **Default Model**: `src/madison/core/config.py:Config.default_model`
- **Strategy Models**: `src/madison/core/config.py:Config.models[task_type]`

### Tool Capability Registry
- **File**: `src/madison/core/model_registry.py:ModelRegistry.supports_tools()`
- **Usage**: Agent uses this to decide if fallback "tools" model is needed

---

## 10. FUTURE EXTENSIBILITY

Current architecture supports:

1. **Easy Model Swapping**: Change `config.models[strategy]` at runtime
2. **Agent Customization**: Create custom agents with specific models, temps, tool restrictions
3. **Tool Adding**: New tools can be added to `src/madison/core/tools.py` and ToolExecutor
4. **Provider Switching**: OpenRouter proxy supports any provider (could replace with native APIs)
5. **Fallback Strategies**: ModelRegistry makes it easy to add fallback logic

---

## ARCHITECTURE CONCLUSION

Madison uses a **multi-level model configuration system**:

1. **Global Level**: User config with default model + task-specific models
2. **Session Level**: Agent definitions with optional model overrides
3. **Command Level**: Direct model specification via /ask or /model commands
4. **Execution Level**: Automatic fallback if selected model doesn't support tools

This creates a flexible system where models can be swapped at multiple levels without code changes, while maintaining sensible defaults and fallbacks for production use.
