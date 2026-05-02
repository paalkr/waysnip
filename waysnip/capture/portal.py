"""Full-screen capture backend.

Dispatches to `gnome-screenshot` or `grim` based on the active desktop
environment (read from `XDG_CURRENT_DESKTOP`), with fall-through to the
other backend if the preferred one fails for any reason.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

_GNOME_TOKENS = frozenset({"gnome", "gnome-classic", "gnome-flashback", "unity"})
_WLROOTS_TOKENS = frozenset({"sway", "hyprland", "wlroots", "wayfire", "river", "miracle-wm"})


def _desktop_tokens() -> set[str]:
    raw = os.environ.get("XDG_CURRENT_DESKTOP", "")
    return {tok.strip().lower() for tok in raw.split(":") if tok.strip()}


def _backend_order() -> list[str]:
    tokens = _desktop_tokens()
    if tokens & _WLROOTS_TOKENS:
        return ["grim", "gnome-screenshot"]
    if tokens & _GNOME_TOKENS:
        return ["gnome-screenshot", "grim"]
    return ["gnome-screenshot", "grim"]


def _capture_via_gnome_screenshot(path: Path, show_cursor: bool) -> bool:
    cmd = ["gnome-screenshot", "-f", str(path)]
    if show_cursor:
        cmd.append("--include-pointer")
    return _run_capture(cmd, path, "gnome-screenshot")


def _capture_via_grim(path: Path, show_cursor: bool) -> bool:
    cmd = ["grim"]
    if show_cursor:
        cmd.append("-c")
    cmd.append(str(path))
    return _run_capture(cmd, path, "grim")


def _run_capture(cmd: list[str], path: Path, name: str) -> bool:
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=10)
    except FileNotFoundError:
        print(f"{name} not installed")
        return False
    except subprocess.TimeoutExpired:
        print(f"{name} timed out")
        return False
    if result.returncode != 0:
        print(f"{name} failed: {result.stderr.decode(errors='replace').strip()}")
        return False
    if not path.exists() or path.stat().st_size == 0:
        print(f"{name} produced no output")
        return False
    return True


_BACKENDS = {
    "gnome-screenshot": _capture_via_gnome_screenshot,
    "grim": _capture_via_grim,
}


def capture_fullscreen(show_cursor: bool = False) -> Path | None:
    """Take a full-screen screenshot silently.

    Returns the path to a temporary PNG, or None if every backend failed.
    """
    tmp = tempfile.NamedTemporaryFile(suffix=".png", prefix="waysnip_", delete=False)
    tmp.close()
    path = Path(tmp.name)

    for backend in _backend_order():
        if _BACKENDS[backend](path, show_cursor):
            return path

    path.unlink(missing_ok=True)
    return None
