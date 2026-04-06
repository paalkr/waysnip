"""Ellipse annotation tool and item."""

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
class EllipseItem(BaseAnnotationItem):
    """An ellipse annotation."""

    item_type = "ellipse"

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._rect = QRectF(0, 0, 100, 60)

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
        painter.drawEllipse(self._rect)

    def serialize(self) -> dict[str, Any]:
        data = super().serialize()
        data.update({
            "width": self._rect.width(),
            "height": self._rect.height(),
            "rect_x": self._rect.x(),
            "rect_y": self._rect.y(),
        })
        return data

    @classmethod
    def _from_data(cls, data: dict[str, Any]) -> EllipseItem:
        item = cls()
        item._apply_base_data(data)
        item._rect = QRectF(
            data.get("rect_x", 0),
            data.get("rect_y", 0),
            data.get("width", 100),
            data.get("height", 60),
        )
        return item


class EllipseTool(BaseTool):
    """Tool for drawing ellipses."""

    name = "ellipse"
    icon = "ellipse"
    shortcut = "E"
    cursor_shape = Qt.CursorShape.CrossCursor

    def __init__(self) -> None:
        self._current_item: EllipseItem | None = None
        self._start_pos: QPointF = QPointF()

    def mouse_press(self, scene: QGraphicsScene, event: QGraphicsSceneMouseEvent) -> None:
        scene.clearSelection()
        self._start_pos = event.scenePos()
        self._current_item = EllipseItem()
        self._current_item.setPos(self._start_pos)
        self._current_item.set_rect(QRectF(0, 0, 0, 0))
        scene.addItem(self._current_item)
        event.accept()

    def mouse_move(self, scene: QGraphicsScene, event: QGraphicsSceneMouseEvent) -> None:
        if self._current_item is None:
            return
        pos = event.scenePos()
        rect = QRectF(QPointF(0, 0), pos - self._start_pos).normalized()
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            side = max(rect.width(), rect.height())
            rect.setWidth(side)
            rect.setHeight(side)
        self._current_item.set_rect(rect)
        event.accept()

    def mouse_release(self, scene: QGraphicsScene, event: QGraphicsSceneMouseEvent) -> None:
        if self._current_item is None:
            return
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
