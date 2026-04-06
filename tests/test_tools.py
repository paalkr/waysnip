"""Interface compliance tests for annotation tools and items.

These tests will fail until the editor agent delivers concrete tool
implementations. They define the contract each tool/item must satisfy.
"""

from __future__ import annotations

import pytest

from waysnip.constants import TOOL_SHORTCUTS

# Try to import the concrete tools module. It won't exist yet.
try:
    from waysnip.editor.tools import get_all_tools, get_all_item_types

    HAS_TOOLS = True
except ImportError:
    HAS_TOOLS = False

try:
    from waysnip.editor.tools.items import NumberedMarkerItem

    HAS_NUMBERED_MARKER = True
except ImportError:
    HAS_NUMBERED_MARKER = False

pytestmark = pytest.mark.skipif(
    not HAS_TOOLS, reason="concrete tool implementations not yet delivered"
)


class TestToolInterface:
    """Every tool must have name, icon, and shortcut."""

    def test_all_tools_have_name(self):
        for tool in get_all_tools():
            assert tool.name, f"{type(tool).__name__} is missing name"

    def test_all_tools_have_icon(self):
        for tool in get_all_tools():
            assert tool.icon, f"{type(tool).__name__} is missing icon"

    def test_all_tools_have_shortcut(self):
        for tool in get_all_tools():
            assert tool.shortcut, f"{type(tool).__name__} is missing shortcut"

    def test_tool_shortcuts_match_constants(self):
        tools = {t.name: t.shortcut for t in get_all_tools()}
        for name, shortcut in TOOL_SHORTCUTS.items():
            assert name in tools, f"Tool {name} not found in implementations"
            assert tools[name] == shortcut, (
                f"Tool {name}: expected shortcut {shortcut}, got {tools[name]}"
            )


class TestItemInterface:
    """Every item type must have item_type and round-trip serialize/deserialize."""

    def test_all_items_have_item_type(self, qapp):
        for item_cls in get_all_item_types():
            assert item_cls.item_type, f"{item_cls.__name__} missing item_type"

    def test_all_items_registered(self, qapp):
        from waysnip.editor.tools.base import _ITEM_REGISTRY

        for item_cls in get_all_item_types():
            assert item_cls.item_type in _ITEM_REGISTRY

    def test_serialize_deserialize_round_trip(self, qapp):
        from waysnip.editor.tools.base import BaseAnnotationItem

        for item_cls in get_all_item_types():
            item = item_cls()
            item.setPos(42.0, 84.0)
            data = item.serialize()
            restored = BaseAnnotationItem.deserialize(data)
            assert restored is not None, f"Failed to deserialize {item_cls.__name__}"
            assert type(restored) is item_cls
            assert restored.pos().x() == pytest.approx(42.0)
            assert restored.pos().y() == pytest.approx(84.0)


@pytest.mark.skipif(
    not HAS_NUMBERED_MARKER,
    reason="NumberedMarkerItem not yet implemented",
)
class TestNumberedMarkerItem:
    def test_auto_renumber(self, qapp):
        from PyQt6.QtWidgets import QGraphicsScene

        scene = QGraphicsScene()
        m1 = NumberedMarkerItem()
        m2 = NumberedMarkerItem()
        m3 = NumberedMarkerItem()
        scene.addItem(m1)
        scene.addItem(m2)
        scene.addItem(m3)
        # Markers should be numbered sequentially
        assert m1.number == 1
        assert m2.number == 2
        assert m3.number == 3

    def test_renumber_after_removal(self, qapp):
        from PyQt6.QtWidgets import QGraphicsScene

        scene = QGraphicsScene()
        m1 = NumberedMarkerItem()
        m2 = NumberedMarkerItem()
        m3 = NumberedMarkerItem()
        scene.addItem(m1)
        scene.addItem(m2)
        scene.addItem(m3)
        scene.removeItem(m2)
        # After removing #2, remaining markers should renumber
        # (exact behavior depends on implementation)
        markers = [
            i for i in scene.items() if isinstance(i, NumberedMarkerItem)
        ]
        numbers = sorted(m.number for m in markers)
        assert numbers == [1, 2]
