"""Tests for waysnip.constants — verify all expected constants exist and have correct types."""

from __future__ import annotations

from pathlib import Path

import waysnip.constants as C


class TestConstantsExist:
    def test_app_identity(self):
        assert C.APP_NAME == "waysnip"
        assert isinstance(C.APP_VERSION, str)
        assert C.APP_DISPLAY_NAME == "WaySnip"

    def test_paths_are_path_objects(self):
        assert isinstance(C.CONFIG_DIR, Path)
        assert isinstance(C.CONFIG_FILE, Path)
        assert isinstance(C.DEFAULT_SAVE_DIR, Path)

    def test_config_file_under_config_dir(self):
        assert C.CONFIG_FILE.parent == C.CONFIG_DIR

    def test_ipc_socket_template(self):
        assert isinstance(C.SOCKET_NAME_TEMPLATE, str)
        assert "{uid}" in C.SOCKET_NAME_TEMPLATE

    def test_filename_pattern(self):
        assert isinstance(C.DEFAULT_FILENAME_PATTERN, str)
        assert ".png" in C.DEFAULT_FILENAME_PATTERN

    def test_font_defaults(self):
        assert isinstance(C.DEFAULT_FONT_FAMILY, str)
        assert isinstance(C.DEFAULT_FONT_SIZE, int)

    def test_magnifier_defaults(self):
        assert isinstance(C.DEFAULT_MAGNIFIER_ZOOM, int)
        assert isinstance(C.DEFAULT_MAGNIFIER_SIZE, int)

    def test_handle_constants(self):
        assert C.HANDLE_SIZE == 8
        assert C.HANDLE_HALF == C.HANDLE_SIZE / 2

    def test_png_metadata_keys(self):
        assert isinstance(C.META_KEY_ANNOTATIONS, str)
        assert isinstance(C.META_KEY_ORIGINAL, str)


class TestToolShortcuts:
    EXPECTED_TOOLS = [
        "select", "rectangle", "ellipse", "arrow", "line",
        "text", "numbered_marker", "freehand", "highlight", "blur", "crop",
    ]

    def test_has_all_11_tools(self):
        assert len(C.TOOL_SHORTCUTS) == 11

    def test_all_expected_tools_present(self):
        for tool in self.EXPECTED_TOOLS:
            assert tool in C.TOOL_SHORTCUTS, f"Missing tool: {tool}"

    def test_shortcuts_are_single_uppercase_letters(self):
        for tool, shortcut in C.TOOL_SHORTCUTS.items():
            assert len(shortcut) == 1, f"{tool} shortcut should be single char"
            assert shortcut.isupper(), f"{tool} shortcut should be uppercase"

    def test_shortcuts_are_unique(self):
        values = list(C.TOOL_SHORTCUTS.values())
        assert len(values) == len(set(values)), "Duplicate shortcut keys found"
