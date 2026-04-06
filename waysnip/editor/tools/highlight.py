"""Highlight (semi-transparent marker) tool and item."""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPainter, QPen, QColor, QPainterPath
from PyQt6.QtWidgets import (
    QGraphicsScene,
    QGraphicsSceneMouseEvent,
    QStyleOptionGraphicsItem,
    QWidget,
)

from waysnip.editor.tools.base import BaseTool, BaseAnnotationItem, register_item_type
from waysnip.constants import HANDLE_HALF


@register_item_type
class HighlightItem(BaseAnnotationItem):
    """A wide semi-transparent highlight stroke."""

    item_type = "highlight"

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._path = QPainterPath()
        self._points: list[tuple[float, float]] = []
        # Defaults: yellow, 40% opacity, 20px width
        self._pen_color = QColor(255, 255, 0)
        self._pen_width = 20
        self._opacity = 0.4
        self.setOpacity(0.4)

    def add_point(self, point: QPointF) -> None:
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
        pen = QPen(self._pen_color, self._pen_width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(self._path)

    def serialize(self) -> dict[str, Any]:
        data = super().serialize()
        data["points"] = self._points
        return data

    @classmethod
    def _from_data(cls, data: dict[str, Any]) -> HighlightItem:
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


class HighlightTool(BaseTool):
    """Tool for drawing highlight strokes."""

    name = "highlight"
    icon = "highlight"
    shortcut = "H"
    cursor_shape = Qt.CursorShape.CrossCursor

    def __init__(self) -> None:
        self._current_item: HighlightItem | None = None
        self._drawing: bool = False

    def mouse_press(self, scene: QGraphicsScene, event: QGraphicsSceneMouseEvent) -> None:
        scene.clearSelection()
        self._current_item = HighlightItem()
        self._current_item.apply_drawing_properties(scene.drawing_properties)
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
