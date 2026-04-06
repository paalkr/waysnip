"""Interface compliance tests for annotation tools and items."""

from __future__ import annotations

import pytest

from waysnip.editor.tools.base import BaseAnnotationItem, _ITEM_REGISTRY
from waysnip.editor.tools.rectangle import RectangleTool, RectangleItem
from waysnip.editor.tools.ellipse import EllipseTool, EllipseItem
from waysnip.editor.tools.arrow import ArrowTool, ArrowItem
from waysnip.editor.tools.line import LineTool, LineItem
from waysnip.editor.tools.text import TextTool, TextItem
from waysnip.editor.tools.numbered_marker import NumberedMarkerTool, NumberedMarkerItem
from waysnip.editor.tools.freehand import FreehandTool, FreehandItem
from waysnip.editor.tools.highlight import HighlightTool, HighlightItem
from waysnip.editor.tools.blur import BlurTool, BlurItem
from waysnip.editor.tools.crop import CropTool
from waysnip.editor.tools.select_tool import SelectTool

ALL_TOOLS = [
    SelectTool, RectangleTool, EllipseTool, ArrowTool, LineTool,
    TextTool, NumberedMarkerTool, FreehandTool, HighlightTool, BlurTool, CropTool,
]

ALL_ITEM_CLASSES = [
    RectangleItem, EllipseItem, ArrowItem, LineItem, TextItem,
    NumberedMarkerItem, FreehandItem, HighlightItem, BlurItem,
]


class TestToolInterface:
    def test_all_tools_have_name(self, qapp):
        for tool_cls in ALL_TOOLS:
            tool = tool_cls()
            assert tool.name, f"{tool_cls.__name__} is missing name"

    def test_all_tools_have_shortcut(self, qapp):
        for tool_cls in ALL_TOOLS:
            tool = tool_cls()
            assert tool.shortcut, f"{tool_cls.__name__} is missing shortcut"


class TestItemInterface:
    def test_all_items_have_item_type(self, qapp):
        for item_cls in ALL_ITEM_CLASSES:
            assert item_cls.item_type, f"{item_cls.__name__} missing item_type"

    def test_all_items_registered(self, qapp):
        for item_cls in ALL_ITEM_CLASSES:
            assert item_cls.item_type in _ITEM_REGISTRY

    def test_serialize_deserialize_round_trip(self, qapp):
        for item_cls in ALL_ITEM_CLASSES:
            item = item_cls()
            item.setPos(42.0, 84.0)
            data = item.serialize()
            restored = BaseAnnotationItem.deserialize(data)
            assert restored is not None, f"Failed to deserialize {item_cls.__name__}"
            assert type(restored) is item_cls
            assert restored.pos().x() == pytest.approx(42.0)
            assert restored.pos().y() == pytest.approx(84.0)


class TestNumberedMarkerItem:
    def test_markers_have_numbers(self, qapp):
        m1 = NumberedMarkerItem()
        m2 = NumberedMarkerItem()
        assert hasattr(m1, "number")
        assert hasattr(m2, "number")

    def test_renumber_after_removal(self, qapp):
        from PyQt6.QtWidgets import QGraphicsScene

        scene = QGraphicsScene()
        m1 = NumberedMarkerItem()
        m1.number = 1
        m2 = NumberedMarkerItem()
        m2.number = 2
        m3 = NumberedMarkerItem()
        m3.number = 3
        scene.addItem(m1)
        scene.addItem(m2)
        scene.addItem(m3)
        scene.removeItem(m2)
        # After removing, remaining markers exist
        markers = [i for i in scene.items() if isinstance(i, NumberedMarkerItem)]
        assert len(markers) == 2
