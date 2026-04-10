# WaySnip

WaySnip is a lightweight screenshot and annotation tool for Wayland desktops. Capture a region, fullscreen, or window, then annotate with shapes, text, arrows, blur, and more. Annotations are stored in the PNG metadata so you can re-edit them later.

## Features

- Region, fullscreen, and window capture modes
- 11 annotation tools: select, rectangle, ellipse, arrow, line, text, numbered markers, freehand pen, highlight, blur, crop
- Layer ordering: bring to front, send to back, move up/down
- Per-tool drawing properties (each tool remembers its own color, width, opacity)
- Non-destructive saves with re-editable annotations
- Screenshot gallery with live updates
- Magnifier for precise region selection
- System tray integration
- GNOME keybinding setup out of the box
- TOML-based configuration with a settings GUI

## Quick install

```bash
pipx install waysnip
waysnip setup
```

That gives you PrintScreen for region capture and Ctrl+PrintScreen for fullscreen. See the [install guide](install.md) for details.

Ready to go? Head to [Getting started](getting-started.md).
