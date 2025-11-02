# Split-Screen UI Design

## Overview

The `madiuxexp` split-screen interface provides an alternative UX for Madison that separates **control flow** from **generated content** into distinct visual spaces.

## Layout

```
┌─────────────────────────────────────────────────────┐
│              Madison UX Experiment                   │
└─────────────────────────────────────────────────────┘
┌──────────────────────┬──────────────────────────────┐
│   LEFT PANE          │    RIGHT PANE                │
│ (Control & Ops)      │  (Generated Content)         │
├──────────────────────┼──────────────────────────────┤
│                      │                              │
│ Time | Type | Msg    │  ┌─────────────────────────┐ │
│ ──────────────────── │  │ Response 1               │ │
│ 11:12 INPUT   User   │  │ ...                      │ │
│       asked: ...     │  └─────────────────────────┘ │
│                      │                              │
│ 11:12 CONTROL:plan   │  ┌─────────────────────────┐ │
│       Creating exec  │  │ Response 2               │ │
│       plan...        │  │ ...                      │ │
│                      │  └─────────────────────────┘ │
│ 11:12 OPERATION:exec │                              │
│       Calling model: │                              │
│       claude-sonnet  │                              │
│                      │                              │
└──────────────────────┴──────────────────────────────┘
```

## Left Pane: Control & Operations

This pane shows the **flow of operations** and **user intent**:

### Message Types

- **INPUT**: User prompts and queries
- **CONTROL**: System status, execution plans, confirmations
  - Categories: `plan`, `complete`, `status`
- **OPERATION**: Actions being executed
  - Categories: `exec`, `search`, `read`, `write`

### Purpose

- Show **what's happening** at a glance
- Provide **visibility** into multi-step processes
- Keep a **log** of all operations
- Allow users to **understand the flow** even as they read the right pane

## Right Pane: Generated Content

This pane displays the **results**:

- **Model responses** (streamed)
- **File contents** (from /read commands)
- **Search results**
- **Command output**
- **Formatted data** and analysis

### Purpose

- Focus on **content consumption**
- Minimize **distraction** during reading
- Keep **generated outputs clean** and uncluttered
- Show **multiple results** stacked vertically

## Interaction Patterns

### Simple Query

```
Left:  [INPUT] User asks a question
       [OPERATION] Calling model...
       [CONTROL] Response received

Right: [Model's response]
```

### Multi-step Operation

```
Left:  [INPUT] User asks for complex task
       [CONTROL] Creating execution plan
       [CONTROL] Step 1: Research...
       [CONTROL] Step 2: Compile...
       [OPERATION] Executing step 1...
       [OPERATION] Executing step 2...
       [CONTROL] All steps complete

Right: [Step 1 result]
       [Step 2 result]
       [Final synthesis]
```

### Tool Usage (exec, search, etc)

```
Left:  [INPUT] User asks to search something
       [OPERATION] Executing: /search ...
       [CONTROL] Found N results

Right: [Search result 1]
       [Search result 2]
       [etc]
```

## Advantages Over Linear Flow

| Aspect | Current Madison | Split-Screen |
|--------|---|---|
| **Discoverability** | Output and control mixed | Clear separation |
| **Context Window** | Need to scroll past operations | Operations always visible |
| **Reading UX** | Interrupted by status messages | Uninterrupted content view |
| **Debugging** | Hard to trace flow | Left pane shows exact flow |
| **Multi-tasking** | Difficult to track progress | Can skim left pane for status |

## Implementation Details

### Core Components

- **`SplitScreenUI`** (`splitscreen.py`): Layout manager using Rich's `Layout`
- **`Message`** dataclass: Standardized message format with timestamp, type, category
- **CLI** (`cli.py`): Integration with typer and async event loop

### Key Methods

- `add_left_message()`: Log control/operation messages
- `add_right_content()`: Display generated content (Rich renderables)
- `refresh()`: Render full UI
- `clear()`: Clear all content

## Usage Example

```python
from madiuxexp.ui.splitscreen import SplitScreenUI

ui = SplitScreenUI()

# Log a user input
ui.add_left_message("What is quantum computing?", "input")

# Log an operation
ui.add_left_message("Searching for information...", "operation", "search")

# Add content to right pane
ui.add_right_content(Panel("Quantum computing is..."))

# Refresh display
ui.refresh()
```

## Future Enhancements

- [ ] Live streaming to right pane while left pane updates
- [ ] Collapsible operation history
- [ ] Color-coded message types
- [ ] Keyboard navigation between panes
- [ ] Search/filter operations
- [ ] Metrics display (tokens, time, cost)
- [ ] Theme customization
- [ ] Mobile-friendly alternative layout
