# WaySnip

Lightweight screenshot and annotation tool for Linux Wayland. Captures your screen, lets you select a region, annotate with shapes and text, and saves with a single shortcut. Built for documentation workflows and quick sharing.

Tested on Ubuntu 24.04 with GNOME Shell 46 on Wayland.

## Features

- Region, window, and fullscreen capture with frozen screen (menus don't close)
- 11 annotation tools: rectangle, ellipse, arrow, line, text, numbered markers, freehand pen, highlight, blur/pixelate, crop
- Color picker with recent colors, stroke width, opacity, font controls
- Undo/redo, clone, multi-select, keyboard shortcuts for every tool
- Re-editable annotations stored as PNG metadata
- Gallery with thumbnail browser
- System tray with hotkey support
- Settings UI backed by TOML config
- Auto-copy to clipboard on capture and save
- Dark theme

## Install

```bash
pipx install waysnip
waysnip setup
```

`waysnip setup` binds PrintScreen to region capture, Ctrl+PrintScreen to fullscreen, and enables tray autostart on login.

### From source

```bash
git clone https://github.com/paalkr/waysnip.git
cd waysnip
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
waysnip setup
```

### Requirements

- Linux with Wayland (GNOME recommended)
- Python 3.12+
- `gnome-screenshot` and `wl-clipboard` (pre-installed on Ubuntu 24.04)

## Quick start

| Action | How |
|--------|-----|
| Region capture | Press **Print** or `waysnip region` |
| Fullscreen capture | Press **Ctrl+Print** or `waysnip fullscreen` |
| Open gallery | `waysnip gallery` |
| Open settings | `waysnip config` |
| Start tray only | `waysnip tray` |

## Editor shortcuts

| Key | Action |
|-----|--------|
| V | Select tool |
| R | Rectangle |
| E | Ellipse |
| A | Arrow |
| L | Line |
| T | Text |
| N | Numbered marker |
| P | Freehand pen |
| H | Highlight |
| B | Blur/pixelate |
| C | Crop |
| Ctrl+Z | Undo |
| Ctrl+Y | Redo |
| Ctrl+S | Save |
| Ctrl+Shift+S | Save as |
| Ctrl+C | Copy to clipboard |
| Ctrl+D | Clone selected |
| Del | Delete selected |
| Ctrl+Shift+] | Bring to front |
| Ctrl+Shift+[ | Send to back |
| Ctrl+] | Move up one layer |
| Ctrl+[ | Move down one layer |
| Ctrl+1 | Actual size (100%) |
| Ctrl+0 | Fit to window |

## Configuration

Config file: `~/.config/waysnip/config.toml`

```toml
[capture]
after_capture = "editor"    # "editor", "clipboard", "save", "clipboard+save"
auto_copy_clipboard = true
show_cursor = false

[save]
directory = "~/Pictures/Screenshots"
pattern = "Screenshot_%Y-%m-%d_%H-%M-%S.png"
mode = "annotated"          # "annotated" (re-editable) or "editable" (smaller)

[editor]
copy_on_save = true

[tray]
enabled = true
left_click_action = "region"
```

Edit via GUI: `waysnip config`
Edit directly: `waysnip config --edit`

## Uninstall

```bash
waysnip uninstall
pipx uninstall waysnip
```

`waysnip uninstall` restores GNOME's default screenshot keys and removes the autostart entry.

## License

GPL-3.0
