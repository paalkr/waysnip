"""Clipboard integration via wl-copy for Wayland."""

from __future__ import annotations

import subprocess
from pathlib import Path

from PyQt6.QtCore import QBuffer, QIODevice
from PyQt6.QtGui import QPixmap


class ClipboardManager:
    """Manage Wayland clipboard via ``wl-copy``.

    Wayland uses a lazy-clipboard model — the source process must stay alive
    for other apps to paste.  We keep the ``wl-copy`` subprocess around until
    a new copy replaces it (or the manager is garbage-collected).
    """

    _process: subprocess.Popen | None = None

    @classmethod
    def copy_image(cls, image_data: bytes) -> None:
        """Copy raw PNG bytes to the Wayland clipboard.

        Any previously running ``wl-copy`` process is killed first.
        """
        cls._kill_previous()
        cls._process = subprocess.Popen(
            ["wl-copy", "--type", "image/png"],
            stdin=subprocess.PIPE,
        )
        # Write all data and close stdin so wl-copy knows the payload is
        # complete, but do NOT wait — the process must stay alive.
        assert cls._process.stdin is not None
        cls._process.stdin.write(image_data)
        cls._process.stdin.close()

    @classmethod
    def copy_image_from_file(cls, path: Path) -> None:
        """Read a PNG file and copy it to the clipboard."""
        data = path.read_bytes()
        cls.copy_image(data)

    @classmethod
    def copy_image_from_pixmap(cls, pixmap: QPixmap) -> None:
        """Convert a QPixmap to PNG and copy it to the clipboard."""
        buf = QBuffer()
        buf.open(QIODevice.OpenModeFlag.WriteOnly)
        pixmap.save(buf, "PNG")
        cls.copy_image(bytes(buf.data()))

    @classmethod
    def _kill_previous(cls) -> None:
        """Terminate any existing wl-copy process."""
        if cls._process is not None:
            try:
                cls._process.kill()
                cls._process.wait(timeout=2)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                pass
            cls._process = None
