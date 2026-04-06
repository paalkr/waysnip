# Changelog

All notable changes to WaySnip will be documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/).

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
