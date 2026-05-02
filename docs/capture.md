# Capture

WaySnip has two capture modes.

## Region capture (default)

```bash
waysnip region
```

The screen freezes into a static image and you draw a selection rectangle. This avoids capturing hover effects or tooltips that appear while selecting. The magnifier helps with precise edge placement.

This is the default when you press PrintScreen or run `waysnip` with no arguments.

## Fullscreen capture

```bash
waysnip fullscreen
```

Captures the entire screen immediately and opens the editor. Bound to **Ctrl+PrintScreen** after running `waysnip setup`.

## Cursor visibility

By default the cursor is not included in captures. To include it, set `show_cursor = true` in the `[capture]` section of your config.

## After capture

The `after_capture` setting controls what happens after a capture completes:

| Value | Behavior |
|---|---|
| `"editor"` (default) | Opens the editor |
| `"clipboard"` | Copies to clipboard only |
| `"save"` | Saves to disk only |
| `"clipboard+save"` | Copies to clipboard and saves to disk |

When `auto_copy_clipboard` is enabled (default), the capture is always copied to the clipboard regardless of the `after_capture` setting.

## Multi-monitor

WaySnip captures across all monitors in region and fullscreen modes. Different DPI monitors are a known limitation that is being improved.

## Capture backends

WaySnip dispatches to one of two screen-capture binaries based on the active compositor (read from `XDG_CURRENT_DESKTOP`):

| Compositor | Preferred backend | Fall-through |
|---|---|---|
| GNOME, Unity | `gnome-screenshot` | `grim` |
| sway, Hyprland, Wayfire, river, wlroots | `grim` | `gnome-screenshot` |
| Other / unknown | `gnome-screenshot` | `grim` |

If the preferred backend is missing or fails (timeout, nonzero return, empty output), WaySnip automatically tries the other one. Install whichever fits your compositor (see [Install](install.md)).
