"""Freehand drawing tool and item."""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPainter, QPainterPath
from PyQt6.QtWidgets import (
    QGraphicsScene,
    QGraphicsSceneMouseEvent,
    QStyleOptionGraphicsItem,
    QWidget,
)

from waysnip.editor.tools.base import BaseTool, BaseAnnotationItem, register_item_type
from waysnip.constants import HANDLE_HALF


@register_item_type
class FreehandItem(BaseAnnotationItem):
    """A freehand drawn path."""

    item_type = "freehand"

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._path = QPainterPath()
        self._points: list[tuple[float, float]] = []

    def add_point(self, point: QPointF) -> None:
        """Add a point to the path."""
        self._points.append((point.x(), point.y()))
        if len(self._points) == 1:
            self._path.moveTo(point)
        else:
            self._path.lineTo(point)
        self.prepareGeometryChange()
        self.update()

    def _content_rect(self) -> QRectF:
        return self._path.boundingRect()

    def boundingRect(self) -> QRectF:
        margin = self._pen_width / 2 + HANDLE_HALF
        return self._path.boundingRect().adjusted(-margin, -margin, margin, margin)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget | None = None) -> None:
        painter.setPen(self.make_pen())
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(self._path)

    def serialize(self) -> dict[str, Any]:
        data = super().serialize()
        data["points"] = self._points
        return data

    @classmethod
    def _from_data(cls, data: dict[str, Any]) -> FreehandItem:
        item = cls()
        item._apply_base_data(data)
        points = data.get("points", [])
        for i, (x, y) in enumerate(points):
            p = QPointF(x, y)
            if i == 0:
                item._path.moveTo(p)
            else:
                item._path.lineTo(p)
        item._points = points
        return item


class FreehandTool(BaseTool):
    """Tool for freehand drawing."""

    name = "freehand"
    icon = "freehand"
    shortcut = "P"
    cursor_shape = Qt.CursorShape.CrossCursor

    def __init__(self) -> None:
        self._current_item: FreehandItem | None = None
        self._drawing: bool = False

    def mouse_press(self, scene: QGraphicsScene, event: QGraphicsSceneMouseEvent) -> None:
        scene.clearSelection()
        self._current_item = FreehandItem()
        pos = event.scenePos()
        self._current_item.setPos(pos)
        self._current_item.add_point(QPointF(0, 0))
        scene.addItem(self._current_item)
        self._drawing = True
        event.accept()

    def mouse_move(self, scene: QGraphicsScene, event: QGraphicsSceneMouseEvent) -> None:
        if not self._drawing or self._current_item is None:
            return
        local_pos = event.scenePos() - self._current_item.pos()
        self._current_item.add_point(local_pos)
        event.accept()

    def mouse_release(self, scene: QGraphicsScene, event: QGraphicsSceneMouseEvent) -> None:
        if not self._drawing or self._current_item is None:
            return
        self._drawing = False
        if len(self._current_item._points) < 2:
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
