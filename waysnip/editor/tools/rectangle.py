"""Rectangle annotation tool and item."""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPainter
from PyQt6.QtWidgets import (
    QGraphicsScene,
    QGraphicsSceneMouseEvent,
    QStyleOptionGraphicsItem,
    QWidget,
)

from waysnip.editor.tools.base import BaseTool, BaseAnnotationItem, register_item_type
from waysnip.constants import HANDLE_HALF


@register_item_type
class RectangleItem(BaseAnnotationItem):
    """A rectangle annotation with optional rounded corners."""

    item_type = "rectangle"

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._rect = QRectF(0, 0, 100, 60)
        self._corner_radius: float = 0.0

    @property
    def corner_radius(self) -> float:
        return self._corner_radius

    @corner_radius.setter
    def corner_radius(self, value: float) -> None:
        self._corner_radius = max(0.0, value)
        self.update()

    def set_rect(self, rect: QRectF) -> None:
        self.prepareGeometryChange()
        self._rect = rect
        self._update_handles()
        self.update()

    def _content_rect(self) -> QRectF:
        return QRectF(self._rect)

    def boundingRect(self) -> QRectF:
        margin = self._pen_width / 2 + HANDLE_HALF
        return self._rect.adjusted(-margin, -margin, margin, margin)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget | None = None) -> None:
        painter.setPen(self.make_pen())
        painter.setBrush(self.make_brush())
        if self._corner_radius > 0:
            painter.drawRoundedRect(self._rect, self._corner_radius, self._corner_radius)
        else:
            painter.drawRect(self._rect)

    def serialize(self) -> dict[str, Any]:
        data = super().serialize()
        data.update({
            "width": self._rect.width(),
            "height": self._rect.height(),
            "rect_x": self._rect.x(),
            "rect_y": self._rect.y(),
            "corner_radius": self._corner_radius,
        })
        return data

    @classmethod
    def _from_data(cls, data: dict[str, Any]) -> RectangleItem:
        item = cls()
        item._apply_base_data(data)
        item._rect = QRectF(
            data.get("rect_x", 0),
            data.get("rect_y", 0),
            data.get("width", 100),
            data.get("height", 60),
        )
        item._corner_radius = data.get("corner_radius", 0.0)
        return item


class RectangleTool(BaseTool):
    """Tool for drawing rectangles."""

    name = "rectangle"
    icon = "rectangle"
    shortcut = "R"
    cursor_shape = Qt.CursorShape.CrossCursor

    def __init__(self) -> None:
        self._current_item: RectangleItem | None = None
        self._start_pos: QPointF = QPointF()

    def mouse_press(self, scene: QGraphicsScene, event: QGraphicsSceneMouseEvent) -> None:
        scene.clearSelection()
        self._start_pos = event.scenePos()
        self._current_item = RectangleItem()
        self._current_item.apply_drawing_properties(scene.drawing_properties)
        self._current_item.setPos(self._start_pos)
        self._current_item.set_rect(QRectF(0, 0, 0, 0))
        scene.addItem(self._current_item)
        event.accept()

    def mouse_move(self, scene: QGraphicsScene, event: QGraphicsSceneMouseEvent) -> None:
        if self._current_item is None:
            return
        pos = event.scenePos()
        rect = QRectF(QPointF(0, 0), pos - self._start_pos).normalized()
        # Shift for square
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            side = max(rect.width(), rect.height())
            rect.setWidth(side)
            rect.setHeight(side)
        self._current_item.set_rect(rect)
        event.accept()

    def mouse_release(self, scene: QGraphicsScene, event: QGraphicsSceneMouseEvent) -> None:
        if self._current_item is None:
            return
        # If too small, remove it
        if self._current_item._rect.width() < 3 and self._current_item._rect.height() < 3:
            scene.removeItem(self._current_item)
        else:
            from waysnip.editor.commands import AddItemCommand

            scene.removeItem(self._current_item)
            cmd = AddItemCommand(scene, self._current_item)
            if hasattr(scene, "undo_stack"):
                scene.undo_stack.push(cmd)
            else:
                scene.addItem(self._current_item)
        self._current_item = None
        event.accept()
