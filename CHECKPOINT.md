# Madison Development Checkpoint

**Session Date:** October 26, 2025
**Current Status:** Tool Calling Foundation Complete - Ready for Agent Refactor

## Overview

Madison is an OpenRouter CLI application with agent-based intent processing. We've completed the foundation for **proper tool calling** (instead of regex parsing) and are ready to refactor the Agent to use it.

## ✅ Completed Phases

### Phase 1: Project Scope & Permissions ✅
- Created `src/madison/core/permissions.py` with PermissionManager
- Extended `src/madison/core/config.py` with ProjectConfig and ProjectPermissions
- Whitelist-based permission system (default deny)
- Permission prompting UX: Yes once / Yes always / No options
- Updated `src/madison/tools/file_ops.py` and `src/madison/tools/command_exec.py` to enforce permissions
- Setup wizard (Step 8) for project-level configuration
- Updated README with project scope documentation

**Key Files:**
- `src/madison/core/permissions.py` - Permission checking and prompting
- `src/madison/core/config.py` - ProjectConfig and ProjectPermissions
- `src/madison/tools/file_ops.py` - Permission checks in file operations
- `src/madison/tools/command_exec.py` - Permission checks in command execution

**Commits:**
- `b057054` - Implement project scope and permission system
- `b70abcb` - Fix NoneType error when resuming from Ctrl+Z

### Phase 2A: Agent System Foundation (Partial - Deprecated)
- Created `src/madison/core/plan.py` - Plan/PlanAction models
- Created `src/madison/core/plan_parser.py` - Regex-based action extraction
- Created `src/madison/core/agent.py` - Agent orchestrator
- Integrated agent into CLI (`src/madison/cli.py`)
- Fixed agent API call bugs and improved parsing

**Status:** ⚠️ These will be replaced by tool calling in next phase

**Commits:**
- `92d7ee8` - Implement agent system for natural language intent processing
- `63963f2` - Fix agent chat_stream API call and message format
- `07d0dee` - Fix plan parser to avoid spurious action extraction
- `1c9b1f2` - Further improve plan parser pattern matching

### Phase 2B: Tool Calling Foundation ✅ (NEW)
- Created `src/madison/core/tools.py` - Tool definitions and schemas
- Created `src/madison/core/model_registry.py` - Model capability tracking
- Updated `src/madison/api/models.py` - Added ToolCall and tools support
- Enhanced `src/madison/api/client.py` - Three new tool calling methods

**Key Files:**
- `src/madison/core/tools.py` - Define execute_command, read_file, write_file, search_web
- `src/madison/core/model_registry.py` - Track 23+ tool-capable models
- `src/madison/api/client.py` - call_with_tools(), _parse_tool_calls(), call_with_tool_loop()

**New Methods in OpenRouterClient:**
1. `call_with_tools()` - Single-turn tool calling with structured responses
2. `_parse_tool_calls()` - Parse tool call data from API responses
3. `call_with_tool_loop()` - Multi-turn conversation with automatic tool execution

**Commits:**
- `3056caa` - Add tool calling foundation: schemas, registry, and API models
- `8e5bc10` - Add comprehensive tool calling support to OpenRouterClient

## 📋 Pending Work

### Phase 3: Agent Refactor (NEXT)
**Tasks:**
1. Create `src/madison/core/tool_executor.py`
   - Maps tool calls to actual operations
   - Handles: execute_command, read_file, write_file, search_web
   - Error handling and result formatting

2. Refactor `src/madison/core/agent.py`
   - Replace regex-based plan generation with tool calling
   - Use `client.call_with_tool_loop()` instead of `generate_plan()`
   - Proper permission integration with PermissionManager
   - Error handling with user prompts

3. Update `src/madison/cli.py`
   - Pass tools to agent
   - Handle tool call responses properly

4. **Delete deprecated files:**
   - `src/madison/core/plan.py` - Old Plan/PlanAction models
   - `src/madison/core/plan_parser.py` - Old regex parser

**Expected Benefits:**
- ✅ No more regex parsing fragility
- ✅ Deterministic, structured tool calls
- ✅ Multi-step workflows with tool results
- ✅ Model "understands" tool results and can refine

### Phase 4: Testing & Polish
- Test with multiple models (OpenAI, Claude, Gemini, etc.)
- Verify tool calling works correctly
- Test permission system integration
- Update documentation

## 🏗️ Architecture

### Tool Calling Flow
```
User Intent
    ↓
Agent.process_intent(user_input)
    ↓
client.call_with_tool_loop(
    initial_message=user_input,
    model=config.default_model,
    tools=ALL_TOOLS,
    tool_executor=executor.execute(tool_name, args)
)
    ↓
Loop:
  1. Send message + tools to model
  2. Get response with tool_calls
  3. Execute tools via tool_executor
  4. Send results back to model
  5. Continue until model returns final response
    ↓
Return final response to user
```

### Tool Definitions
```python
# 4 core tools (from src/madison/core/tools.py)
- execute_command(command: str)
- read_file(file_path: str)
- write_file(file_path: str, content: str)
- search_web(query: str)
```

### Permission Integration
- PermissionManager checks all operations before execution
- User prompting on permission denial
- Whitelist-based (default deny)
- Project-scoped (./.madison/config.yaml)

## 📝 Key Design Decisions

### Why Tool Calling Instead of Regex?
- **Before:** AI responds with natural language, regex extracts actions (fragile)
- **After:** AI generates structured function calls (deterministic)
- More robust for multi-step workflows
- Model "understands" tool results
- Scales better for future additions

### Permission System
- Whitelist model (secure by default)
- Project-scoped (no parent directory inheritance)
- User prompting for overrides
- Persistent save to ./.madison/config.yaml

### Model Registry
- Track which models support tool calling
- 23 known tool-capable models
- Runtime registration for new models
- Graceful fallback for non-tool models

## 🐛 Known Issues & Fixes

### Resolved
- ✅ Agent chat_stream API call (missing model parameter)
- ✅ Spurious action extraction (too-loose regex patterns)
- ✅ NoneType error on Ctrl+Z resume
- ✅ Message.content false positives in write file detection

### In Progress
- None currently

## 📚 File Structure

### Core
- `src/madison/core/config.py` - Config management
- `src/madison/core/permissions.py` - Permission system
- `src/madison/core/tools.py` - Tool definitions ⭐ NEW
- `src/madison/core/model_registry.py` - Model capabilities ⭐ NEW
- `src/madison/core/agent.py` - Agent (needs refactor)
- `src/madison/core/plan.py` - Plan models (deprecated)
- `src/madison/core/plan_parser.py` - Regex parser (deprecated)
- `src/madison/core/session.py` - Session management
- `src/madison/core/history.py` - History tracking
- `src/madison/core/session_manager.py` - Session persistence

### API
- `src/madison/api/client.py` - OpenRouter client ⭐ UPDATED
- `src/madison/api/models.py` - API models ⭐ UPDATED

### Tools
- `src/madison/tools/file_ops.py` - File operations
- `src/madison/tools/command_exec.py` - Command execution
- `src/madison/tools/web_search.py` - Web search

### CLI
- `src/madison/cli.py` - Main CLI interface

## 🚀 Next Session Checklist

### To Do in Next Session:
- [ ] Create ToolExecutor class (map tool calls to operations)
- [ ] Refactor Agent to use tool calling
- [ ] Update CLI to integrate with new Agent
- [ ] Delete deprecated plan.py and plan_parser.py
- [ ] Test with "please make the directory foo"
- [ ] Test permission prompting
- [ ] Test multi-step workflows
- [ ] Update README with tool calling info
- [ ] Final documentation

### Quick Start Commands
```bash
# Run Madison
madison

# Test tool calling (after refactor)
> please make the directory test_dir
> create a file called test.txt with content "hello"
> list files in this directory
```

## 💡 Tips for Next Session

1. **ToolExecutor Implementation**
   - Should be simple: just call file_ops, command_executor, searcher
   - Handle permissions via PermissionManager
   - Return result as string for model

2. **Agent Refactor**
   - Remove `generate_plan()` and `execute_plan()` methods
   - Implement new `process_intent()` using `client.call_with_tool_loop()`
   - Pass tool executor callback to client

3. **Testing**
   - Simple intent: "make directory foo" (should work)
   - Complex intent: "create 3 directories: a, b, c" (multi-step)
   - Error case: try to access /etc/passwd (should prompt for permission)

4. **Reference Code**
   - Look at `call_with_tool_loop()` in client.py for the pattern
   - tool_executor callback should be: `def execute(tool_name: str, args: Dict) -> str`

## 🎯 Success Criteria

Agent system is working correctly when:
- ✅ "please make directory foo" creates the directory
- ✅ No spurious files created (like "the")
- ✅ No regex parsing in execution
- ✅ Model explicitly calls tools with arguments
- ✅ Permission system still enforces restrictions
- ✅ Multi-step workflows work (create multiple items)

## 📖 Related Documentation

- README.md - User guide
- PLAN.md - Original implementation plan
- src/madison/core/tools.py - Tool definitions
- src/madison/core/model_registry.py - Supported models

---

**Last Updated:** October 26, 2025
**Next Session Focus:** Agent Refactor (Phase 3)
**Estimated Time:** 1-2 hours to complete refactor and testing
