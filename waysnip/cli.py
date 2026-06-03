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
    sub.add_parser("fullscreen", help="Fullscreen capture")
    sub.add_parser("gallery", help="Open the screenshot gallery")
    sub.add_parser("tray", help="Start in system tray (no capture)")
    sub.add_parser("setup", help="Install keybindings and autostart")
    sub.add_parser("uninstall", help="Remove keybindings and autostart")

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

    if command == "uninstall":
        _uninstall()
        return

    # Hand off to the application layer (handles single-instance IPC).
    from waysnip.app import run

    run(command)


def _setup() -> None:
    """Install keybindings and autostart entry."""
    import shutil
    import sys
    from pathlib import Path

    # Find the waysnip binary. Priority:
    # 1. The actual command that's running right now (sys.argv[0] resolved)
    # 2. `which waysnip` on PATH (works for pipx, pip --user, system pip)
    # 3. Development venv fallback
    running = Path(sys.argv[0]).resolve()
    if running.exists() and running.name == "waysnip":
        waysnip_bin = str(running)
    else:
        waysnip_bin = shutil.which("waysnip")
    if not waysnip_bin:
        venv_bin = Path(__file__).parent.parent / ".venv" / "bin" / "waysnip"
        if venv_bin.exists():
            waysnip_bin = str(venv_bin)
        else:
            print("Error: waysnip not found in PATH or venv")
            return

    # Create a wrapper script that preserves the environment GNOME needs
    wrapper_dir = Path.home() / ".local" / "bin"
    wrapper_dir.mkdir(parents=True, exist_ok=True)
    wrapper = wrapper_dir / "waysnip-launch"

    wrapper_content = f"""#!/bin/bash
# WaySnip launcher — preserves environment for GNOME keybindings
export XDG_RUNTIME_DIR="${{XDG_RUNTIME_DIR:-/run/user/$(id -u)}}"
export WAYLAND_DISPLAY="${{WAYLAND_DISPLAY:-wayland-0}}"
export DISPLAY="${{DISPLAY:-:0}}"
export DBUS_SESSION_BUS_ADDRESS="${{DBUS_SESSION_BUS_ADDRESS:-unix:path=$XDG_RUNTIME_DIR/bus}}"
exec {waysnip_bin} "$@"
"""
    wrapper.write_text(wrapper_content)
    wrapper.chmod(0o755)
    print(f"Launcher installed: {wrapper}")

    # Install app icon
    icon_src = Path(__file__).parent / "resources" / "icons" / "waysnip.svg"
    if icon_src.exists():
        icon_dir = Path.home() / ".local" / "share" / "icons" / "hicolor" / "scalable" / "apps"
        icon_dir.mkdir(parents=True, exist_ok=True)
        import shutil as _shutil
        _shutil.copy2(icon_src, icon_dir / "waysnip.svg")
        print(f"Icon installed: {icon_dir / 'waysnip.svg'}")

    # Install autostart desktop entry
    autostart_dir = Path.home() / ".config" / "autostart"
    autostart_dir.mkdir(parents=True, exist_ok=True)
    autostart_file = autostart_dir / "waysnip.desktop"

    desktop_content = f"""[Desktop Entry]
Name=WaySnip
Comment=WaySnip screenshot tool (tray)
Exec={wrapper} tray
Icon=waysnip
Terminal=false
Type=Application
X-GNOME-Autostart-enabled=true
Hidden=false
"""
    autostart_file.write_text(desktop_content)
    print(f"Autostart installed: {autostart_file}")

    # Install application launcher entry
    apps_dir = Path.home() / ".local" / "share" / "applications"
    apps_dir.mkdir(parents=True, exist_ok=True)
    app_desktop = apps_dir / "waysnip.desktop"

    app_content = f"""[Desktop Entry]
Name=WaySnip
Comment=Screenshot and annotation tool for Wayland
Exec={wrapper} tray
Icon=waysnip
Terminal=false
Type=Application
Categories=Graphics;Utility;
Keywords=screenshot;snip;capture;annotate;
"""
    app_desktop.write_text(app_content)
    print(f"App launcher installed: {app_desktop}")

    # Pre-grant silent portal screenshots (needed on GNOME 49+ where
    # gnome-screenshot lost access to the shell's screenshot API).
    _grant_portal_permission()

    # Install keybindings using the wrapper
    _setup_keybindings(str(wrapper))

    # Restart gsd-media-keys so it picks up the new keybindings immediately
    _restart_media_keys()

    print()
    print("Setup complete. WaySnip will:")
    print("  - Start in system tray on login")
    print("  - PrintScreen → region capture")
    print("  - Ctrl+PrintScreen → fullscreen capture")
    print(f"  - Using: {waysnip_bin}")


def _grant_portal_permission() -> None:
    """Grant WaySnip silent screenshots in the xdg portal permission store.

    The desktop portal resolves the app id "waysnip" from the systemd scope
    created when WaySnip is launched via its .desktop entry. With this grant,
    the org.freedesktop.portal.Screenshot backend captures without showing a
    permission dialog. Best-effort: skipped silently when the permission
    store isn't available.
    """
    try:
        result = subprocess.run(
            [
                "gdbus", "call", "--session",
                "-d", "org.freedesktop.impl.portal.PermissionStore",
                "-o", "/org/freedesktop/impl/portal/PermissionStore",
                "-m", "org.freedesktop.impl.portal.PermissionStore.SetPermission",
                "screenshot", "true", "screenshot", "waysnip", "['yes']",
            ],
            capture_output=True,
        )
    except FileNotFoundError:
        return
    if result.returncode == 0:
        print("Portal screenshot permission granted")


def _revoke_portal_permission() -> None:
    """Remove the WaySnip entry from the portal permission store (best-effort)."""
    try:
        subprocess.run(
            [
                "gdbus", "call", "--session",
                "-d", "org.freedesktop.impl.portal.PermissionStore",
                "-o", "/org/freedesktop/impl/portal/PermissionStore",
                "-m", "org.freedesktop.impl.portal.PermissionStore.DeletePermission",
                "screenshot", "screenshot", "waysnip",
            ],
            capture_output=True,
        )
    except FileNotFoundError:
        pass


def _restart_media_keys() -> None:
    """Restart GNOME's media keys daemon to pick up new keybindings."""
    try:
        subprocess.run(["killall", "gsd-media-keys"], capture_output=True)
        import time
        time.sleep(1)
        subprocess.Popen(
            ["/usr/libexec/gsd-media-keys"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print("Media keys daemon restarted")
    except Exception:
        print("Note: restart gsd-media-keys manually or log out/in for keybindings to take effect")


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


def _uninstall() -> None:
    """Remove keybindings, autostart, and wrapper."""
    from pathlib import Path

    # Remove autostart
    autostart_file = Path.home() / ".config" / "autostart" / "waysnip.desktop"
    if autostart_file.exists():
        autostart_file.unlink()
        print(f"Removed: {autostart_file}")

    # Remove app launcher
    app_desktop = Path.home() / ".local" / "share" / "applications" / "waysnip.desktop"
    if app_desktop.exists():
        app_desktop.unlink()
        print(f"Removed: {app_desktop}")

    # Remove icon
    icon_file = Path.home() / ".local" / "share" / "icons" / "hicolor" / "scalable" / "apps" / "waysnip.svg"
    if icon_file.exists():
        icon_file.unlink()
        print(f"Removed: {icon_file}")

    # Remove wrapper
    wrapper = Path.home() / ".local" / "bin" / "waysnip-launch"
    if wrapper.exists():
        wrapper.unlink()
        print(f"Removed: {wrapper}")

    # Remove the portal permission grant
    _revoke_portal_permission()

    # Restore GNOME default screenshot keys
    def gsettings(*args):
        subprocess.run(["gsettings"] + list(args), capture_output=True)

    gsettings("reset", "org.gnome.shell.keybindings", "screenshot")
    gsettings("reset", "org.gnome.shell.keybindings", "screenshot-window")
    gsettings("reset", "org.gnome.shell.keybindings", "show-screenshot-ui")

    # Force GNOME Shell to re-grab the restored keybindings by toggling
    import time
    gsettings("set", "org.gnome.shell.keybindings", "show-screenshot-ui", "[]")
    time.sleep(0.3)
    gsettings("reset", "org.gnome.shell.keybindings", "show-screenshot-ui")

    # Remove our custom keybindings from the list
    custom_path = "/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings"
    result = subprocess.run(
        ["gsettings", "get", "org.gnome.settings-daemon.plugins.media-keys", "custom-keybindings"],
        capture_output=True, text=True,
    )
    existing = result.stdout.strip()

    # Filter out waysnip entries
    import ast
    try:
        paths = ast.literal_eval(existing)
        paths = [p for p in paths if "waysnip" not in p]
        if paths:
            new_val = str(paths)
        else:
            new_val = "@as []"
    except Exception:
        new_val = existing

    gsettings("set", "org.gnome.settings-daemon.plugins.media-keys", "custom-keybindings", new_val)

    # Clear the waysnip binding dconf entries
    subprocess.run(["dconf", "reset", "-f", f"{custom_path}/waysnip0/"], capture_output=True)
    subprocess.run(["dconf", "reset", "-f", f"{custom_path}/waysnip1/"], capture_output=True)

    # Kill running waysnip instances
    subprocess.run(["pkill", "-f", "waysnip tray"], capture_output=True)
    subprocess.run(["pkill", "-f", "waysnip-launch"], capture_output=True)
    print("Stopped running WaySnip instances")

    _restart_media_keys()

    print("GNOME default screenshot keys restored")
    print("Uninstall complete")
