# Changelog

All notable changes to WaySnip will be documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/).

## [0.6.0b1] - 2026-05-02

### Added
- `grim` capture backend for sway, Hyprland, Wayfire, river, and other wlroots-based compositors
- `XDG_CURRENT_DESKTOP` dispatch in `capture/portal.py`: GNOME / Unity → `gnome-screenshot` first, wlroots-based → `grim` first, with automatic fall-through to the other backend on any failure (missing binary, nonzero return, timeout, empty output)

### Fixed
- WaySnip no longer hangs on sway / wlroots compositors (closes #2). Fullscreen capture now picks the right backend for the active desktop.

### Notes
- Pre-release. Install with `pip install --pre waysnip` or `pipx install --pip-args '--pre' waysnip`.

## [0.5.0] - 2026-04-24

### Removed
- Window capture mode (`waysnip window`, tray "Window Capture" menu item, "Window" left-click action). The portal-based interactive backend was the only blocking subprocess loop in the app and was the proximate cause of a tray crash when the portal dialog was dismissed without taking a screenshot. GNOME's built-in `Super+Print` covers window capture for users who need it.

### Fixed
- Tray no longer freezes the Qt event loop when the GNOME portal dialog is cancelled. With the portal path removed entirely, region and fullscreen capture clicks can no longer queue up behind a stalled portal monitor and fire as a delayed burst.

## [0.4.0] - 2026-04-10

### Added
- Layer ordering: bring to front, send to back, move up, move down via Edit menu and context menu
- Keyboard shortcuts for layer ordering: Ctrl+Shift+]/[, Ctrl+]/[
- Right-click context menu on annotations (reorder, delete, clone)
- Per-tool drawing properties: each tool remembers its own color, width, opacity, and font independently
- Per-tool state persisted in `~/.config/waysnip/tool_state.json`
- Edit > Reset Tool Defaults menu action
- Blur regions show a dashed boundary while drawing and when selected
- Z-order preserved in saved PNG metadata

### Fixed
- Switching tools while an annotation is selected now works (selection is cleared on tool switch)
- Objects no longer stick to the mouse after using the context menu
- Blur regions always render below other annotations regardless of draw order

### Removed
- Global drawing defaults from config (`default_pen_color`, `default_pen_width`, `default_fill_color`, `default_font`, `default_font_size`, `default_blur_block_size`). These are now per-tool properties.

## [0.3.0] - 2026-04-06

### Added
- Custom app icon (monitor with selection rectangle) for launcher, dock, tray, and editor windows
- Bright symbolic tray icon that's visible on dark panels
- `waysnip setup` installs the icon to the user's icon theme
- GNOME dock now shows "WaySnip" with the proper icon instead of "python3"

### Fixed
- `waysnip setup` installs an app launcher `.desktop` entry (moved from 0.2.1)
- `waysnip uninstall` cleans up the icon and launcher entry

## [0.2.1] - 2026-04-06

### Fixed
- `waysnip setup` now installs an app launcher entry so WaySnip appears in the GNOME application menu
- `waysnip uninstall` removes the app launcher entry

## [0.2.0] - 2026-04-06

### Fixed
- Region selector now covers the GNOME top panel and dock (switched from constrained single window to per-screen fullscreen overlays)
- Editor zoom status bar updates in real time when zooming with Ctrl+scroll
- Initial fit-to-view is more reliable (deferred until layout is complete)

### Improved
- Editor window sizes itself to fit the image at 100% when possible, instead of a fixed 1200x800
- Small snippets open at 100% zoom instead of being upscaled to fill the window
- Image stays fitted when resizing the editor window (until you manually zoom)
- Smoother antialiasing when viewing images zoomed out (SmoothTransformation on background)
- Pressing PrintScreen while the selector is open cancels and restarts with a fresh capture

### Added
- Ctrl+1 shortcut for actual size (100%) zoom
- Ctrl+0 shortcut for fit-to-window zoom

## [0.1.0] - 2026-04-06

### Added
- Region, window, and fullscreen capture via gnome-screenshot and xdg-desktop-portal
- Annotation editor with 11 tools: select, rectangle, ellipse, arrow, line, text, numbered markers, freehand, highlight, blur/pixelate, crop
- Properties panel with color picker, recent colors, stroke width, opacity
- Undo/redo support
- PNG metadata for re-editable annotations (original image + annotation data embedded in PNG iTXt chunks)
- Gallery with thumbnail browser and context menu (copy, edit, reveal, flatten, delete)
- System tray icon with configurable left-click action
- Settings dialog with 5 tabs (Capture, Save, Editor, Tray, About)
- CLI with subcommands: region, window, fullscreen, gallery, config, tray, setup, uninstall
- PrintScreen keybinding setup for GNOME (`waysnip setup`)
- Autostart on login
- Dark theme stylesheet
- Copy to clipboard on capture and on save (configurable)
- Configurable save directory and filename patterns with strftime
