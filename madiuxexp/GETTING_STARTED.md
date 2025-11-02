# Getting Started with Madison UX Experiment

## What is This?

`madiuxexp` is a **separate, isolated package** alongside madison where you can freely experiment with new UI/UX ideas without affecting the main application.

## Quick Setup

Already installed? Just run:

```bash
madiuxexp
```

## Current Feature: Split-Screen Interface

When you run `madiuxexp`, you'll see a two-pane layout:

```
Left Pane                    | Right Pane
─────────────────────────────────────────
Control & Operations log     | Generated Content
(what's happening)           | (model responses, etc)
```

### Try These Commands

1. **See a demo**:
   ```
   > /demo
   ```

2. **Type anything else** to echo in the UI (placeholder for real model responses):
   ```
   > What is quantum computing?
   ```

3. **Clear the screen**:
   ```
   > /clear
   ```

4. **Exit**:
   ```
   > /quit
   ```

## Project Layout

```
madison/                          # Main project
├── madison/                       # Existing Madison package
│   └── src/madison/               # Madison source code
│
└── madiuxexp/                    # ← YOU ARE HERE
    ├── README.md                 # Main documentation
    ├── DESIGN.md                 # Detailed design doc
    ├── GETTING_STARTED.md        # This file
    ├── pyproject.toml
    └── src/madiuxexp/
        ├── cli.py                # Entry point
        └── ui/
            └── splitscreen.py     # Split-screen implementation
```

## How to Experiment

### Option 1: Modify the Demo

Edit `src/madiuxexp/cli.py`, specifically the `_demo_interaction()` function:

```python
async def _demo_interaction(ui: SplitScreenUI) -> None:
    """Demo the split-screen UI with a simulated interaction."""
    ui.clear()

    # Add your own messages here!
    ui.add_left_message("Your message", "control")
    ui.add_right_content(Panel("Your content"))
    ui.refresh()
```

### Option 2: Try a New Layout

Create a new file in `src/madiuxexp/ui/`:

```python
# src/madiuxexp/ui/alt_layout.py
from rich.console import Console
from rich.layout import Layout

class AlternativeLayout:
    def __init__(self):
        self.layout = Layout()
        # Design your layout here
```

### Option 3: Integrate with Real Madison

In `cli.py`, you could import madison components:

```python
from madison.api.client import OpenRouterClient
from madison.core.config import Config
from madiuxexp.ui.splitscreen import SplitScreenUI

# Use SplitScreenUI to display real madison interactions!
```

## Key Files to Know

| File | Purpose |
|------|---------|
| `cli.py` | Main entry point - where the REPL loop runs |
| `ui/splitscreen.py` | The UI layout implementation |
| `DESIGN.md` | Detailed rationale for the split-screen design |

## Making Changes

All the code is fresh and yours to modify:

```bash
# Edit the files
nano src/madiuxexp/cli.py
nano src/madiuxexp/ui/splitscreen.py

# Reinstall to test changes
uv pip install -e .

# Run the updated version
madiuxexp
```

## Ideas for Exploration

- [ ] **Modal inputs**: Pop-up dialogs for special input modes
- [ ] **Tabbed interface**: Switch between different view modes
- [ ] **Progress bars**: Visual feedback for long operations
- [ ] **Syntax highlighting**: Better code display on right pane
- [ ] **Keyboard navigation**: Arrow keys to scroll and navigate
- [ ] **Collapsible sections**: Hide/show operation details
- [ ] **Live metrics**: Show tokens, time, cost in real-time
- [ ] **Custom themes**: Dark mode, light mode, etc.
- [ ] **Search/filter**: Find operations in the log
- [ ] **Export**: Save interactions to file

## Integration Checklist

When you find something that works well and want to move it to Madison:

- [ ] Code is tested and working
- [ ] Documentation is clear
- [ ] Follows Madison's code style
- [ ] Compatible with existing Madison CLI
- [ ] No breaking changes to core functionality

## Troubleshooting

**Package not found?**
```bash
uv pip install -e .
```

**Import errors?**
```bash
# Reinstall and rebuild
uv pip install -e . --force-reinstall
```

**Want to see the raw layout structure?**
```python
# In cli.py, just after creating the SplitScreenUI:
print(ui.layout)
```

## Questions?

- Check `DESIGN.md` for the philosophy behind split-screen
- Review `src/madiuxexp/ui/splitscreen.py` for API details
- Look at how madison's `cli.py` structures messages

## Next Steps

1. Run `madiuxexp` and try `/demo`
2. Read `DESIGN.md` to understand the split-screen rationale
3. Modify `_demo_interaction()` to test your own messages
4. Explore creating alternative layouts
5. Consider integrating real Madison functionality

Have fun experimenting! 🚀
