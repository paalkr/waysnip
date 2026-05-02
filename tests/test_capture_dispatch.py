"""Tests for the fullscreen-capture backend dispatch in waysnip.capture.portal."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from waysnip.capture import portal


class TestBackendOrder:
    @pytest.mark.parametrize(
        "xdg, expected_first",
        [
            ("GNOME", "gnome-screenshot"),
            ("ubuntu:GNOME", "gnome-screenshot"),
            ("pop:GNOME", "gnome-screenshot"),
            ("GNOME-Classic:GNOME", "gnome-screenshot"),
            ("Unity", "gnome-screenshot"),
            ("sway", "grim"),
            ("Hyprland", "grim"),
            ("wlroots", "grim"),
            ("Wayfire", "grim"),
            ("river", "grim"),
            ("KDE", "gnome-screenshot"),
            ("", "gnome-screenshot"),
        ],
    )
    def test_first_backend_for_env(self, monkeypatch, xdg, expected_first):
        monkeypatch.setenv("XDG_CURRENT_DESKTOP", xdg)
        order = portal._backend_order()
        assert order[0] == expected_first
        assert len(order) == 2
        assert set(order) == {"gnome-screenshot", "grim"}

    def test_no_xdg_var_falls_back_to_gnome_first(self, monkeypatch):
        monkeypatch.delenv("XDG_CURRENT_DESKTOP", raising=False)
        order = portal._backend_order()
        assert order[0] == "gnome-screenshot"


def _fake_run(written: dict[str, bool]):
    """Build a subprocess.run side-effect that simulates per-binary outcomes.

    written maps binary name -> bool (True if the run should succeed and write
    a non-empty file).
    """

    def runner(cmd, capture_output=True, timeout=10):
        binary = cmd[0]
        outcome = written.get(binary, False)
        # find the path argument
        if binary == "gnome-screenshot":
            path = Path(cmd[cmd.index("-f") + 1])
        elif binary == "grim":
            path = Path(cmd[-1])
        else:
            raise FileNotFoundError(binary)

        if outcome is FileNotFoundError:
            raise FileNotFoundError(binary)
        if outcome is subprocess.TimeoutExpired:
            raise subprocess.TimeoutExpired(cmd, timeout)
        if outcome:
            path.write_bytes(b"fake-png")
            return MagicMock(returncode=0, stderr=b"")
        return MagicMock(returncode=1, stderr=b"simulated failure")

    return runner


class TestCaptureFullscreenDispatch:
    def test_gnome_env_uses_gnome_screenshot(self, monkeypatch):
        monkeypatch.setenv("XDG_CURRENT_DESKTOP", "GNOME")
        monkeypatch.setattr(
            portal.subprocess, "run",
            _fake_run({"gnome-screenshot": True, "grim": False}),
        )
        result = portal.capture_fullscreen()
        assert result is not None and result.exists()
        result.unlink()

    def test_sway_env_uses_grim(self, monkeypatch):
        monkeypatch.setenv("XDG_CURRENT_DESKTOP", "sway")
        monkeypatch.setattr(
            portal.subprocess, "run",
            _fake_run({"gnome-screenshot": False, "grim": True}),
        )
        result = portal.capture_fullscreen()
        assert result is not None and result.exists()
        result.unlink()

    def test_gnome_env_falls_through_to_grim_on_failure(self, monkeypatch):
        monkeypatch.setenv("XDG_CURRENT_DESKTOP", "GNOME")
        monkeypatch.setattr(
            portal.subprocess, "run",
            _fake_run({"gnome-screenshot": False, "grim": True}),
        )
        result = portal.capture_fullscreen()
        assert result is not None and result.exists()
        result.unlink()

    def test_sway_env_falls_through_to_gnome_screenshot(self, monkeypatch):
        monkeypatch.setenv("XDG_CURRENT_DESKTOP", "sway")
        monkeypatch.setattr(
            portal.subprocess, "run",
            _fake_run({"gnome-screenshot": True, "grim": False}),
        )
        result = portal.capture_fullscreen()
        assert result is not None and result.exists()
        result.unlink()

    def test_both_backends_fail_returns_none(self, monkeypatch):
        monkeypatch.setenv("XDG_CURRENT_DESKTOP", "GNOME")
        monkeypatch.setattr(
            portal.subprocess, "run",
            _fake_run({"gnome-screenshot": False, "grim": False}),
        )
        result = portal.capture_fullscreen()
        assert result is None

    def test_gnome_screenshot_missing_falls_through(self, monkeypatch):
        monkeypatch.setenv("XDG_CURRENT_DESKTOP", "GNOME")
        monkeypatch.setattr(
            portal.subprocess, "run",
            _fake_run({"gnome-screenshot": FileNotFoundError, "grim": True}),
        )
        result = portal.capture_fullscreen()
        assert result is not None and result.exists()
        result.unlink()

    def test_grim_missing_falls_through(self, monkeypatch):
        monkeypatch.setenv("XDG_CURRENT_DESKTOP", "sway")
        monkeypatch.setattr(
            portal.subprocess, "run",
            _fake_run({"gnome-screenshot": True, "grim": FileNotFoundError}),
        )
        result = portal.capture_fullscreen()
        assert result is not None and result.exists()
        result.unlink()

    def test_timeout_falls_through(self, monkeypatch):
        monkeypatch.setenv("XDG_CURRENT_DESKTOP", "GNOME")
        monkeypatch.setattr(
            portal.subprocess, "run",
            _fake_run({"gnome-screenshot": subprocess.TimeoutExpired, "grim": True}),
        )
        result = portal.capture_fullscreen()
        assert result is not None and result.exists()
        result.unlink()

    def test_show_cursor_passed_to_gnome_screenshot(self, monkeypatch):
        monkeypatch.setenv("XDG_CURRENT_DESKTOP", "GNOME")
        seen_cmd: list[list[str]] = []

        def runner(cmd, capture_output=True, timeout=10):
            seen_cmd.append(list(cmd))
            Path(cmd[cmd.index("-f") + 1]).write_bytes(b"fake-png")
            return MagicMock(returncode=0, stderr=b"")

        monkeypatch.setattr(portal.subprocess, "run", runner)
        result = portal.capture_fullscreen(show_cursor=True)
        assert result is not None and result.exists()
        result.unlink()
        assert "--include-pointer" in seen_cmd[0]

    def test_show_cursor_passed_to_grim(self, monkeypatch):
        monkeypatch.setenv("XDG_CURRENT_DESKTOP", "sway")
        seen_cmd: list[list[str]] = []

        def runner(cmd, capture_output=True, timeout=10):
            seen_cmd.append(list(cmd))
            Path(cmd[-1]).write_bytes(b"fake-png")
            return MagicMock(returncode=0, stderr=b"")

        monkeypatch.setattr(portal.subprocess, "run", runner)
        result = portal.capture_fullscreen(show_cursor=True)
        assert result is not None and result.exists()
        result.unlink()
        assert "-c" in seen_cmd[0]

    def test_empty_output_file_treated_as_failure(self, monkeypatch):
        monkeypatch.setenv("XDG_CURRENT_DESKTOP", "GNOME")

        def runner(cmd, capture_output=True, timeout=10):
            # Don't write any bytes — leaves the tempfile at size 0.
            if cmd[0] == "grim":
                Path(cmd[-1]).write_bytes(b"fake-png")
                return MagicMock(returncode=0, stderr=b"")
            return MagicMock(returncode=0, stderr=b"")

        monkeypatch.setattr(portal.subprocess, "run", runner)
        result = portal.capture_fullscreen()
        # gnome-screenshot returned 0 but produced empty file -> fall through to grim
        assert result is not None and result.exists()
        result.unlink()
