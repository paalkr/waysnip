"""Line annotation tool and item."""

from __future__ import annotations

import math
from typing import Any

from PyQt6.QtCore import Qt, QRectF, QPointF, QLineF
from PyQt6.QtGui import QPainter, QPen
from PyQt6.QtWidgets import (
    QGraphicsScene,
    QGraphicsSceneMouseEvent,
    QStyleOptionGraphicsItem,
    QWidget,
)

from waysnip.editor.tools.base import BaseTool, BaseAnnotationItem, register_item_type
from waysnip.constants import HANDLE_HALF

# Dash patterns: name -> (dash, space) multiplier on pen_width
_DASH_PATTERNS = {
    "solid": [],
    "dashed": [4.0, 2.0],
    "dotted": [1.0, 2.0],
}


@register_item_type
class LineItem(BaseAnnotationItem):
    """A straight line annotation."""

    item_type = "line"

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._start = QPointF(0, 0)
        self._end = QPointF(100, 0)
        self._dash_pattern: str = "solid"

    @property
    def dash_pattern(self) -> str:
        return self._dash_pattern

    @dash_pattern.setter
    def dash_pattern(self, value: str) -> None:
        if value in _DASH_PATTERNS:
            self._dash_pattern = value
            self.update()

    def set_line(self, start: QPointF, end: QPointF) -> None:
        self.prepareGeometryChange()
        self._start = start
        self._end = end
        self.update()

    def set_rect(self, rect: QRectF) -> None:
        self.prepareGeometryChange()
        self._start = rect.topLeft()
        self._end = rect.bottomRight()
        self._update_handles()
        self.update()

    def _content_rect(self) -> QRectF:
        return QRectF(self._start, self._end).normalized()

    def boundingRect(self) -> QRectF:
        margin = self._pen_width / 2 + HANDLE_HALF
        return self._content_rect().adjusted(-margin, -margin, margin, margin)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget | None = None) -> None:
        pen = self.make_pen()
        pattern = _DASH_PATTERNS.get(self._dash_pattern, [])
        if pattern:
            pen.setDashPattern(pattern)
        painter.setPen(pen)
        painter.drawLine(QLineF(self._start, self._end))

    def serialize(self) -> dict[str, Any]:
        data = super().serialize()
        data.update({
            "start_x": self._start.x(),
            "start_y": self._start.y(),
            "end_x": self._end.x(),
            "end_y": self._end.y(),
            "dash_pattern": self._dash_pattern,
        })
        return data

    @classmethod
    def _from_data(cls, data: dict[str, Any]) -> LineItem:
        item = cls()
        item._apply_base_data(data)
        item._start = QPointF(data.get("start_x", 0), data.get("start_y", 0))
        item._end = QPointF(data.get("end_x", 100), data.get("end_y", 0))
        item._dash_pattern = data.get("dash_pattern", "solid")
        return item


class LineTool(BaseTool):
    """Tool for drawing straight lines."""

    name = "line"
    icon = "line"
    shortcut = "L"
    cursor_shape = Qt.CursorShape.CrossCursor

    def __init__(self) -> None:
        self._current_item: LineItem | None = None
        self._start_pos: QPointF = QPointF()

    def mouse_press(self, scene: QGraphicsScene, event: QGraphicsSceneMouseEvent) -> None:
        scene.clearSelection()
        self._start_pos = event.scenePos()
        self._current_item = LineItem()
        self._current_item.setPos(self._start_pos)
        self._current_item.set_line(QPointF(0, 0), QPointF(0, 0))
        scene.addItem(self._current_item)
        event.accept()

    def mouse_move(self, scene: QGraphicsScene, event: QGraphicsSceneMouseEvent) -> None:
        if self._current_item is None:
            return
        end = event.scenePos() - self._start_pos
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            angle = math.atan2(end.y(), end.x())
            snapped = round(angle / (math.pi / 4)) * (math.pi / 4)
            length = math.sqrt(end.x() ** 2 + end.y() ** 2)
            end = QPointF(math.cos(snapped) * length, math.sin(snapped) * length)
        self._current_item.set_line(QPointF(0, 0), end)
        event.accept()

    def mouse_release(self, scene: QGraphicsScene, event: QGraphicsSceneMouseEvent) -> None:
        if self._current_item is None:
            return
        line = QLineF(self._current_item._start, self._current_item._end)
        if line.length() < 5:
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
