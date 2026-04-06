"""Tests for waysnip clipboard functionality."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from waysnip.capture.clipboard import ClipboardManager


class TestCopyImage:
    @patch("waysnip.capture.clipboard.subprocess.Popen")
    def test_calls_wl_copy(self, mock_popen):
        mock_proc = MagicMock()
        mock_proc.stdin = MagicMock()
        mock_popen.return_value = mock_proc

        ClipboardManager._process = None
        ClipboardManager.copy_image(b"\x89PNG\r\n\x1a\nfake")
        mock_popen.assert_called_once()
        cmd = mock_popen.call_args[0][0]
        assert "wl-copy" in cmd
        assert "image/png" in " ".join(cmd)

    @patch("waysnip.capture.clipboard.subprocess.Popen")
    def test_kills_previous_process(self, mock_popen):
        mock_proc = MagicMock()
        mock_proc.stdin = MagicMock()
        mock_popen.return_value = mock_proc

        ClipboardManager._process = None
        ClipboardManager.copy_image(b"first")
        ClipboardManager.copy_image(b"second")
        mock_proc.kill.assert_called()


class TestCopyImageFromPixmap:
    @patch("waysnip.capture.clipboard.subprocess.Popen")
    def test_converts_pixmap_to_png_bytes(self, mock_popen, qapp, sample_pixmap):
        mock_proc = MagicMock()
        mock_proc.stdin = MagicMock()
        mock_popen.return_value = mock_proc

        ClipboardManager._process = None
        ClipboardManager.copy_image_from_pixmap(sample_pixmap)
        mock_popen.assert_called_once()
        # Verify PNG data was written to stdin
        written = mock_proc.stdin.write.call_args[0][0]
        assert written[:4] == b"\x89PNG"
