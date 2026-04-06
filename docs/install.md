# Install

## Prerequisites

- Python 3.12 or newer
- Ubuntu 24.04 or similar Wayland-based desktop
- `wl-clipboard` (for clipboard support)
- `gnome-screenshot` (for screen capture)

Install system dependencies on Ubuntu/Debian:

```bash
sudo apt install wl-clipboard gnome-screenshot
```

## Install via pipx (recommended)

```bash
pipx install waysnip
```

## Install via pip

```bash
pip install --user waysnip
```

## Install from source

```bash
git clone https://github.com/paalkr/waysnip.git
cd waysnip
pip install -e .
```

## Setup keybindings

After installing, run:

```bash
waysnip setup
```

This does three things:

1. Installs a launcher wrapper at `~/.local/bin/waysnip-launch`
2. Creates an autostart entry so WaySnip starts in the system tray on login
3. Binds PrintScreen to region capture and Ctrl+PrintScreen to fullscreen capture

The setup also restarts `gsd-media-keys` so the keybindings take effect immediately.

## Uninstall

```bash
waysnip uninstall && pipx uninstall waysnip
```

`waysnip uninstall` removes keybindings, the autostart entry, and the launcher wrapper. It also restores GNOME's default screenshot keys.
