"""Per-tool drawing property storage with persistence."""

from __future__ import annotations

import json
from typing import Any

from waysnip.constants import CONFIG_DIR

# Canonical per-tool defaults. Colors stored as HexArgb strings for easy JSON serialization.
TOOL_DEFAULTS: dict[str, dict[str, Any]] = {
    "rectangle": {
        "pen_color": "#ffff0000",
        "fill_color": "#00000000",
        "pen_width": 3,
        "item_opacity": 1.0,
    },
    "ellipse": {
        "pen_color": "#ffff0000",
        "fill_color": "#00000000",
        "pen_width": 3,
        "item_opacity": 1.0,
    },
    "arrow": {
        "pen_color": "#ffff0000",
        "fill_color": "#00000000",
        "pen_width": 3,
        "item_opacity": 1.0,
    },
    "line": {
        "pen_color": "#ffff0000",
        "fill_color": "#00000000",
        "pen_width": 3,
        "item_opacity": 1.0,
    },
    "freehand": {
        "pen_color": "#ffff0000",
        "fill_color": "#00000000",
        "pen_width": 3,
        "item_opacity": 1.0,
    },
    "highlight": {
        "pen_color": "#ffffff00",
        "fill_color": "#00000000",
        "pen_width": 20,
        "item_opacity": 0.4,
    },
    "text": {
        "pen_color": "#ffffffff",
        "fill_color": "#00000000",
        "pen_width": 3,
        "item_opacity": 1.0,
        "font_family": "Sans",
        "font_size": 16,
    },
    "numbered_marker": {
        "pen_color": "#ffff0000",
        "fill_color": "#ffffffff",
        "pen_width": 3,
        "item_opacity": 1.0,
    },
    "blur": {
        "block_size": 10,
    },
}


class ToolPropertyStore:
    """Manages per-tool drawing properties with persistence."""

    _STATE_FILE = CONFIG_DIR / "tool_state.json"

    def __init__(self) -> None:
        self._props: dict[str, dict[str, Any]] = {
            name: dict(defaults) for name, defaults in TOOL_DEFAULTS.items()
        }

    def get(self, tool_name: str) -> dict[str, Any]:
        """Return the property dict for a tool (or empty dict for tools without properties)."""
        return self._props.get(tool_name, {})

    def update(self, tool_name: str, changes: dict[str, Any]) -> None:
        """Merge changes into a tool's properties."""
        if tool_name in self._props:
            self._props[tool_name].update(changes)

    def reset_all(self) -> None:
        """Reset all tools to their code-defined defaults."""
        self._props = {
            name: dict(defaults) for name, defaults in TOOL_DEFAULTS.items()
        }

    def reset_tool(self, tool_name: str) -> None:
        """Reset a single tool to its defaults."""
        if tool_name in TOOL_DEFAULTS:
            self._props[tool_name] = dict(TOOL_DEFAULTS[tool_name])

    @classmethod
    def load(cls) -> ToolPropertyStore:
        """Load persisted state from disk, falling back to defaults."""
        store = cls()
        if cls._STATE_FILE.exists():
            try:
                with open(cls._STATE_FILE) as f:
                    data = json.load(f)
                for tool_name, saved_props in data.items():
                    if tool_name in store._props and isinstance(saved_props, dict):
                        store._props[tool_name].update(saved_props)
            except (json.JSONDecodeError, OSError):
                pass
        return store

    def save(self) -> None:
        """Persist current state to disk."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(self._STATE_FILE, "w") as f:
            json.dump(self._props, f, indent=2)
