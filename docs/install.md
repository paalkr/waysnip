# Install

## Prerequisites

- Python 3.12 or newer
- A Wayland-based Linux desktop
- `wl-clipboard` (for clipboard support)
- One screen-capture binary, depending on your compositor:
  - GNOME / Unity: `gnome-screenshot`
  - sway, Hyprland, Wayfire, river, or other wlroots-based compositors: `grim`

WaySnip auto-detects the compositor via `XDG_CURRENT_DESKTOP` and falls through to the next backend if the preferred one isn't installed or fails. The fall-through order is the preferred binary, then the `org.freedesktop.portal.Screenshot` D-Bus portal, then the other binary.

On GNOME 49 and newer (Ubuntu 26.04+), `gnome-screenshot` no longer has access to the shell's screenshot API and fails with `AccessDenied`. WaySnip falls through to the portal there. `waysnip setup` pre-grants the portal permission so captures stay silent (no per-shot dialog).

Install system dependencies on Ubuntu/Debian:

```bash
# GNOME / Unity
sudo apt install wl-clipboard gnome-screenshot

# sway / Hyprland / wlroots
sudo apt install wl-clipboard grim
```

## Install via uv (recommended)

```bash
uv tool install waysnip
```

If you don't have [uv](https://docs.astral.sh/uv/), install it with `curl -LsSf https://astral.sh/uv/install.sh | sh`.

## Install via pipx

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
waysnip uninstall && uv tool uninstall waysnip
```

Use `pipx uninstall waysnip` or `pip uninstall waysnip` instead if that's how you installed.

`waysnip uninstall` removes keybindings, the autostart entry, and the launcher wrapper. It also restores GNOME's default screenshot keys.
