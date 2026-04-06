"""Configuration management — reads/writes TOML at ~/.config/waysnip/config.toml."""

from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

import tomli_w

from waysnip.constants import (
    CONFIG_DIR,
    CONFIG_FILE,
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


@dataclass
class CaptureConfig:
    after_capture: str = "editor"  # "editor", "clipboard", "save", "clipboard+save"
    auto_copy_clipboard: bool = True
    show_cursor: bool = False


@dataclass
class SaveConfig:
    directory: str = str(DEFAULT_SAVE_DIR)
    pattern: str = DEFAULT_FILENAME_PATTERN
    mode: str = "annotated"  # "annotated" or "editable"


@dataclass
class EditorConfig:
    default_pen_color: str = DEFAULT_PEN_COLOR
    default_pen_width: int = DEFAULT_PEN_WIDTH
    default_fill_color: str = DEFAULT_FILL_COLOR
    default_font: str = DEFAULT_FONT_FAMILY
    default_font_size: int = DEFAULT_FONT_SIZE
    recent_colors: list[str] = field(default_factory=list)


@dataclass
class MagnifierConfig:
    enabled: bool = True
    zoom: int = DEFAULT_MAGNIFIER_ZOOM
    size: int = DEFAULT_MAGNIFIER_SIZE


@dataclass
class TrayConfig:
    enabled: bool = True
    left_click_action: str = "region"


@dataclass
class AppConfig:
    capture: CaptureConfig = field(default_factory=CaptureConfig)
    save: SaveConfig = field(default_factory=SaveConfig)
    editor: EditorConfig = field(default_factory=EditorConfig)
    magnifier: MagnifierConfig = field(default_factory=MagnifierConfig)
    tray: TrayConfig = field(default_factory=TrayConfig)

    @classmethod
    def load(cls) -> AppConfig:
        """Load config from disk, falling back to defaults for missing keys."""
        config = cls()
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "rb") as f:
                data = tomllib.load(f)
            config._apply(data)
        return config

    def save_to_disk(self) -> None:
        """Write current config to disk."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = self._to_toml_dict()
        with open(CONFIG_FILE, "wb") as f:
            tomli_w.dump(data, f)

    def _apply(self, data: dict[str, Any]) -> None:
        """Apply a dict of values onto the config, ignoring unknown keys."""
        for section_name, section_data in data.items():
            section = getattr(self, section_name, None)
            if section is None or not isinstance(section_data, dict):
                continue
            for key, value in section_data.items():
                if hasattr(section, key):
                    setattr(section, key, value)

    def _to_toml_dict(self) -> dict[str, Any]:
        """Convert config to a nested dict suitable for TOML serialization."""
        result = {}
        for section_name in ("capture", "save", "editor", "magnifier", "tray"):
            section = getattr(self, section_name)
            result[section_name] = asdict(section)
        return result

    def get_save_directory(self) -> Path:
        """Resolve the save directory, expanding ~ and creating if needed."""
        path = Path(self.save.directory).expanduser()
        path.mkdir(parents=True, exist_ok=True)
        return path

    def add_recent_color(self, color_hex: str) -> None:
        """Add a color to the recent colors list (max 8, most recent first)."""
        colors = self.editor.recent_colors
        if color_hex in colors:
            colors.remove(color_hex)
        colors.insert(0, color_hex)
        self.editor.recent_colors = colors[:8]
