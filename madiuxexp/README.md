# Madison UX Experiment (madiuxexp)

Experimental package for exploring alternative UI/UX designs for the Madison AI interaction framework.

## Overview

This is an **isolated playground** for prototyping and testing new UI/UX approaches without affecting the main Madison implementation. You have complete freedom to iterate on interface designs, interaction patterns, and user experiences.

## Current Experiments

### 1. **Split-Screen Interface** (Active)

A dual-pane layout separating control flow from generated content:

- **Left pane**: User input + operation log (what's happening)
- **Right pane**: Generated content (model responses, file contents, etc.)

This design improves:
- Visibility into multi-step operations
- Content readability (no interruptions from status messages)
- Debugging and flow understanding
- Parallel work (reading output while tracking progress)

**Try it out**: `madiuxexp` (runs a demo with `/demo` command)

See [DESIGN.md](./DESIGN.md) for detailed design documentation.

## Installation

Install in development mode:

```bash
cd madiuxexp
uv pip install -e .
```

Or use the provided test setup:

```bash
uv pip install -e ".[dev]"
```

## Quick Start

```bash
# Run the split-screen demo
madiuxexp

# In the interactive prompt:
# /demo     - Show a simulated interaction
# /clear    - Clear the screen
# /quit     - Exit
```

## Project Structure

```
madiuxexp/
├── pyproject.toml          # Package configuration
├── README.md               # This file
├── DESIGN.md              # Split-screen design details
└── src/madiuxexp/
    ├── __init__.py
    ├── cli.py              # Main CLI entry point
    └── ui/
        ├── __init__.py
        └── splitscreen.py   # Split-screen UI implementation
```

## Philosophy

- **Isolation**: Changes here don't affect the main Madison package
- **Experimentation**: Freedom to try radical UI/UX changes without constraints
- **Rapid Iteration**: Easy to modify, test, and validate
- **Integration Path**: Successful patterns can be migrated to Madison when proven

## Next Steps

You can extend this in several directions:

1. **Enhance the split-screen**: Add real Madison backend integration
2. **Try alternative layouts**: Modal dialogs, tabbed interfaces, etc.
3. **Improve interactions**: Better input handling, keyboard navigation
4. **Add theming**: Custom color schemes and styling
5. **Performance metrics**: Token counts, execution time, costs

## Development Notes

- Uses **Rich** for terminal UI rendering
- **Typer** for CLI structure
- **Async/await** for handling long-running operations
- Same dependencies as Madison (easy to share code)

Start modifying `src/madiuxexp/` to explore your ideas!
