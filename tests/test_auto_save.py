"""Tests for the auto-save behavior: fresh snips saved on capture, and
editor Ctrl+C persisting the snip."""

from __future__ import annotations

from pathlib import Path

import pytest
from PyQt6.QtGui import QColor, QPixmap

from waysnip.config import AppConfig


@pytest.fixture()
def config(tmp_path) -> AppConfig:
    cfg = AppConfig()
    cfg.save.directory = str(tmp_path / "shots")
    cfg.editor.copy_on_save = False  # keep clipboard out of these tests
    return cfg


@pytest.fixture()
def pixmap() -> QPixmap:
    pm = QPixmap(120, 80)
    pm.fill(QColor("steelblue"))
    return pm


def _png_count(cfg: AppConfig) -> int:
    return len(list(Path(cfg.save.directory).glob("*.png")))


class TestAutoSaveConfig:
    def test_defaults_true(self):
        assert AppConfig().capture.auto_save is True

    def test_round_trips_through_disk(self, tmp_path, monkeypatch):
        from waysnip import config as config_mod

        cfg_file = tmp_path / "config.toml"
        monkeypatch.setattr(config_mod, "CONFIG_FILE", cfg_file)
        monkeypatch.setattr(config_mod, "CONFIG_DIR", tmp_path)

        cfg = AppConfig()
        cfg.capture.auto_save = False
        cfg.save_to_disk()

        reloaded = AppConfig.load()
        assert reloaded.capture.auto_save is False


class TestEditorAutoSaveOnCopy:
    def _editor(self, config, pixmap, **kwargs):
        from waysnip.editor.editor_window import EditorWindow

        return EditorWindow(pixmap, config, **kwargs)

    def test_copy_persists_when_auto_save_on(self, qapp, config, pixmap):
        config.capture.auto_save = True
        win = self._editor(config, pixmap)
        assert _png_count(config) == 0

        emitted: list[str] = []
        win.image_saved.connect(emitted.append)
        win._copy_to_clipboard()

        assert _png_count(config) == 1
        assert len(emitted) == 1
        assert win._saved is True

    def test_copy_does_not_save_when_auto_save_off(self, qapp, config, pixmap):
        config.capture.auto_save = False
        win = self._editor(config, pixmap)

        win._copy_to_clipboard()

        assert _png_count(config) == 0
        assert win._saved is False

    def test_copy_overwrites_autosaved_file_not_duplicate(self, qapp, config, pixmap):
        # Simulate a fresh snip already auto-saved at capture time.
        from waysnip.save import save_screenshot

        first = save_screenshot(pixmap, [], pixmap, config)
        assert _png_count(config) == 1

        config.capture.auto_save = True
        win = self._editor(config, pixmap, autosaved_path=str(first))
        win._copy_to_clipboard()

        # Still one file — the existing one was overwritten, not duplicated.
        assert _png_count(config) == 1
        assert win._save_path == str(first)

    def test_autosaved_editor_keeps_close_prompt_alive(self, qapp, config, pixmap):
        # An auto-saved fresh snip must not be treated as "annotations saved".
        from waysnip.save import save_screenshot

        first = save_screenshot(pixmap, [], pixmap, config)
        win = self._editor(config, pixmap, autosaved_path=str(first))
        assert win._saved is False
        assert win._save_path == str(first)

    def test_save_overwrites_autosaved_path(self, qapp, config, pixmap):
        from waysnip.save import save_screenshot

        first = save_screenshot(pixmap, [], pixmap, config)
        win = self._editor(config, pixmap, autosaved_path=str(first))
        win._save()

        assert _png_count(config) == 1
        assert win._save_path == str(first)
        assert win._saved is True
