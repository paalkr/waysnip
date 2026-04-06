"""Tests for waysnip.config — AppConfig loading, saving, round-trip."""

from __future__ import annotations

import tomllib


from waysnip.config import AppConfig
from waysnip.constants import (
    DEFAULT_FILL_COLOR,
    DEFAULT_FILENAME_PATTERN,
    DEFAULT_FONT_FAMILY,
    DEFAULT_FONT_SIZE,
    DEFAULT_MAGNIFIER_SIZE,
    DEFAULT_MAGNIFIER_ZOOM,
    DEFAULT_PEN_COLOR,
    DEFAULT_PEN_WIDTH,
    DEFAULT_SAVE_DIR,
)


class TestDefaults:
    def test_capture_defaults(self):
        cfg = AppConfig()
        assert cfg.capture.after_capture == "editor"
        assert cfg.capture.auto_copy_clipboard is True
        assert cfg.capture.show_cursor is False

    def test_save_defaults(self):
        cfg = AppConfig()
        assert cfg.save.directory == str(DEFAULT_SAVE_DIR)
        assert cfg.save.pattern == DEFAULT_FILENAME_PATTERN
        assert cfg.save.mode == "annotated"

    def test_editor_defaults(self):
        cfg = AppConfig()
        assert cfg.editor.default_pen_color == DEFAULT_PEN_COLOR
        assert cfg.editor.default_pen_width == DEFAULT_PEN_WIDTH
        assert cfg.editor.default_fill_color == DEFAULT_FILL_COLOR
        assert cfg.editor.default_font == DEFAULT_FONT_FAMILY
        assert cfg.editor.default_font_size == DEFAULT_FONT_SIZE
        assert cfg.editor.recent_colors == []

    def test_magnifier_defaults(self):
        cfg = AppConfig()
        assert cfg.magnifier.enabled is True
        assert cfg.magnifier.zoom == DEFAULT_MAGNIFIER_ZOOM
        assert cfg.magnifier.size == DEFAULT_MAGNIFIER_SIZE

    def test_tray_defaults(self):
        cfg = AppConfig()
        assert cfg.tray.enabled is True
        assert cfg.tray.left_click_action == "region"


class TestLoadNoFile:
    def test_load_missing_file_returns_defaults(self, tmp_config_dir):
        """load() with no config file on disk should return defaults."""
        cfg = AppConfig.load()
        default = AppConfig()
        assert cfg.capture.after_capture == default.capture.after_capture
        assert cfg.save.directory == default.save.directory
        assert cfg.editor.default_pen_color == default.editor.default_pen_color


class TestSaveToDisk:
    def test_save_creates_file(self, tmp_config_dir):
        cfg = AppConfig()
        cfg.save_to_disk()
        config_file = tmp_config_dir / "config.toml"
        assert config_file.exists()

    def test_save_creates_valid_toml(self, tmp_config_dir):
        cfg = AppConfig()
        cfg.save_to_disk()
        config_file = tmp_config_dir / "config.toml"
        with open(config_file, "rb") as f:
            data = tomllib.load(f)
        assert "capture" in data
        assert "save" in data
        assert "editor" in data


class TestRoundTrip:
    def test_save_then_load_preserves_values(self, tmp_config_dir):
        cfg = AppConfig()
        cfg.capture.after_capture = "clipboard+save"
        cfg.editor.default_pen_color = "#00ff00"
        cfg.editor.default_pen_width = 7
        cfg.magnifier.zoom = 10
        cfg.tray.left_click_action = "fullscreen"
        cfg.save_to_disk()

        loaded = AppConfig.load()
        assert loaded.capture.after_capture == "clipboard+save"
        assert loaded.editor.default_pen_color == "#00ff00"
        assert loaded.editor.default_pen_width == 7
        assert loaded.magnifier.zoom == 10
        assert loaded.tray.left_click_action == "fullscreen"

    def test_round_trip_recent_colors(self, tmp_config_dir):
        cfg = AppConfig()
        cfg.editor.recent_colors = ["#aabbcc", "#112233"]
        cfg.save_to_disk()

        loaded = AppConfig.load()
        assert loaded.editor.recent_colors == ["#aabbcc", "#112233"]


class TestPartialConfig:
    def test_missing_sections_get_defaults(self, tmp_config_dir):
        """A TOML file with only [capture] should leave other sections at defaults."""
        import tomli_w

        config_file = tmp_config_dir / "config.toml"
        partial = {"capture": {"after_capture": "save"}}
        with open(config_file, "wb") as f:
            tomli_w.dump(partial, f)

        loaded = AppConfig.load()
        assert loaded.capture.after_capture == "save"
        # Other sections should be defaults
        assert loaded.editor.default_pen_color == DEFAULT_PEN_COLOR
        assert loaded.magnifier.zoom == DEFAULT_MAGNIFIER_ZOOM

    def test_unknown_keys_are_ignored(self, tmp_config_dir):
        import tomli_w

        config_file = tmp_config_dir / "config.toml"
        data = {
            "capture": {"after_capture": "editor", "nonexistent_key": True},
            "unknown_section": {"foo": "bar"},
        }
        with open(config_file, "wb") as f:
            tomli_w.dump(data, f)

        loaded = AppConfig.load()
        assert loaded.capture.after_capture == "editor"
        # Should not crash, unknown keys silently ignored


class TestAddRecentColor:
    def test_adds_to_front(self):
        cfg = AppConfig()
        cfg.add_recent_color("#aabbcc")
        cfg.add_recent_color("#ddeeff")
        assert cfg.editor.recent_colors[0] == "#ddeeff"
        assert cfg.editor.recent_colors[1] == "#aabbcc"

    def test_max_eight_colors(self):
        cfg = AppConfig()
        for i in range(12):
            cfg.add_recent_color(f"#{i:06x}")
        assert len(cfg.editor.recent_colors) == 8

    def test_deduplicates(self):
        cfg = AppConfig()
        cfg.add_recent_color("#aabbcc")
        cfg.add_recent_color("#ddeeff")
        cfg.add_recent_color("#aabbcc")
        assert cfg.editor.recent_colors == ["#aabbcc", "#ddeeff"]

    def test_duplicate_moves_to_front(self):
        cfg = AppConfig()
        cfg.add_recent_color("#111111")
        cfg.add_recent_color("#222222")
        cfg.add_recent_color("#333333")
        cfg.add_recent_color("#111111")
        assert cfg.editor.recent_colors[0] == "#111111"
        assert len(cfg.editor.recent_colors) == 3


class TestGetSaveDirectory:
    def test_creates_directory(self, tmp_path):
        cfg = AppConfig()
        cfg.save.directory = str(tmp_path / "screenshots")
        result = cfg.get_save_directory()
        assert result.exists()
        assert result.is_dir()

    def test_expands_tilde(self, tmp_path, monkeypatch):
        cfg = AppConfig()
        cfg.save.directory = "~/test_waysnip_save"
        result = cfg.get_save_directory()
        assert "~" not in str(result)
        # Clean up
        if result.exists():
            result.rmdir()
