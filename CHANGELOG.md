# Changelog

All notable changes to WaySnip will be documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/).

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
