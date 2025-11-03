# Madison - Detailed Code Implementation Reference

## QUICK REFERENCE: KEY FILES AND THEIR RESPONSIBILITIES

### Configuration Layer
- **src/madison/core/config.py** (289 lines)
  - `Config` class: User-level configuration (models, API key, defaults)
  - `ProjectConfig` class: Project-level security settings
  - `ProjectPermissions` class: File/command execution whitelists
  - XDG Base Directory support with auto-migration

### Agent System
- **src/madison/core/agent_registry.py** (478 lines)
  - `AgentDefinition` dataclass: Agent metadata and prompt
  - `AgentManager` class: CRUD operations for agents
  - `AGENT_TEMPLATES` dict: 6 built-in agent definitions

- **src/madison/core/agent.py** (173 lines)
  - `Agent` class: Intent processing and tool execution
  - `_get_tool_model()`: Model selection fallback logic
  - `process_intent()`: Main async entry point for agent processing

- **src/madison/core/agent_commands.py** (Agent management CLI commands)
  - `handle_agent_command()`: Processes /agent commands
  - Agent creation wizard, listing, deletion, viewing

### Model System
- **src/madison/core/model_registry.py** (138 lines)
  - `ModelRegistry` class: Maintains model capability database
  - Tool-calling support tracking for 50+ models
  - Prefix matching for model variants

### Tool Execution
- **src/madison/core/tools.py** (164 lines)
  - Tool definitions: execute_command, read_file, write_file, search_web
  - OpenRouter-compatible schema format

- **src/madison/core/tool_executor.py** (120+ lines)
  - `ToolExecutor` class: Maps tool names to implementations
  - Handles both sync and async tool calls

### API Client
- **src/madison/api/client.py** (538 lines)
  - `OpenRouterClient` class: HTTP client with retries
  - `call_with_tool_loop()`: Multi-turn tool calling implementation
  - `call_with_tools()`: Single-turn tool calling with response parsing
  - Retry logic: 3 retries, exponential backoff (1s -> 2s -> 4s)

### CLI Interface
- **src/madison/cli.py** (900+ lines)
  - `main()`: Entry point
  - `_repl_loop()`: Main conversation loop
  - `_handle_commands()`: Command parsing and execution
  - `/model`, `/ask`, `/agent`, `/read`, `/write`, `/exec`, `/search`, etc.

---

## DETAILED: MODEL SELECTION FLOW

### 1. Configuration Loading

**Entry Point**: `src/madison/cli.py:main()`

```python
def main(...):
    config = Config.load()  # Priority: ENV > config.yaml > defaults
    model = model or config.default_model
    # ... initialize session and REPL
```

**Config.load() Priority**:
```python
@classmethod
def load(cls) -> "Config":
    # 1. Try migration from old ~/.madison location
    cls._migrate_from_old_location()
    
    # 2. Get API key from environment (highest priority)
    api_key = os.getenv("OPENROUTER_API_KEY")
    config_data = {}
    
    # 3. Try to load from config file (~/.config/madison/config.yaml)
    config_file = cls.config_file()
    if config_file.exists():
        with open(config_file, "r") as f:
            file_data = yaml.safe_load(f) or {}
            config_data.update(file_data)
    
    # 4. Environment variable overrides file
    if api_key:
        config_data["api_key"] = api_key
    elif "api_key" not in config_data:
        raise ConfigError("No OpenRouter API key found...")
    
    # 5. Create Config object with defaults for missing fields
    return cls(**config_data)
```

### 2. Regular Chat Flow

**Entry Point**: `src/madison/cli.py:_handle_chat()`

```python
async def _handle_chat(
    user_input: str,
    session: Session,
    client: OpenRouterClient,
    model: str,  # <- Current model
    config: Config,
    file_ops: FileOperations,
    cancel_token: CancellationToken,
    agent: Agent,  # <- Agent instance
):
    """Handle regular chat (after command parsing)"""
    
    # Add to session
    session.add_message("user", user_input)
    
    try:
        # Check if intent should be processed by agent
        success, response = await agent.process_intent(user_input)
        
        if success:
            # Agent handled it with tools
            console.print(f"[cyan]Agent: {response}[/cyan]")
            session.add_message("assistant", response)
        else:
            # No agent or agent can't handle - do regular chat
            console.print("[bold cyan]Assistant:[/bold cyan]", end=" ")
            
            response_text = ""
            async for token in client.chat_stream(
                messages=session.get_messages(),
                model=model,  # <- DEFAULT MODEL USED HERE
                temperature=config.temperature,
                max_tokens=config.max_tokens,
            ):
                console.print(token, end="", flush=True)
                response_text += token
            
            console.print()  # newline
            session.add_message("assistant", response_text)
            
    except Exception as e:
        logger.error(f"Chat error: {e}")
        console.print(f"[red]Error: {e}[/red]")
```

### 3. Agent-Based Model Selection

**Entry Point**: `src/madison/core/agent.py:Agent.process_intent()`

```python
async def process_intent(self, user_prompt: str) -> Tuple[bool, Optional[str]]:
    """Process user intent and execute tools as needed."""
    
    # Get available tools (may be filtered by agent)
    all_tools = get_tools_as_dicts()
    
    if self.active_agent and self.active_agent.tools:
        # Agent restricts tools - filter them
        tools = [tool for tool in all_tools 
                 if tool["function"]["name"] in self.active_agent.tools]
    else:
        tools = all_tools
    
    # KEY DECISION: SELECT MODEL FOR TOOL EXECUTION
    tool_model = self._get_tool_model()  # <- Fallback logic here
    
    # Get temperature/max_tokens (agent-specific if set)
    temperature = (self.active_agent.temperature 
                   if (self.active_agent and self.active_agent.temperature is not None) 
                   else self.config.temperature)
    max_tokens = (self.active_agent.max_tokens 
                  if (self.active_agent and self.active_agent.max_tokens) 
                  else self.config.max_tokens)
    
    # Execute tool calling loop
    response = await self.client.call_with_tool_loop(
        initial_message=user_prompt,
        model=tool_model,  # <- SELECTED MODEL
        tools=tools,
        tool_executor=self.tool_executor.execute,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    
    return True, response if response else None

def _get_tool_model(self) -> str:
    """Fallback logic for tool execution model selection."""
    
    # Priority 1: Agent-specific model
    if self.active_agent and self.active_agent.model:
        logger.debug(f"Using agent-specific model: {self.active_agent.model}")
        return self.active_agent.model
    
    # Priority 2: Default model if it supports tools
    default_model = self.config.default_model
    if self.config.model_supports_tools(default_model):
        logger.debug(f"Using default model for tools: {default_model}")
        return default_model
    
    # Priority 3: Dedicated "tools" model if configured
    tools_model = self.config.models.get("tools")
    if tools_model:
        logger.info(f"Default model '{default_model}' doesn't support tools, "
                   f"using: '{tools_model}'")
        return tools_model
    
    # Priority 4: Return default anyway (may fail)
    logger.warning(f"Default model '{default_model}' doesn't support tools "
                   f"and no 'tools' model configured. Tool execution may fail.")
    return default_model
```

### 4. Strategy-Based Model Selection (/ask command)

**Entry Point**: `src/madison/cli.py:_handle_commands()` - `/ask` block

```python
elif command == "/ask":
    if not args:
        # Show help
        console.print("[red]Usage: /ask <strategy|model=MODEL> <prompt>[/red]")
        # ...available strategies...
    else:
        # Parse strategy/model and prompt
        parts = args.split(maxsplit=1)
        if len(parts) == 2:
            strategy_or_model, prompt = parts
            
            # Determine which model to use
            specific_model = None
            strategy_label = None
            
            if strategy_or_model.startswith("model="):
                # Direct model specification: /ask model=gpt-4
                specific_model = strategy_or_model[6:]
                strategy_label = specific_model
            else:
                # Strategy lookup: /ask thinking "What is..."
                strategy_name = strategy_or_model
                if strategy_name in config.models:
                    specific_model = config.models[strategy_name]  # <- LOOKUP HERE
                    strategy_label = strategy_name
                else:
                    console.print(f"[red]Unknown strategy: {strategy_name}[/red]")
                    # Show available strategies
                    return True
            
            # Execute chat with specific model
            session.add_message("user", prompt)
            console.print(f"\n[bold cyan]Assistant ({strategy_label}):[/bold cyan]", 
                         end=" ")
            
            response_text = ""
            async for token in client.chat_stream(
                messages=session.get_messages(),
                model=specific_model,  # <- STRATEGY-SELECTED MODEL
                temperature=config.temperature,
                max_tokens=config.max_tokens,
            ):
                console.print(token, end="", flush=True)
                response_text += token
            
            console.print()
            session.add_message("assistant", response_text)
```

### 5. Model Capability Check

**File**: `src/madison/core/model_registry.py`

```python
class ModelRegistry:
    TOOL_CALLING_MODELS: Set[str] = {
        # OpenAI
        "openai/gpt-4", "openai/gpt-4-turbo", "openai/gpt-3.5-turbo",
        # Anthropic Claude
        "anthropic/claude-3-opus", "anthropic/claude-3-sonnet",
        "anthropic/claude-3.5-sonnet", "anthropic/claude-sonnet-4",
        # Google, Meta, Mistral, others...
    }
    
    EXPERIMENTAL_TOOL_MODELS: Set[str] = {
        "openchat/openchat-7b",
        "gryphe/mythomax-l2-13b",
    }
    
    NO_TOOL_MODELS: Set[str] = {
        "openai/text-davinci-003",  # Legacy
        "huggingface/meta-llama/llama-2-70b",
        # ...others that don't support tools
    }
    
    @classmethod
    def supports_tools(cls, model: str) -> bool:
        """Check if model supports tool calling."""
        
        # Exact match
        if model in cls.TOOL_CALLING_MODELS:
            return True
        
        # Prefix match (e.g., "openai/gpt-4" matches "openai/gpt-4-turbo")
        for supported in cls.TOOL_CALLING_MODELS:
            if model.startswith(supported):
                return True
        
        # Check experimental
        if model in cls.EXPERIMENTAL_TOOL_MODELS:
            return True
        
        # Check known unsupported
        if model in cls.NO_TOOL_MODELS:
            return False
        
        # Default: assume tools supported (optimistic)
        logger.warning(f"Model {model} not in registry, assuming tool calling supported")
        return True
```

### 6. Tool Calling Loop

**File**: `src/madison/api/client.py:OpenRouterClient.call_with_tool_loop()`

```python
async def call_with_tool_loop(
    self,
    initial_message: str,
    model: str,
    tools: List[Dict[str, Any]],
    tool_executor: Callable[[str, Dict[str, Any]], Any],
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    max_iterations: int = 10,
) -> str:
    """Execute multi-turn tool calling conversation."""
    
    logger.info(f"Starting tool calling loop for model: {model}")
    
    messages: List[Message] = [
        Message(role="user", content=initial_message)
    ]
    
    for iteration in range(max_iterations):
        logger.debug(f"Tool calling iteration {iteration + 1}/{max_iterations}")
        
        # Get response with potential tool calls
        response_text, tool_calls = await self.call_with_tools(
            messages=messages,
            model=model,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        # Add assistant's response
        assistant_message = Message(
            role="assistant",
            content=response_text if response_text else None,
            tool_calls=[tc.model_dump() for tc in tool_calls] if tool_calls else None,
        )
        messages.append(assistant_message)
        
        # If no tool calls, we're done
        if not tool_calls:
            return response_text
        
        # Execute tool calls
        tool_results = []
        for tool_call in tool_calls:
            try:
                logger.info(f"Executing tool: {tool_call.name}")
                result = tool_executor(tool_call.name, tool_call.arguments)
                
                # Handle async results
                if asyncio.iscoroutine(result):
                    result = await result
                
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_call.id,
                    "content": str(result),
                })
            except Exception as e:
                logger.error(f"Tool execution failed: {e}")
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_call.id,
                    "content": f"Error: {str(e)}",
                })
        
        # Add tool results as tool messages (OpenAI format)
        for result in tool_results:
            messages.append(Message(
                role="tool",
                tool_call_id=result["tool_use_id"],
                content=result["content"],
            ))
    
    # Max iterations reached
    return response_text or "Tool calling max iterations reached"
```

---

## AGENT LOADING AND ACTIVATION

### Loading an Agent

**File**: `src/madison/core/agent_commands.py:handle_agent_command()`

```python
async def handle_agent_command(args: str, agent_manager: AgentManager, 
                               prompt: MadisonPrompt) -> Optional[AgentDefinition]:
    """Handle /agent commands and return selected agent."""
    
    parts = args.split(maxsplit=1) if args else []
    subcommand = parts[0].lower() if parts else ""
    rest_args = parts[1] if len(parts) > 1 else ""
    
    if subcommand == "use":
        # /agent use <category> <name>
        parts = rest_args.split(maxsplit=1)
        if len(parts) < 2:
            console.print("[red]Usage: /agent use <category> <name>[/red]")
            return None
        
        category, name = parts
        agent = agent_manager.get_agent(category, name)
        if agent:
            console.print(f"[green]✓ Switched to agent:[/green] {agent.name}")
            return agent  # <- Return agent definition
        else:
            console.print(f"[red]Agent not found:[/red] {category}/{name}")
            return None
```

### Agent Activation in REPL

**File**: `src/madison/cli.py:_repl_loop()`

```python
async def _repl_loop(...):
    # ... initialization ...
    agent = Agent(config, client)  # Create agent instance
    
    while True:
        try:
            user_input = await prompt.prompt_async()
            
            # Handle commands (including /agent use)
            if await _handle_commands(...):
                # If command returns an AgentDefinition, load it
                if isinstance(user_input, AgentDefinition):
                    agent.load_agent(user_input)
                continue
            
            # Regular chat (uses active agent if loaded)
            await _handle_chat(..., agent)
            
        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted. Type '/quit' to exit.[/yellow]")
```

### Agent Loading in Agent Class

**File**: `src/madison/core/agent.py`

```python
class Agent:
    def __init__(self, config: Config, client: OpenRouterClient):
        self.config = config
        self.client = client
        self.permission_manager = PermissionManager()
        self.tool_executor = ToolExecutor()
        self.active_agent: Optional[AgentDefinition] = None
    
    def load_agent(self, agent_definition: AgentDefinition) -> None:
        """Load a saved agent definition."""
        self.active_agent = agent_definition
        logger.info(f"Loaded agent: {agent_definition.name}")
    
    def clear_agent(self) -> None:
        """Clear the active agent."""
        if self.active_agent:
            logger.info(f"Cleared agent: {self.active_agent.name}")
            self.active_agent = None
```

---

## AGENT FILE FORMAT AND PARSING

### Agent File Storage

**Location**: 
- User: `~/.config/madison/agents/<category>/<name-lowercase>.md`
- Project: `./.madison/agents/<category>/<name-lowercase>.md`

**Example File**: `~/.config/madison/agents/analysis/code-reviewer.md`

```yaml
---
name: Code Reviewer
category: analysis
description: Analyzes code for quality, security, and best practices
version: 1.0
scope: user
model: claude-opus
temperature: 0.7
max_tokens: 4000
tools:
  - read_file
  - execute_command
  - search_web
---

You are an expert code reviewer with deep knowledge of software engineering best practices.

## Your Role
- Review code for quality and correctness
- Identify security vulnerabilities
- Suggest performance improvements
- Ensure adherence to coding standards
- Provide constructive feedback

[... rest of prompt ...]
```

### Parsing Agent File

**File**: `src/madison/core/agent_registry.py`

```python
@classmethod
def from_file(cls, file_path: Path) -> "AgentDefinition":
    """Load agent from markdown file with YAML frontmatter."""
    
    content = file_path.read_text()
    
    # Must start with ---
    if not content.startswith("---"):
        raise ValueError(f"Invalid agent file format: {file_path}")
    
    # Split on second ---
    parts = content.split("---", 2)
    if len(parts) < 3:
        raise ValueError(f"Invalid agent file format: {file_path}")
    
    # Parse frontmatter
    frontmatter = yaml.safe_load(parts[1])
    prompt = parts[2].strip()
    
    # Create agent definition
    return cls(
        name=frontmatter.get("name"),
        category=frontmatter.get("category"),
        description=frontmatter.get("description"),
        prompt=prompt,
        version=frontmatter.get("version", "1.0"),
        model=frontmatter.get("model"),
        temperature=frontmatter.get("temperature"),
        max_tokens=frontmatter.get("max_tokens"),
        tools=frontmatter.get("tools"),
        scope=frontmatter.get("scope", "user"),
    )
```

### Creating Agent from Template

**File**: `src/madison/core/agent_commands.py`

```python
async def create_agent_wizard(agent_manager: AgentManager, 
                              prompt: MadisonPrompt) -> Optional[AgentDefinition]:
    """Interactive wizard to create a custom agent."""
    
    # 1. Choose starting point
    console.print("\n[bold]Create New Agent[/bold]")
    console.print("1. Blank agent")
    console.print("2. From template")
    choice = prompt.input("Select (1-2): ")
    
    if choice == "2":
        # Show templates
        templates = list(AGENT_TEMPLATES.values())
        # User selects template...
        agent = selected_template  # Start from template
    else:
        agent = AgentDefinition(
            name="",
            category="",
            description="",
            prompt="",
        )
    
    # 2. Get user input (name, category, description, etc.)
    agent.name = prompt.input("Agent name: ")
    agent.category = prompt.input("Category: ")
    agent.description = prompt.input("Description: ")
    agent.model = prompt.input("Model (optional, press Enter to skip): ") or None
    agent.temperature = float(prompt.input("Temperature (0-2, press Enter for 0.7): ") or 0.7)
    agent.max_tokens = int(prompt.input("Max tokens (press Enter for 2000): ") or 2000)
    
    # 3. Ask about tool restrictions
    tools_input = prompt.input("Tools (comma-separated or Enter for all): ")
    agent.tools = [t.strip() for t in tools_input.split(",")] if tools_input else None
    
    # 4. Choose scope
    scope_choice = prompt.input("Scope (u=user, p=project): ").lower()
    agent.scope = "project" if scope_choice == "p" else "user"
    
    # 5. Edit prompt
    console.print("\n[bold]Edit Agent Prompt[/bold]")
    # Multi-line input...
    agent.prompt = edited_prompt
    
    # 6. Save agent
    agent_manager.create_agent(agent)
    console.print(f"[green]✓ Agent created: {agent.id}[/green]")
    
    return agent
```

---

## KEY CONFIGURATION EXAMPLES

### Example 1: Configure Multiple Strategy Models

**File**: `~/.config/madison/config.yaml`

```yaml
api_key: "sk-or-v1-xxx"
default_model: "openrouter/auto"
models:
  default: "openrouter/auto"           # Chat mode
  thinking: "anthropic/claude-3-opus"  # Deep analysis (most expensive)
  planning: "openai/gpt-4-turbo"       # Strategic planning
  summarization: "openai/gpt-3.5-turbo" # Quick summaries (cheapest)
  tools: "anthropic/claude-sonnet-4"   # Tool execution fallback
system_prompt: "You are a helpful AI assistant."
temperature: 0.7
max_tokens: 2000
timeout: 30
history_size: 50
```

**Usage**:
```bash
# Regular chat - uses "openrouter/auto"
madison
> What is the capital of France?

# Deep thinking - uses claude-opus
/ask thinking "What are the implications of quantum computing?"

# Strategic planning - uses gpt-4-turbo
/ask planning "Create a 5-year roadmap"

# Quick summary - uses gpt-3.5-turbo
/ask summarization "Summarize this document"

# Direct model - bypasses strategy
/ask model=gpt-4 "Quick question"
```

### Example 2: Agent with Model Override

**File**: `./.madison/agents/analysis/security-reviewer.md`

```yaml
---
name: Security Reviewer
category: analysis
description: Security-focused code auditor
version: 1.0
model: anthropic/claude-3-opus  # <- OVERRIDES DEFAULT
temperature: 0.3                 # <- LOW for consistent security analysis
max_tokens: 3000
tools:
  - read_file
  - execute_command
  - search_web
---

You are a security expert focused on identifying vulnerabilities...
```

**Result**: When agent is active, tool calling uses claude-opus instead of default model.

---

## PERFORMANCE CONSIDERATIONS

### Retry Logic

**File**: `src/madison/api/client.py`

```python
OpenRouterClient(
    api_key="...",
    timeout=30,           # Request timeout
    max_retries=3,        # Retry on 429, 503, 504
    retry_initial_delay=1.0,      # Start with 1 second
    retry_backoff_factor=2.0,     # Exponential: 1s, 2s, 4s
)
```

Retryable status codes: 429 (rate limit), 503 (service unavailable), 504 (gateway timeout)

### Tool Calling Iterations

**Max iterations**: 10 (safety limit to prevent infinite loops)

Typical flow:
- Iteration 1: Model receives tools, returns initial tool calls
- Iterations 2-N: Model gets tool results, refines plan
- Iteration N+1: Model returns final response (no tool calls)

---

## DEBUGGING AND LOGGING

### Enable Debug Logging

```bash
madison --verbose
```

Sets logging level to DEBUG for madison namespace:
```python
if verbose:
    logging.getLogger("madison").setLevel(logging.DEBUG)
else:
    logging.getLogger("madison").setLevel(logging.WARNING)
```

### Key Log Points

- Agent loading: `logger.info(f"Loaded agent: {agent_definition.name}")`
- Model selection: `logger.debug(f"Using agent-specific model: {model}")`
- Tool execution: `logger.info(f"Executing tool: {tool_call.name}")`
- API errors: `logger.error(error_msg)`
- Retry attempts: `logger.warning(f"Retrying... (attempt {attempt+1}/{max_retries})")`

---

