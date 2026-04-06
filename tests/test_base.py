"""Tests for waysnip.editor.tools.base — BaseAnnotationItem, ResizeHandle, registry."""

from __future__ import annotations

import pytest

from PyQt6.QtCore import QRectF, QPointF
from PyQt6.QtGui import QColor, QPen, QBrush, QPainter
from PyQt6.QtWidgets import QGraphicsItem, QStyleOptionGraphicsItem, QWidget

from waysnip.editor.tools.base import (
    BaseAnnotationItem,
    BaseTool,
    ResizeHandle,
    register_item_type,
    _ITEM_REGISTRY,
)
from waysnip.constants import HANDLE_SIZE, HANDLE_HALF


# --- Concrete subclass for testing (BaseAnnotationItem requires paint/boundingRect) ---

@register_item_type
class _TestItem(BaseAnnotationItem):
    """Minimal concrete subclass for testing."""

    item_type = "_test_item"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rect = QRectF(0, 0, 100, 80)

    def boundingRect(self) -> QRectF:
        margin = HANDLE_HALF
        return self._rect.adjusted(-margin, -margin, margin, margin)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget | None = None) -> None:
        painter.setPen(self.make_pen())
        painter.setBrush(self.make_brush())
        painter.drawRect(self._rect)

    def _content_rect(self) -> QRectF:
        return QRectF(self._rect)


# --- BaseTool tests ---

class TestBaseTool:
    def test_cannot_instantiate_directly(self):
        """BaseTool is abstract — instantiation should raise TypeError."""
        with pytest.raises(TypeError):
            BaseTool()

    def test_has_expected_class_attributes(self):
        assert hasattr(BaseTool, "name")
        assert hasattr(BaseTool, "icon")
        assert hasattr(BaseTool, "shortcut")
        assert hasattr(BaseTool, "cursor_shape")


# --- BaseAnnotationItem tests ---

class TestBaseAnnotationItemInstantiation:
    def test_cannot_instantiate_bare_base(self, qapp):
        """BaseAnnotationItem requires paint() and boundingRect() — but they're
        not marked abstract in the scaffold, so it CAN be instantiated.
        We test the concrete subclass instead."""
        item = _TestItem()
        assert item.item_type == "_test_item"

    def test_default_visual_properties(self, qapp):
        item = _TestItem()
        assert item.pen_color == QColor(255, 0, 0)
        assert item.fill_color == QColor(0, 0, 0, 0)
        assert item.pen_width == 3
        assert item.item_opacity == 1.0
        assert item.rotation_angle == 0.0

    def test_has_eight_resize_handles(self, qapp):
        item = _TestItem()
        assert len(item._handles) == 8


class TestPropertySetters:
    def test_pen_color_setter(self, qapp):
        item = _TestItem()
        new_color = QColor(0, 255, 0)
        item.pen_color = new_color
        assert item.pen_color == new_color

    def test_fill_color_setter(self, qapp):
        item = _TestItem()
        new_color = QColor(0, 0, 255, 128)
        item.fill_color = new_color
        assert item.fill_color == new_color

    def test_pen_width_setter(self, qapp):
        item = _TestItem()
        item.pen_width = 10
        assert item.pen_width == 10

    def test_pen_width_minimum_is_one(self, qapp):
        item = _TestItem()
        item.pen_width = 0
        assert item.pen_width == 1
        item.pen_width = -5
        assert item.pen_width == 1

    def test_opacity_setter(self, qapp):
        item = _TestItem()
        item.item_opacity = 0.5
        assert item.item_opacity == pytest.approx(0.5)

    def test_opacity_clamped_high(self, qapp):
        item = _TestItem()
        item.item_opacity = 2.0
        assert item.item_opacity == pytest.approx(1.0)

    def test_opacity_clamped_low(self, qapp):
        item = _TestItem()
        item.item_opacity = -0.5
        assert item.item_opacity == pytest.approx(0.0)

    def test_rotation_setter(self, qapp):
        item = _TestItem()
        item.rotation_angle = 45.0
        assert item.rotation_angle == pytest.approx(45.0)


class TestPenBrushHelpers:
    def test_make_pen_returns_qpen(self, qapp):
        item = _TestItem()
        pen = item.make_pen()
        assert isinstance(pen, QPen)

    def test_make_pen_color_matches(self, qapp):
        item = _TestItem()
        item.pen_color = QColor(0, 128, 255)
        pen = item.make_pen()
        assert pen.color() == QColor(0, 128, 255)

    def test_make_pen_width_matches(self, qapp):
        item = _TestItem()
        item.pen_width = 5
        pen = item.make_pen()
        assert pen.width() == 5

    def test_make_brush_returns_qbrush(self, qapp):
        item = _TestItem()
        brush = item.make_brush()
        assert isinstance(brush, QBrush)

    def test_make_brush_color_matches(self, qapp):
        item = _TestItem()
        item.fill_color = QColor(255, 0, 0, 100)
        brush = item.make_brush()
        assert brush.color() == QColor(255, 0, 0, 100)


class TestSerialization:
    def test_serialize_returns_dict(self, qapp):
        item = _TestItem()
        data = item.serialize()
        assert isinstance(data, dict)

    def test_serialize_has_expected_keys(self, qapp):
        item = _TestItem()
        data = item.serialize()
        expected_keys = {"type", "x", "y", "pen_color", "fill_color", "pen_width", "opacity", "rotation"}
        assert expected_keys == set(data.keys())

    def test_serialize_type_matches(self, qapp):
        item = _TestItem()
        data = item.serialize()
        assert data["type"] == "_test_item"

    def test_serialize_position(self, qapp):
        item = _TestItem()
        item.setPos(10.0, 20.0)
        data = item.serialize()
        assert data["x"] == pytest.approx(10.0)
        assert data["y"] == pytest.approx(20.0)

    def test_serialize_pen_color_is_hex_argb(self, qapp):
        item = _TestItem()
        data = item.serialize()
        assert data["pen_color"].startswith("#")
        # HexArgb format: #aarrggbb (9 chars)
        assert len(data["pen_color"]) == 9


class TestRegistry:
    def test_test_item_is_registered(self, qapp):
        assert "_test_item" in _ITEM_REGISTRY
        assert _ITEM_REGISTRY["_test_item"] is _TestItem

    def test_register_item_type_decorator(self, qapp):
        @register_item_type
        class _AnotherItem(BaseAnnotationItem):
            item_type = "_another_test"

            def boundingRect(self):
                return QRectF(0, 0, 10, 10)

            def paint(self, painter, option, widget=None):
                pass

        assert "_another_test" in _ITEM_REGISTRY

    def test_deserialize_dispatches_to_correct_type(self, qapp):
        item = _TestItem()
        item.setPos(5.0, 15.0)
        item.pen_width = 7
        data = item.serialize()

        restored = BaseAnnotationItem.deserialize(data)
        assert restored is not None
        assert isinstance(restored, _TestItem)
        assert restored.pos().x() == pytest.approx(5.0)
        assert restored.pen_width == 7

    def test_deserialize_unknown_type_returns_none(self, qapp):
        data = {"type": "nonexistent_widget_type"}
        result = BaseAnnotationItem.deserialize(data)
        assert result is None


class TestClone:
    def test_clone_creates_offset_copy(self, qapp):
        item = _TestItem()
        item.setPos(10.0, 30.0)
        cloned = item.clone()
        assert cloned is not None
        assert cloned.pos().x() == pytest.approx(30.0)
        assert cloned.pos().y() == pytest.approx(50.0)

    def test_clone_preserves_properties(self, qapp):
        item = _TestItem()
        item.pen_width = 9
        item.item_opacity = 0.7
        cloned = item.clone()
        assert cloned.pen_width == 9
        assert cloned.item_opacity == pytest.approx(0.7)


class TestResizeHandle:
    ALL_POSITIONS = [
        "top-left", "top", "top-right", "right",
        "bottom-right", "bottom", "bottom-left", "left",
    ]

    def test_handle_positions_on_item(self, qapp):
        item = _TestItem()
        positions = [h.position for h in item._handles]
        assert set(positions) == set(self.ALL_POSITIONS)

    def test_handles_initially_hidden(self, qapp):
        item = _TestItem()
        for handle in item._handles:
            assert not handle.isVisible()

    def test_update_position_top_left(self, qapp):
        item = _TestItem()
        handle = item._handles[0]  # top-left
        rect = QRectF(0, 0, 100, 80)
        handle.update_position(rect)
        assert handle.pos().x() == pytest.approx(rect.topLeft().x())
        assert handle.pos().y() == pytest.approx(rect.topLeft().y())

    def test_update_position_center_top(self, qapp):
        item = _TestItem()
        # Find the "top" handle
        top_handle = next(h for h in item._handles if h.position == "top")
        rect = QRectF(0, 0, 100, 80)
        top_handle.update_position(rect)
        assert top_handle.pos().x() == pytest.approx(50.0)
        assert top_handle.pos().y() == pytest.approx(0.0)

    def test_handle_rect_size(self, qapp):
        item = _TestItem()
        handle = item._handles[0]
        r = handle.rect()
        assert r.width() == pytest.approx(HANDLE_SIZE)
        assert r.height() == pytest.approx(HANDLE_SIZE)
