"""Tests for waysnip.editor.tool_properties — ToolPropertyStore."""

from __future__ import annotations

import json

from waysnip.editor.tool_properties import TOOL_DEFAULTS, ToolPropertyStore


class TestToolDefaults:
    def test_has_all_drawing_tools(self):
        expected = {"rectangle", "ellipse", "arrow", "line", "freehand",
                    "highlight", "text", "numbered_marker", "blur"}
        assert set(TOOL_DEFAULTS.keys()) == expected

    def test_highlight_defaults_are_yellow_thick_transparent(self):
        h = TOOL_DEFAULTS["highlight"]
        assert h["pen_color"] == "#ffffff00"
        assert h["pen_width"] == 20
        assert h["item_opacity"] == 0.4

    def test_freehand_defaults_are_red_thin_opaque(self):
        f = TOOL_DEFAULTS["freehand"]
        assert f["pen_color"] == "#ffff0000"
        assert f["pen_width"] == 3
        assert f["item_opacity"] == 1.0

    def test_text_has_font_properties(self):
        t = TOOL_DEFAULTS["text"]
        assert "font_family" in t
        assert "font_size" in t

    def test_blur_has_only_block_size(self):
        b = TOOL_DEFAULTS["blur"]
        assert "block_size" in b
        assert "pen_color" not in b


class TestToolPropertyStore:
    def test_get_returns_defaults(self):
        store = ToolPropertyStore()
        props = store.get("highlight")
        assert props["pen_color"] == "#ffffff00"
        assert props["pen_width"] == 20

    def test_get_unknown_tool_returns_empty(self):
        store = ToolPropertyStore()
        assert store.get("nonexistent") == {}

    def test_update_merges_changes(self):
        store = ToolPropertyStore()
        store.update("highlight", {"pen_color": "#ff00ff00"})
        assert store.get("highlight")["pen_color"] == "#ff00ff00"
        # Other props unchanged
        assert store.get("highlight")["pen_width"] == 20

    def test_update_unknown_tool_is_noop(self):
        store = ToolPropertyStore()
        store.update("nonexistent", {"pen_color": "#ff00ff00"})
        assert store.get("nonexistent") == {}

    def test_reset_all_restores_defaults(self):
        store = ToolPropertyStore()
        store.update("highlight", {"pen_color": "#ff00ff00"})
        store.update("freehand", {"pen_width": 10})
        store.reset_all()
        assert store.get("highlight")["pen_color"] == "#ffffff00"
        assert store.get("freehand")["pen_width"] == 3

    def test_reset_tool_restores_single_tool(self):
        store = ToolPropertyStore()
        store.update("highlight", {"pen_color": "#ff00ff00"})
        store.update("freehand", {"pen_width": 10})
        store.reset_tool("highlight")
        assert store.get("highlight")["pen_color"] == "#ffffff00"
        # Other tools unchanged
        assert store.get("freehand")["pen_width"] == 10

    def test_instances_are_independent(self):
        """Modifying one store should not affect another."""
        store1 = ToolPropertyStore()
        store2 = ToolPropertyStore()
        store1.update("highlight", {"pen_color": "#ff00ff00"})
        assert store2.get("highlight")["pen_color"] == "#ffffff00"


class TestToolPropertyStorePersistence:
    def test_save_creates_file(self, tmp_config_dir):
        store = ToolPropertyStore()
        store._STATE_FILE = tmp_config_dir / "tool_state.json"
        store.save()
        assert (tmp_config_dir / "tool_state.json").exists()

    def test_save_creates_valid_json(self, tmp_config_dir):
        store = ToolPropertyStore()
        store._STATE_FILE = tmp_config_dir / "tool_state.json"
        store.save()
        with open(tmp_config_dir / "tool_state.json") as f:
            data = json.load(f)
        assert "highlight" in data
        assert "rectangle" in data

    def test_load_returns_defaults_when_no_file(self, tmp_config_dir, monkeypatch):
        state_file = tmp_config_dir / "tool_state.json"
        monkeypatch.setattr(ToolPropertyStore, "_STATE_FILE", state_file)
        store = ToolPropertyStore.load()
        assert store.get("highlight")["pen_color"] == "#ffffff00"

    def test_save_then_load_round_trip(self, tmp_config_dir, monkeypatch):
        state_file = tmp_config_dir / "tool_state.json"
        monkeypatch.setattr(ToolPropertyStore, "_STATE_FILE", state_file)

        store = ToolPropertyStore()
        store.update("highlight", {"pen_color": "#ff00ff00"})
        store.update("freehand", {"pen_width": 10})
        store.save()

        loaded = ToolPropertyStore.load()
        assert loaded.get("highlight")["pen_color"] == "#ff00ff00"
        assert loaded.get("freehand")["pen_width"] == 10
        # Unmodified tools should have defaults
        assert loaded.get("rectangle")["pen_color"] == "#ffff0000"

    def test_load_ignores_unknown_tools(self, tmp_config_dir, monkeypatch):
        state_file = tmp_config_dir / "tool_state.json"
        monkeypatch.setattr(ToolPropertyStore, "_STATE_FILE", state_file)
        with open(state_file, "w") as f:
            json.dump({"unknown_tool": {"pen_color": "#ff0000"}}, f)
        store = ToolPropertyStore.load()
        assert store.get("unknown_tool") == {}

    def test_load_handles_corrupt_json(self, tmp_config_dir, monkeypatch):
        state_file = tmp_config_dir / "tool_state.json"
        monkeypatch.setattr(ToolPropertyStore, "_STATE_FILE", state_file)
        with open(state_file, "w") as f:
            f.write("not valid json{{{")
        store = ToolPropertyStore.load()
        # Should fall back to defaults
        assert store.get("highlight")["pen_color"] == "#ffffff00"

    def test_load_merges_with_defaults(self, tmp_config_dir, monkeypatch):
        """Saved state with fewer keys should merge with defaults (forward compat)."""
        state_file = tmp_config_dir / "tool_state.json"
        monkeypatch.setattr(ToolPropertyStore, "_STATE_FILE", state_file)
        # Save only pen_color for highlight
        with open(state_file, "w") as f:
            json.dump({"highlight": {"pen_color": "#ff00ff00"}}, f)
        store = ToolPropertyStore.load()
        assert store.get("highlight")["pen_color"] == "#ff00ff00"
        # pen_width should still be the default
        assert store.get("highlight")["pen_width"] == 20
