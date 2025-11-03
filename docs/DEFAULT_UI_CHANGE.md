# Default UI Mode Change: TUI is Now Default

## Summary

Changed Madison's default UI mode from CLI to Textual TUI. This provides a better out-of-the-box experience with the modern split-screen interface.

## Changes Made

### 1. Madison CLI (`src/madison/cli.py`)
- Changed `--ui` parameter default from `"cli"` to `"tui"`
- Updated help text to reflect TUI as default

**Before:**
```python
ui: str = typer.Option(
    "cli",
    "--ui",
    help="UI mode: 'cli' for command-line interface, 'tui' for Textual TUI",
)
```

**After:**
```python
ui: str = typer.Option(
    "tui",
    "--ui",
    help="UI mode: 'tui' for Textual TUI (default), 'cli' for command-line interface",
)
```

### 2. README.md
- Reordered UI Modes section
- Textual TUI now listed first and marked as "Default"
- CLI section moved to second position and marked as "Opt-In"
- Updated all usage examples to reflect new default

### 3. Documentation Files
- **INTEGRATION_PROGRESS.md** - Updated Usage section
- **PHASE_1_2_3_SUMMARY.md** - Updated Usage Examples section

## Usage Changes

### Old Behavior (CLI Default)
```bash
madison          # Launches CLI
madison --ui=tui # Opt in to TUI
```

### New Behavior (TUI Default)
```bash
madison          # Launches Textual TUI (NEW!)
madison --ui=cli # Opt in to CLI
```

## Backward Compatibility

✅ **Fully backward compatible**
- Users can still use `madison --ui=cli` to get the old CLI experience
- All existing commands and features work identically
- Configuration and sessions are unchanged
- Only the default UI mode has changed

## Why TUI as Default?

1. **Better UX** - Split-screen layout provides more context
2. **Modern** - Uses Textual framework (modern, actively maintained)
3. **Richer Display** - Shows operations log and content side-by-side
4. **Same Features** - Full feature parity with CLI
5. **Optional** - madiuxexp dependency can be installed separately if needed

## Verification

```bash
# Check the help text
madison --help

# Output shows:
# [default: tui]
```

## Files Modified

| File | Changes |
|------|---------|
| `src/madison/cli.py` | Changed default --ui to "tui" |
| `README.md` | Reordered sections, TUI first |
| `INTEGRATION_PROGRESS.md` | Updated usage examples |
| `PHASE_1_2_3_SUMMARY.md` | Updated usage examples |

## No Breaking Changes

- Existing scripts using `madison --ui=cli` still work
- Environment variables unchanged
- Configuration format unchanged
- All commands work identically
- Only the default behavior changed

---

**Date:** November 1, 2025
**Status:** ✅ Complete
