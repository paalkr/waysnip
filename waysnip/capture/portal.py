"""Full-screen capture backend.

Uses gnome-screenshot for silent, non-interactive capture on GNOME Wayland.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


def capture_fullscreen(show_cursor: bool = False) -> Path | None:
    """Take a full-screen screenshot silently.

    Returns the path to a temporary PNG, or None if capture failed.
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
        print("gnome-screenshot not found")
        return None
    except subprocess.TimeoutExpired:
        print("gnome-screenshot timed out")
        return None
