# Phase 4 Enhancement Plan - Enhanced Panes

## Overview
Phase 4 focuses on enhancing the TUI panes with better content display and real-time feedback. Each enhancement will be implemented and human-tested independently before moving to the next.

---

## Enhancement 1: Real-time Operation Logging in Left Pane

**Goal:** Track all operations with timestamps and status in the left pane

**Implementation:**
- Update `display_operation()` in TextualUIHandler to format operations consistently
- Add operation start/end tracking (e.g., "READ started" → "READ completed" or "READ failed")
- Show operation details inline (file path for reads, command for execs, query for searches)
- Format: `[HH:MM:SS] [OP_TYPE] status: details`
- Example output:
  ```
  [14:23:45] READ: Reading /path/to/file.py
  [14:23:46] READ: Complete (2,340 bytes)
  [14:23:47] EXEC: Running: ls -la
  [14:23:48] EXEC: Complete (exit code: 0)
  ```

**Testing Checklist:**
- [ ] Run madison TUI mode
- [ ] Execute `/read <filepath>` and verify operation appears in left pane with timestamp
- [ ] Execute `/exec <command>` and verify operation appears with status
- [ ] Execute `/search <query>` and verify operation appears with query text
- [ ] Verify all operations show completion status or error status

---

## Enhancement 2: Streaming Response in Right Pane

**Goal:** Display model responses token-by-token as they arrive in real-time

**Implementation:**
- Improve `start_streaming()`, `stream_token()`, `end_streaming()` in TextualUIHandler
- Display response in right pane incrementally (no buffering until complete)
- Show response as it's generated, not all at once at the end
- Add visual indicator (maybe "⏳ Generating..." header)
- When complete, clean up the header or show completion status

**Testing Checklist:**
- [ ] Start conversation with model
- [ ] Send a prompt that generates a longer response
- [ ] Verify response appears character-by-character in right pane (not all at once)
- [ ] Verify left pane shows "RESPONSE" operation while generating
- [ ] Verify response completes and is fully readable in right pane

---

## Enhancement 3: File Content Formatting

**Goal:** Pretty-print file contents when displayed via `/read` command

**Implementation:**
- When `/read` displays a file, detect file type from extension
- Use Rich's `Syntax` class for code files (.py, .js, .ts, .json, .yaml, etc.)
- Use `Markdown` for .md files
- Plain text for others
- Display formatted content in right pane via `display_panel()`
- Left pane just shows operation log: "READ: /path/to/file.py (1,234 bytes)"

**Testing Checklist:**
- [ ] `/read` a Python file and verify syntax highlighting appears
- [ ] `/read` a Markdown file and verify formatting (bold, lists, etc.)
- [ ] `/read` a JSON file and verify indentation/formatting
- [ ] `/read` a plain text file and verify displays as plain text
- [ ] Verify file contents display in right pane, not left pane

---

## Enhancement 4: Status Bar / Status Information Display

**Goal:** Show current context (model, agent, operation count, etc.)

**Implementation:**
- Add a status line at the bottom of the TUI (or top, or integrated into UI)
- Display: `Model: <name> | Agent: <name> | Operations: <count> | Status: <state>`
- Update dynamically as state changes
- Example: `Model: claude-opus | Agent: default | Operations: 3 | Ready`
- Should be always visible and lightweight
- Update when:
  - Model is changed with `/model`
  - Agent is selected with `/agent`
  - Operations are executed
  - Connection status changes

**Testing Checklist:**
- [ ] Launch madison and verify status bar is visible at bottom (or designated location)
- [ ] Verify it shows current model name
- [ ] Execute `/model <new-model>` and verify status bar updates
- [ ] Execute operations and verify operation counter increments
- [ ] Select agent with `/agent` and verify status bar updates

---

## Implementation Order

1. **Enhancement 1: Operation Logging**
   - Foundation for visibility into what madison is doing
   - Makes debugging easier

2. **Enhancement 2: Streaming Response**
   - Core UX improvement for the most frequent user interaction
   - Better perceived performance

3. **Enhancement 3: File Formatting**
   - Quality of life improvement for developers using `/read`
   - Makes code easier to parse visually

4. **Enhancement 4: Status Bar**
   - Context awareness across the application
   - Keeps user informed of current state

---

## Notes

- Each enhancement is independent and can be tested in isolation
- Human testing happens after each enhancement is complete
- No dependencies between enhancements (can potentially be reordered if needed)
- All enhancements improve the user experience without breaking existing functionality
- Changes are localized to UI handlers and display logic, not core application logic
