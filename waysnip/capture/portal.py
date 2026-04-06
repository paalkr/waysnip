"""Screen capture backends for Wayland.

On GNOME: uses gnome-screenshot for fast silent capture, falls back to
xdg-desktop-portal interactive mode for window selection.

On wlroots compositors: could use grim (not yet implemented).
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


def capture_fullscreen(show_cursor: bool = False) -> Path | None:
    """Take a full-screen screenshot silently.

    Uses gnome-screenshot which works on GNOME Wayland without portal
    permission dialogs.
    """
    tmp = tempfile.NamedTemporaryFile(suffix=".png", prefix="waysnip_", delete=False)
    tmp.close()
    path = Path(tmp.name)

    cmd = ["gnome-screenshot", "-f", str(path)]
    if show_cursor:
        cmd.append("--include-pointer")

    try:
        result = subprocess.run(cmd, capture_output=True, timeout=10)
        if result.returncode != 0:
            print(f"gnome-screenshot failed: {result.stderr.decode()}")
            return None
        if not path.exists() or path.stat().st_size == 0:
            print("gnome-screenshot produced no output")
            return None
        return path
    except FileNotFoundError:
        print("gnome-screenshot not found, falling back to portal")
        return _capture_via_portal(interactive=False)
    except subprocess.TimeoutExpired:
        print("gnome-screenshot timed out")
        return None


def capture_interactive() -> Path | None:
    """Open the portal's interactive screenshot picker (GNOME's own UI).

    This shows GNOME's built-in screenshot tool where the user can select
    a region, window, or full screen.
    """
    # For interactive mode, the portal is the right approach since GNOME
    # shows its own polished UI.
    return _capture_via_portal(interactive=True)


def _capture_via_portal(interactive: bool) -> Path | None:
    """Use gdbus to call the xdg-desktop-portal Screenshot method.

    We use gdbus subprocess instead of Qt's D-Bus bindings because
    PyQt6's QDBusConnection.connect() has issues with portal response
    signals on GNOME.
    """

    interactive_str = "true" if interactive else "false"
    cmd = [
        "gdbus", "call", "--session",
        "--dest", "org.freedesktop.portal.Desktop",
        "--object-path", "/org/freedesktop/portal/desktop",
        "--method", "org.freedesktop.portal.Screenshot.Screenshot",
        "",
        f'{{"interactive": <{interactive_str}>}}',
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            print(f"Portal call failed: {result.stderr}")
            return None
    except subprocess.TimeoutExpired:
        print("Portal call timed out")
        return None

    # The gdbus call returns immediately with a request path.
    # The actual screenshot happens asynchronously via GNOME's UI.
    # We need to listen for the response signal.
    # Use gdbus monitor for this.
    try:
        monitor = subprocess.Popen(
            [
                "dbus-monitor", "--session",
                "type='signal',interface='org.freedesktop.portal.Request',member='Response'",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        # Wait for the user to complete the screenshot in GNOME's UI
        # (up to 60 seconds for interactive mode)
        timeout = 60 if interactive else 15
        output_lines = []
        import select
        import time

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            ready, _, _ = select.select([monitor.stdout], [], [], min(remaining, 0.5))
            if ready:
                line = monitor.stdout.readline().decode("utf-8", errors="replace")
                if not line:
                    break
                output_lines.append(line)
                # Look for the uri in the response
                if "string" in line and "file://" in line:
                    monitor.kill()
                    uri = line.strip().split('"')[1] if '"' in line else ""
                    if uri.startswith("file://"):
                        from urllib.parse import urlparse, unquote
                        return Path(unquote(urlparse(uri).path))

                # Check for response code indicating failure
                if "uint32 1" in line or "uint32 2" in line:
                    monitor.kill()
                    print("Portal screenshot was cancelled or denied")
                    return None

        monitor.kill()
        monitor.wait(timeout=2)
        print("Portal interactive screenshot timed out")
        return None

    except Exception as e:
        print(f"Portal monitor error: {e}")
        return None
