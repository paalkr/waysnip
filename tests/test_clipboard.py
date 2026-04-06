"""Tests for waysnip clipboard functionality.

These tests define the contract for clipboard.py. They will fail until
the capture agent delivers the implementation.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch, call

import pytest

try:
    from waysnip.capture.clipboard import ClipboardManager

    HAS_CLIPBOARD_MODULE = True
except ImportError:
    HAS_CLIPBOARD_MODULE = False

pytestmark = pytest.mark.skipif(
    not HAS_CLIPBOARD_MODULE, reason="waysnip.capture.clipboard not yet implemented"
)


class TestCopyImage:
    @patch("waysnip.capture.clipboard.subprocess.Popen")
    def test_calls_wl_copy(self, mock_popen):
        mgr = ClipboardManager()
        png_data = b"\x89PNG\r\n\x1a\nfake"
        mgr.copy_image(png_data)
        mock_popen.assert_called_once()
        args = mock_popen.call_args
        # wl-copy should be called with --type image/png
        cmd = args[0][0] if args[0] else args[1].get("args", [])
        assert "wl-copy" in cmd
        assert "image/png" in cmd or "--type" in cmd

    @patch("waysnip.capture.clipboard.subprocess.Popen")
    def test_kills_previous_process(self, mock_popen):
        mock_proc = MagicMock()
        mock_popen.return_value = mock_proc

        mgr = ClipboardManager()
        mgr.copy_image(b"first")
        mgr.copy_image(b"second")
        # First process should have been killed before starting second
        mock_proc.kill.assert_called()


class TestCopyImageFromPixmap:
    def test_converts_pixmap_to_png_bytes(self, qapp, sample_pixmap):
        mgr = ClipboardManager()
        with patch.object(mgr, "copy_image") as mock_copy:
            mgr.copy_image_from_pixmap(sample_pixmap)
            mock_copy.assert_called_once()
            data = mock_copy.call_args[0][0]
            # Should be PNG data
            assert data[:4] == b"\x89PNG"
