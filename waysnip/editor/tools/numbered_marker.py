"""Numbered marker annotation tool and item."""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QFont, QPen
from PyQt6.QtWidgets import (
    QGraphicsScene,
    QGraphicsSceneMouseEvent,
    QStyleOptionGraphicsItem,
    QWidget,
)

from waysnip.editor.tools.base import BaseTool, BaseAnnotationItem, register_item_type
from waysnip.constants import HANDLE_HALF


@register_item_type
class NumberedMarkerItem(BaseAnnotationItem):
    """A numbered circle marker."""

    item_type = "numbered_marker"

    # Class-level creation counter for ordering
    _creation_counter: int = 0

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._number: int = 1
        self._size: float = 28.0
        self._circle_color = QColor(255, 0, 0)
        self._text_color = QColor(255, 255, 255)
        self._pen_color = QColor(255, 0, 0)
        self._fill_color = QColor(255, 0, 0)

        NumberedMarkerItem._creation_counter += 1
        self._creation_order: int = NumberedMarkerItem._creation_counter

    @property
    def number(self) -> int:
        return self._number

    @number.setter
    def number(self, value: int) -> None:
        self._number = value
        self.update()

    @property
    def circle_color(self) -> QColor:
        return self._circle_color

    @circle_color.setter
    def circle_color(self, color: QColor) -> None:
        self._circle_color = color
        self.update()

    @property
    def text_color(self) -> QColor:
        return self._text_color

    @text_color.setter
    def text_color(self, color: QColor) -> None:
        self._text_color = color
        self.update()

    @property
    def size(self) -> float:
        return self._size

    @size.setter
    def size(self, value: float) -> None:
        self.prepareGeometryChange()
        self._size = max(16.0, value)
        self._update_handles()
        self.update()

    def _content_rect(self) -> QRectF:
        r = self._size / 2
        return QRectF(-r, -r, self._size, self._size)

    def boundingRect(self) -> QRectF:
        margin = HANDLE_HALF + 2
        cr = self._content_rect()
        return cr.adjusted(-margin, -margin, margin, margin)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget | None = None) -> None:
        r = self._size / 2
        rect = QRectF(-r, -r, self._size, self._size)

        # Circle
        painter.setBrush(self._circle_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(rect)

        # Number text
        painter.setPen(QPen(self._text_color))
        font = QFont("Sans", int(self._size * 0.5))
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(self._number))

    def serialize(self) -> dict[str, Any]:
        data = super().serialize()
        data.update({
            "number": self._number,
            "size": self._size,
            "circle_color": self._circle_color.name(QColor.NameFormat.HexArgb),
            "text_color": self._text_color.name(QColor.NameFormat.HexArgb),
            "creation_order": self._creation_order,
        })
        return data

    @classmethod
    def _from_data(cls, data: dict[str, Any]) -> NumberedMarkerItem:
        item = cls()
        item._apply_base_data(data)
        item._number = data.get("number", 1)
        item._size = data.get("size", 28.0)
        item._circle_color = QColor(data.get("circle_color", "#ffff0000"))
        item._text_color = QColor(data.get("text_color", "#ffffffff"))
        item._creation_order = data.get("creation_order", item._creation_order)
        return item

    @staticmethod
    def renumber_all(scene: QGraphicsScene) -> None:
        """Renumber all markers in the scene by creation order."""
        markers: list[NumberedMarkerItem] = []
        for item in scene.items():
            if isinstance(item, NumberedMarkerItem):
                markers.append(item)
        markers.sort(key=lambda m: m._creation_order)
        for i, marker in enumerate(markers, start=1):
            marker.number = i


class NumberedMarkerTool(BaseTool):
    """Tool for placing numbered circle markers."""

    name = "numbered_marker"
    icon = "numbered_marker"
    shortcut = "N"
    cursor_shape = Qt.CursorShape.CrossCursor

    def __init__(self) -> None:
        self._counter: int = 0

    def activate(self, scene: QGraphicsScene) -> None:
        """Reset counter based on existing markers in the scene."""
        existing = [
            item for item in scene.items() if isinstance(item, NumberedMarkerItem)
        ]
        self._counter = len(existing)

    def mouse_press(self, scene: QGraphicsScene, event: QGraphicsSceneMouseEvent) -> None:
        scene.clearSelection()
        self._counter += 1
        item = NumberedMarkerItem()
        item.number = self._counter
        item.setPos(event.scenePos())

        from waysnip.editor.commands import AddItemCommand

        cmd = AddItemCommand(scene, item)
        if hasattr(scene, "undo_stack"):
            scene.undo_stack.push(cmd)
        else:
            scene.addItem(item)
        event.accept()

    def mouse_move(self, scene: QGraphicsScene, event: QGraphicsSceneMouseEvent) -> None:
        event.accept()

    def mouse_release(self, scene: QGraphicsScene, event: QGraphicsSceneMouseEvent) -> None:
        event.accept()
