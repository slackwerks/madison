# Phase 4 Enhancement Plan - Enhanced Panes

## Overview
Phase 4 focuses on enhancing the TUI panes with better content display and real-time feedback. Each enhancement will be implemented and human-tested independently before moving to the next.

---

## Enhancement 1: Real-time Operation Logging in Left Pane

**Goal:** Track all operations with hierarchical details in the left pane using Claude Code style formatting

**Implementation:**
- Create `OperationContext` class to track operations and their details
- Add `start_operation()` and `complete_operation()` methods to UIHandler
- Display operations in Claude Code style with `↳` arrow for details:
  ```
  Operation(description)
    ↳ Detail line 1
    ↳ Detail line 2
  ```
- Integrate operation logging into `/read`, `/exec`, `/search` commands
- Example output:
  ```
  Read(story.txt)
    ↳ Read 147 lines (4,234 bytes)

  Exec(ls -la)
    ↳ Exit code: 0
    ↳ Output: 1,234 bytes

  Search(python async)
    ↳ Found 2,456 characters
  ```

**Implementation Details:**
- `OperationContext` tracks operation type, description, and details
- Details can be marked as success (green) or failure (red)
- Operations display once at completion with all accumulated details
- File operations show line counts and byte counts
- Command execution shows exit codes and output/error sizes
- Search results show character counts

**Outstanding Items for Step 1:**
- Plan execution operations not yet tracked (orchestration visibility gap)
  - Need to show when each plan task starts/completes
  - Need to show overall plan completion status
  - Currently plan execution is silent until results appear

**Testing Checklist:**
- [ ] Run madison TUI mode
- [ ] Execute `/read <filepath>` and verify operation format with lines and bytes
- [ ] Execute `/exec <command>` and verify operation shows exit code and output size
- [ ] Execute `/search <query>` and verify operation shows result size
- [ ] Verify operations appear only once with all details
- [ ] Verify success/failure details show correct colors (green/red)

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

## Enhancement 4: Scrollbuffers and Pane Focus Management

**Goal:** Add scrollable content buffers to both panes with proper focus management

**Implementation:**

### Part 4a: Scrollbuffers
- **Left pane:** Add scrollable container for message log
  - Auto-scrolls to bottom when new messages/operations are added
  - User can manually scroll up to view history
  - Session-based (no limit - keeps all messages for current session)
  - New content triggers auto-scroll to latest

- **Right pane:** Add scrollable container for content display
  - Content renders with beginning pinned to top of pane
  - Scrolling enabled only if content exceeds pane height
  - Always scrolls to beginning (top) when new content is displayed

### Part 4b: Pane Focus Management
- **Ctrl-Tab:** Toggle scroll focus between left and right panes
- Input field in left pane has separate focus from scroll focus
- Visual indicator of which pane has scroll focus (e.g., border styling)
- Left pane scrolling: operates on message/operation history
- Right pane scrolling: operates on displayed content (file contents, responses, etc.)

**Testing Checklist:**
- [ ] Launch madison and verify both panes are scrollable
- [ ] Add messages to left pane and verify auto-scroll to bottom
- [ ] Manually scroll up in left pane to view history, verify new messages don't force scroll
- [ ] Display large content in right pane and verify scrolling enabled
- [ ] Display small content in right pane and verify no scrollbar
- [ ] Test Ctrl-Tab to switch pane focus (visual indication changes)
- [ ] Verify scrolling works in focused pane, not the unfocused pane
- [ ] Verify input field in left pane works independently of scroll focus

---

## Implementation Order

1. **Enhancement 1: Operation Logging** ✓
   - Foundation for visibility into what madison is doing
   - Makes debugging easier

2. **Enhancement 2: Streaming Response** ✓
   - Core UX improvement for the most frequent user interaction
   - Better perceived performance

3. **Enhancement 3: File Formatting** ✓
   - Quality of life improvement for developers using `/read`
   - Makes code easier to parse visually

4. **Enhancement 4: Scrollbuffers and Pane Focus Management**
   - Improved content navigation for both panes
   - Better UX for viewing large outputs and conversation history

---

## Notes

- Each enhancement is independent and can be tested in isolation
- Human testing happens after each enhancement is complete
- No dependencies between enhancements (can potentially be reordered if needed)
- All enhancements improve the user experience without breaking existing functionality
- Changes are localized to UI handlers and display logic, not core application logic
