# Configuration

## Config file

WaySnip stores its config at:

```
~/.config/waysnip/config.toml
```

The file is created automatically with defaults the first time you open the settings GUI or edit the config.

## Settings GUI

```bash
waysnip config
```

## Edit TOML directly

```bash
waysnip config --edit
```

Opens the config file in `$EDITOR` (falls back to `xdg-open`).

## Full example config

All values shown are the defaults:

```toml
[capture]
after_capture = "editor"       # "editor", "clipboard", "save", "clipboard+save"
auto_copy_clipboard = true
show_cursor = false
auto_save = true               # save snips to the gallery without pressing Ctrl+S

[save]
directory = "~/Pictures/Screenshots"
pattern = "Screenshot_%Y-%m-%d_%H-%M-%S.png"
mode = "annotated"             # "annotated" or "editable"

[editor]
copy_on_save = true
recent_colors = []

[magnifier]
enabled = true
zoom = 5
size = 150

[tray]
enabled = true
left_click_action = "region"
```

## Section reference

### [capture]

| Key | Type | Default | Description |
|---|---|---|---|
| `after_capture` | string | `"editor"` | What to do after capture: `"editor"`, `"clipboard"`, `"save"`, `"clipboard+save"` |
| `auto_copy_clipboard` | bool | `true` | Always copy captures to clipboard |
| `show_cursor` | bool | `false` | Include the cursor in captures |
| `auto_save` | bool | `true` | Save fresh snips to the gallery immediately, and persist on Ctrl+C in the editor, without needing Ctrl+S |

### [save]

| Key | Type | Default | Description |
|---|---|---|---|
| `directory` | string | `"~/Pictures/Screenshots"` | Where to save screenshots |
| `pattern` | string | `"Screenshot_%Y-%m-%d_%H-%M-%S.png"` | Filename pattern (supports strftime: `%Y` year, `%m` month, `%d` day, `%H` hour, `%M` minute, `%S` second) |
| `mode` | string | `"annotated"` | `"annotated"` saves the flattened image with annotation data embedded for re-editing. `"editable"` saves annotation data as the primary image content. |

### [editor]

| Key | Type | Default | Description |
|---|---|---|---|
| `copy_on_save` | bool | `true` | Copy to clipboard when saving |
| `recent_colors` | list | `[]` | Recently used colors (managed automatically, max 8) |

Drawing defaults (color, width, opacity, font) are now stored per-tool. See [Per-tool properties](#per-tool-properties) below.

### [magnifier]

| Key | Type | Default | Description |
|---|---|---|---|
| `enabled` | bool | `true` | Show magnifier during region selection |
| `zoom` | int | `5` | Magnifier zoom level |
| `size` | int | `150` | Magnifier window size in pixels |

### [tray]

| Key | Type | Default | Description |
|---|---|---|---|
| `enabled` | bool | `true` | Show system tray icon |
| `left_click_action` | string | `"region"` | Action when left-clicking the tray icon |

## Per-tool properties

Each annotation tool remembers its own drawing settings (color, width, opacity, font, etc.) independently. When you change the pen color while using the arrow tool, that color is remembered for arrows but doesn't affect rectangles or other tools.

Per-tool properties are stored in:

```
~/.config/waysnip/tool_state.json
```

This file is loaded when the editor opens and saved when it closes. You don't need to edit it manually.

To reset all tools to their defaults, use **Edit > Reset Tool Defaults** in the editor menu bar.
