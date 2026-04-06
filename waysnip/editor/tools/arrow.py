"""Arrow annotation tool and item."""

from __future__ import annotations

import math
from typing import Any

from PyQt6.QtCore import Qt, QRectF, QPointF, QLineF
from PyQt6.QtGui import QPainter, QPolygonF
from PyQt6.QtWidgets import (
    QGraphicsScene,
    QGraphicsSceneMouseEvent,
    QStyleOptionGraphicsItem,
    QWidget,
)

from waysnip.editor.tools.base import BaseTool, BaseAnnotationItem, register_item_type
from waysnip.constants import HANDLE_HALF


@register_item_type
class ArrowItem(BaseAnnotationItem):
    """A line with an arrowhead at the end."""

    item_type = "arrow"

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._start = QPointF(0, 0)
        self._end = QPointF(100, 0)
        self._head_size: float = 15.0

    @property
    def head_size(self) -> float:
        return self._head_size

    @head_size.setter
    def head_size(self, value: float) -> None:
        self._head_size = max(5.0, value)
        self.update()

    def set_line(self, start: QPointF, end: QPointF) -> None:
        self.prepareGeometryChange()
        self._start = start
        self._end = end
        self.update()

    def set_rect(self, rect: QRectF) -> None:
        """Resize by fitting line into the rect."""
        self.prepareGeometryChange()
        self._start = rect.topLeft()
        self._end = rect.bottomRight()
        self._update_handles()
        self.update()

    def _content_rect(self) -> QRectF:
        return QRectF(self._start, self._end).normalized()

    def boundingRect(self) -> QRectF:
        margin = self._pen_width / 2 + self._head_size + HANDLE_HALF
        return self._content_rect().adjusted(-margin, -margin, margin, margin)

    def _arrowhead_polygon(self) -> QPolygonF:
        line = QLineF(self._start, self._end)
        if line.length() < 1:
            return QPolygonF()

        angle = math.atan2(-line.dy(), line.dx())
        p1 = self._end + QPointF(
            math.cos(angle + math.pi + math.pi / 6) * self._head_size,
            -math.sin(angle + math.pi + math.pi / 6) * self._head_size,
        )
        p2 = self._end + QPointF(
            math.cos(angle + math.pi - math.pi / 6) * self._head_size,
            -math.sin(angle + math.pi - math.pi / 6) * self._head_size,
        )
        return QPolygonF([self._end, p1, p2])

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget | None = None) -> None:
        pen = self.make_pen()
        painter.setPen(pen)
        painter.drawLine(QLineF(self._start, self._end))

        # Filled arrowhead
        polygon = self._arrowhead_polygon()
        if not polygon.isEmpty():
            painter.setBrush(self._pen_color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPolygon(polygon)

    def serialize(self) -> dict[str, Any]:
        data = super().serialize()
        data.update({
            "start_x": self._start.x(),
            "start_y": self._start.y(),
            "end_x": self._end.x(),
            "end_y": self._end.y(),
            "head_size": self._head_size,
        })
        return data

    @classmethod
    def _from_data(cls, data: dict[str, Any]) -> ArrowItem:
        item = cls()
        item._apply_base_data(data)
        item._start = QPointF(data.get("start_x", 0), data.get("start_y", 0))
        item._end = QPointF(data.get("end_x", 100), data.get("end_y", 0))
        item._head_size = data.get("head_size", 15.0)
        return item


class ArrowTool(BaseTool):
    """Tool for drawing arrows."""

    name = "arrow"
    icon = "arrow"
    shortcut = "A"
    cursor_shape = Qt.CursorShape.CrossCursor

    def __init__(self) -> None:
        self._current_item: ArrowItem | None = None
        self._start_pos: QPointF = QPointF()

    def mouse_press(self, scene: QGraphicsScene, event: QGraphicsSceneMouseEvent) -> None:
        scene.clearSelection()
        self._start_pos = event.scenePos()
        self._current_item = ArrowItem()
        self._current_item.setPos(self._start_pos)
        self._current_item.set_line(QPointF(0, 0), QPointF(0, 0))
        scene.addItem(self._current_item)
        event.accept()

    def mouse_move(self, scene: QGraphicsScene, event: QGraphicsSceneMouseEvent) -> None:
        if self._current_item is None:
            return
        end = event.scenePos() - self._start_pos
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            # Snap to 45-degree angles
            end = self._snap_angle(end)
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

    @staticmethod
    def _snap_angle(point: QPointF) -> QPointF:
        """Snap a point to the nearest 45-degree angle from origin."""
        angle = math.atan2(point.y(), point.x())
        snapped = round(angle / (math.pi / 4)) * (math.pi / 4)
        length = math.sqrt(point.x() ** 2 + point.y() ** 2)
        return QPointF(math.cos(snapped) * length, math.sin(snapped) * length)
