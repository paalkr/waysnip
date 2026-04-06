"""CLI entry point — parse arguments and dispatch to the application."""

from __future__ import annotations

import argparse
import os
import subprocess

from waysnip.constants import APP_DISPLAY_NAME, APP_VERSION, CONFIG_FILE


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="waysnip",
        description=f"{APP_DISPLAY_NAME} — lightweight Wayland screenshot & annotation tool",
    )
    parser.add_argument(
        "--version", action="version", version=f"{APP_DISPLAY_NAME} {APP_VERSION}"
    )

    sub = parser.add_subparsers(dest="command")

    sub.add_parser("region", help="Region capture (default)")
    sub.add_parser("window", help="Window capture (portal interactive mode)")
    sub.add_parser("fullscreen", help="Fullscreen capture")
    sub.add_parser("gallery", help="Open the screenshot gallery")
    sub.add_parser("tray", help="Start in system tray (no capture)")
    sub.add_parser("setup", help="Install keybindings and autostart")

    config_parser = sub.add_parser("config", help="Open settings GUI")
    config_parser.add_argument(
        "--edit",
        action="store_true",
        help="Open the config TOML in $EDITOR instead of the GUI",
    )

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    command = args.command or "region"

    # `config --edit` is a special case — just open the file in $EDITOR.
    if command == "config" and getattr(args, "edit", False):
        editor = os.environ.get("EDITOR", "xdg-open")
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        if not CONFIG_FILE.exists():
            # Ensure the file exists so the editor doesn't complain.
            from waysnip.config import AppConfig

            AppConfig().save_to_disk()
        subprocess.run([editor, str(CONFIG_FILE)])
        return

    if command == "setup":
        _setup()
        return

    # Hand off to the application layer (handles single-instance IPC).
    from waysnip.app import run

    run(command)


def _setup() -> None:
    """Install keybindings and autostart entry."""
    import shutil
    from pathlib import Path

    # Find the waysnip binary
    waysnip_bin = shutil.which("waysnip")
    if not waysnip_bin:
        # Try the venv
        venv_bin = Path(__file__).parent.parent / ".venv" / "bin" / "waysnip"
        if venv_bin.exists():
            waysnip_bin = str(venv_bin)
        else:
            print("Error: waysnip not found in PATH")
            return

    # Install autostart desktop entry
    autostart_dir = Path.home() / ".config" / "autostart"
    autostart_dir.mkdir(parents=True, exist_ok=True)
    autostart_file = autostart_dir / "waysnip.desktop"

    desktop_content = f"""[Desktop Entry]
Name=WaySnip
Comment=WaySnip screenshot tool (tray)
Exec={waysnip_bin} tray
Icon=waysnip
Terminal=false
Type=Application
X-GNOME-Autostart-enabled=true
Hidden=false
"""
    autostart_file.write_text(desktop_content)
    print(f"Autostart installed: {autostart_file}")

    # Install keybindings via gsettings
    _setup_keybindings(waysnip_bin)

    print()
    print("Setup complete. WaySnip will:")
    print("  - Start in system tray on login")
    print("  - PrintScreen → region capture")
    print("  - Ctrl+PrintScreen → fullscreen capture")
    print(f"  - Using: {waysnip_bin}")


def _setup_keybindings(waysnip_bin: str) -> None:
    """Configure GNOME keybindings for WaySnip."""
    custom_path = "/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings"

    def gsettings(*args):
        subprocess.run(["gsettings"] + list(args), capture_output=True)

    # Disable GNOME defaults
    gsettings("set", "org.gnome.shell.keybindings", "screenshot", "[]")
    gsettings("set", "org.gnome.shell.keybindings", "screenshot-window", "[]")
    gsettings("set", "org.gnome.shell.keybindings", "show-screenshot-ui", "[]")

    # Get existing custom keybindings
    result = subprocess.run(
        ["gsettings", "get", "org.gnome.settings-daemon.plugins.media-keys", "custom-keybindings"],
        capture_output=True, text=True,
    )
    existing = result.stdout.strip()

    # Add our slots if not present
    slots = [f"'{custom_path}/waysnip0/'", f"'{custom_path}/waysnip1/'"]
    for slot in slots:
        if slot not in existing:
            if existing == "@as []":
                existing = f"[{slot}]"
            else:
                existing = existing.rstrip("]") + f", {slot}]"

    gsettings("set", "org.gnome.settings-daemon.plugins.media-keys", "custom-keybindings", existing)

    # PrintScreen → region
    base = f"org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:{custom_path}/waysnip0/"
    gsettings("set", base, "name", "WaySnip Region")
    gsettings("set", base, "command", f"{waysnip_bin} region")
    gsettings("set", base, "binding", "Print")

    # Ctrl+PrintScreen → fullscreen
    base = f"org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:{custom_path}/waysnip1/"
    gsettings("set", base, "name", "WaySnip Fullscreen")
    gsettings("set", base, "command", f"{waysnip_bin} fullscreen")
    gsettings("set", base, "binding", "<Ctrl>Print")

    print("Keybindings installed")
