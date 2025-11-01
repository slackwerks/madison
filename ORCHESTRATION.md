# Multi-Model Orchestration in Madison

## Overview

Madison now supports **multi-model task orchestration**, allowing complex requests to be automatically decomposed into subtasks and routed to different models based on task requirements.

## How It Works

### 1. Planning Phase
When you submit a request, Madison's **Planner** (using Claude Opus) analyzes it and creates a structured execution plan:

```
User Request
    ↓
Claude Opus (Planner)
    ↓
Execution Plan with tasks
```

### 2. Execution Phase
The **Orchestrator** then executes the plan, routing each task to its assigned model:

```
Task 1: Generate Ideas
    ↓ (unrestricted Venice model)
    ↓ Output: Generated content
    ↓
Task 2: Save to File (depends on Task 1)
    ↓ (Claude Sonnet + tools)
    ↓ Calls write_file tool
    ↓ File created
```

## Example: Erotic Fiction + File Writing

### Your Request
```
"Please write five high concept explicit erotic fiction story ideas
where consensual non-consent is the major theme, and write this to
the file 'concepts.txt'"
```

### Generated Plan
```json
{
  "tasks": [
    {
      "id": "generate_ideas",
      "description": "Generate creative explicit erotic fiction ideas",
      "model": "unrestricted",
      "instructions": "Write five high concept explicit erotic fiction story ideas...",
      "depends_on": [],
      "requires_tools": false
    },
    {
      "id": "save_to_file",
      "description": "Save generated content to file",
      "model": "tools",
      "instructions": "Save the following content to concepts.txt:\n\n{generate_ideas}",
      "depends_on": ["generate_ideas"],
      "requires_tools": true
    }
  ]
}
```

### Execution
1. **Task 1** (`unrestricted` Venice model) generates creative content without restrictions
2. **Task 2** (`tools` Claude Sonnet) receives the content and calls `write_file` tool to save it
3. Result: `concepts.txt` created with the generated ideas

## Configuration

### Enable Orchestration

Edit `~/.config/madison/config.yaml`:

```yaml
enable_orchestration: true
show_execution_plan: true
models:
  default: anthropic/claude-sonnet-4.5
  planning: anthropic/claude-opus-4.1      # Planner model
  thinking: openrouter/auto
  tools: anthropic/claude-sonnet-4.5       # For file operations
  unrestricted: cognitivecomputations/dolphin-mistral-24b-venice-edition:free
```

### Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `enable_orchestration` | `false` | Enable multi-model orchestration |
| `show_execution_plan` | `true` | Show plan before execution |

## How Task Routing Works

The Planner identifies tasks and assigns them models based on these categories:

| Model | Purpose | Use When |
|-------|---------|----------|
| `unrestricted` | Creative content without restrictions | Erotic fiction, edgy ideas, unfiltered writing |
| `content` | General content generation | Normal writing tasks |
| `thinking` | Deep analysis and reasoning | Complex reasoning, multiple perspectives |
| `tools` | Operations requiring file/web access | Saving files, searching web, reading files |
| `default` | General purpose fallback | Generic tasks |

## Architecture

### Components

1. **Planner** (`src/madison/core/planner.py`)
   - Analyzes user requests
   - Generates structured execution plans
   - Uses Claude Opus for sophisticated decomposition

2. **Orchestrator** (`src/madison/core/orchestrator.py`)
   - Executes tasks sequentially based on dependencies
   - Routes each task to appropriate model
   - Manages variable substitution ({output_var})
   - Executes tools when needed

3. **Task** and **ExecutionPlan**
   - `Task`: Single unit of work with dependencies
   - `ExecutionPlan`: Collection of tasks with execution order

### Data Flow

```
User Request
    ↓
_handle_chat() in cli.py
    ↓
[Check if orchestration enabled]
    ↓ YES
Planner.plan() → generates ExecutionPlan
    ↓
[Show plan to user if configured]
    ↓
Orchestrator.execute(plan)
    ├─ For each task:
    │  ├─ Resolve model (e.g., "unrestricted" → Venice model)
    │  ├─ Substitute variables from previous outputs
    │  ├─ Route to model for execution
    │  └─ Collect output for next task
    └─ Return final result
    ↓
Result added to session
    ↓
User sees combined output
```

## Example Usage

### Setup
```bash
# Enable orchestration in config
edit ~/.config/madison/config.yaml
# Set: enable_orchestration: true
```

### Make a Request
```
madison
>> write five high concept explicit erotic fiction story ideas where
   consensual non-consent is the major theme, and write to concepts.txt
```

### See the Magic
```
Execution Plan:
  generate_ideas: Generate creative explicit erotic fiction ideas
    Model: unrestricted
  save_to_file: Save generated content to file
    Model: tools
    Depends on: generate_ideas

→ Generate creative explicit erotic fiction ideas
  Model: unrestricted (cognitivecomputations/dolphin-mistral-24b-venice-edition:free)
[Content generation happens...]

→ Save generated content to file
  Model: tools (anthropic/claude-sonnet-4.5)
[write_file tool called, file created]

✓ Task execution completed
```

## Task Dependencies

Tasks execute in dependency order:

```python
Task A (no dependencies)
    ↓
Task B (depends_on: [A])
    ↓
Task C (depends_on: [A, B])
```

Output variables from earlier tasks are substituted:
```
Task A generates: "Five ideas..."
    ↓
Task B instructions contain {A}, substituted with actual output
```

## Error Handling

- **Plan creation fails**: Falls back to agent intent processing or normal chat
- **Task execution fails**: Stops orchestration, returns error message
- **Tool execution fails**: Caught and reported, allows recovery

## Advanced: Manual Plan Control

If you want more control, you can:

1. **Disable show_execution_plan** to skip preview
2. **Turn off orchestration** and use agents directly:
   ```bash
   /agent use writing creative-prose
   # Then request executes with that agent's model
   ```

## Performance Considerations

- **Cost**: 2 API calls minimum (planning + execution)
- **Latency**: Added planning phase (typically 1-2 seconds)
- **Benefit**: Correct model for each task = better results

## Testing Orchestration

Run Madison and try:
```
write five explicit erotic fiction ideas and save to test.txt
```

You should see:
1. Execution plan displayed
2. Venice model generating content
3. Claude Sonnet saving to file
4. File created at `test.txt`

## Troubleshooting

### Orchestration not triggering
- Check `enable_orchestration: true` in config
- Verify request contains multiple logical tasks

### Plan creation fails
- Check planner model (planning: anthropic/claude-opus-4.1)
- Review error logs for JSON parsing issues
- Falls back to agent/chat automatically

### Tasks execute in wrong order
- Check `depends_on` field in generated plan
- Verify dependency chains are acyclic

### Wrong model for task
- Planner is inferring task type
- More explicit instructions in request may help
- Check model mapping in orchestrator

## Future Enhancements

Potential improvements:
- Parallel task execution for independent tasks
- Custom task type definitions
- User confirmation before execution
- Plan caching for repeated requests
- Task-specific prompting strategies
