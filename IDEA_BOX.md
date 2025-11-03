# Madison Idea Box

A repository for ideas, refinements, and potential enhancements to Madison.

## UI/UX Ideas

### Scrollbar Refinements
- Current scrollbar width is 1 character - may be configurable in future
- Consider aesthetic improvements to scrollbar appearance
- Scrollbar visibility on both left and right panes

### Pane Focus Indicator
- Currently uses yellow/accent border with background boost
- Consider alternative visual indicators (cursor change, different styling)
- Make focus state more prominent or subtle based on user preference

### Input History Navigation
- Currently uses Alt+Up/Alt+Down for history
- Consider if this feels natural or if other keybindings would be better
- Could add visual indicator showing which history item is active

## Performance/Architecture Ideas

### Scrollbuffer Management
- Currently session-based with no limit
- Future: Implement memory-based limits or time-based retention
- Could be configurable via settings

### Logging Configuration
- Currently DEBUG for madison, INFO for third-party libs
- Works well but may want to expose as user preference
- Could add per-module logging control

## Feature Ideas

### Status Display
- Abandoned Enhancement 4 (Status Bar) in favor of scrollbuffers
- Could revisit later if needed - might want quick status visibility
- Could be subtle header/footer instead of dedicated status bar

### Content Display Enhancements
- File formatting (Enhancement 3) now supports 24+ languages
- Could expand language support or add custom themes
- Syntax highlighting theme could be configurable
- **Add line-wrap to content output window** - long lines should wrap instead of requiring horizontal scroll
- **Treat most content as markdown by default** - render markdown formatting (bold, lists, code blocks, etc.) in responses. When content contains code blocks or is file/script output, render according to file type rules (syntax highlighting for Python, JavaScript, etc.)

### Orchestration Visualization
- Currently shows task counts and completion status
- Could add visual progress indicators or timeline view
- Could show task dependencies or execution flow

## Known Tweaks/Refinements Mentioned

User mentioned "tweaks I alluded to earlier":
- Visual indicators for streaming responses (⏳ Generating...) - DONE
- Operation logging format with ↳ arrows - DONE
- Real-time streaming without buffering - DONE
- Need to revisit if there were other tweaks not yet implemented

## Testing Observations

- Scrolling implementation required fixing InputTextArea key handling
- Textual's focus model required app-level on_key handler
- VerticalScroll containers work well with height: 1fr + width: 1fr pattern
- ContentPane height must not constrain content size (height: auto didn't work)

## Areas for Future Exploration

- [ ] Terminal color scheme/theming
- [ ] Custom keybinding configuration
- [ ] User preferences/settings system
- [ ] Plugin/extension system
- [ ] Session management enhancements
- [ ] Context window optimization
- [ ] Model-specific optimizations
- [ ] Tool execution improvements
