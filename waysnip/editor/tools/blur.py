"""Blur (pixelation) tool and item."""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPainter, QPixmap, QColor
from PyQt6.QtWidgets import (
    QGraphicsScene,
    QGraphicsSceneMouseEvent,
    QStyleOptionGraphicsItem,
    QWidget,
)

from waysnip.editor.tools.base import BaseTool, BaseAnnotationItem, register_item_type
from waysnip.constants import HANDLE_HALF


@register_item_type
class BlurItem(BaseAnnotationItem):
    """A rectangular region that pixelates the underlying scene content."""

    item_type = "blur"

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._rect = QRectF(0, 0, 100, 60)
        self._block_size: int = 10
        self._cached_pixmap: QPixmap | None = None
        self._cache_rect: QRectF | None = None
        # No pen/fill visible for blur
        self._pen_width = 0

    @property
    def block_size(self) -> int:
        return self._block_size

    @block_size.setter
    def block_size(self, value: int) -> None:
        self._block_size = max(2, value)
        self._invalidate_cache()
        self.update()

    def set_rect(self, rect: QRectF) -> None:
        self.prepareGeometryChange()
        self._rect = rect
        self._invalidate_cache()
        self._update_handles()
        self.update()

    def _content_rect(self) -> QRectF:
        return QRectF(self._rect)

    def boundingRect(self) -> QRectF:
        margin = HANDLE_HALF
        return self._rect.adjusted(-margin, -margin, margin, margin)

    def _invalidate_cache(self) -> None:
        self._cached_pixmap = None
        self._cache_rect = None

    def _render_pixelated(self, painter: QPainter) -> None:
        """Grab the scene content under this item, pixelate it, and draw it."""
        scene = self.scene()
        if scene is None:
            return

        # Map rect to scene coordinates
        scene_rect = self.mapRectToScene(self._rect)

        # Check cache
        if (
            self._cached_pixmap is not None
            and self._cache_rect is not None
            and self._cache_rect == scene_rect
        ):
            painter.drawPixmap(self._rect.toRect(), self._cached_pixmap)
            return

        w = max(1, int(scene_rect.width()))
        h = max(1, int(scene_rect.height()))
        if w < 1 or h < 1:
            return

        # Temporarily hide this item so we grab the background
        self.setVisible(False)

        source = QPixmap(w, h)
        source.fill(QColor(0, 0, 0, 0))
        p = QPainter(source)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        scene.render(p, source=scene_rect)
        p.end()

        self.setVisible(True)

        # Pixelate: scale down then back up
        bs = self._block_size
        small_w = max(1, w // bs)
        small_h = max(1, h // bs)
        small = source.scaled(small_w, small_h, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.FastTransformation)
        pixelated = small.scaled(w, h, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.FastTransformation)

        self._cached_pixmap = pixelated
        self._cache_rect = QRectF(scene_rect)

        painter.drawPixmap(self._rect.toRect(), pixelated)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget | None = None) -> None:
        self._render_pixelated(painter)

        # Draw a subtle border when selected
        if self.isSelected():
            pen = painter.pen()
            from PyQt6.QtGui import QPen
            painter.setPen(QPen(QColor(0, 120, 215), 1, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(self._rect)

    def serialize(self) -> dict[str, Any]:
        data = super().serialize()
        data.update({
            "width": self._rect.width(),
            "height": self._rect.height(),
            "rect_x": self._rect.x(),
            "rect_y": self._rect.y(),
            "block_size": self._block_size,
        })
        return data

    @classmethod
    def _from_data(cls, data: dict[str, Any]) -> BlurItem:
        item = cls()
        item._apply_base_data(data)
        item._rect = QRectF(
            data.get("rect_x", 0),
            data.get("rect_y", 0),
            data.get("width", 100),
            data.get("height", 60),
        )
        item._block_size = data.get("block_size", 10)
        return item

    def itemChange(self, change, value):
        """Invalidate cache on position change."""
        if change == self.GraphicsItemChange.ItemPositionHasChanged:
            self._invalidate_cache()
        return super().itemChange(change, value)


class BlurTool(BaseTool):
    """Tool for drawing blur/pixelation regions."""

    name = "blur"
    icon = "blur"
    shortcut = "B"
    cursor_shape = Qt.CursorShape.CrossCursor

    def __init__(self) -> None:
        self._current_item: BlurItem | None = None
        self._start_pos: QPointF = QPointF()

    def mouse_press(self, scene: QGraphicsScene, event: QGraphicsSceneMouseEvent) -> None:
        scene.clearSelection()
        self._start_pos = event.scenePos()
        self._current_item = BlurItem()
        self._current_item.setPos(self._start_pos)
        self._current_item.set_rect(QRectF(0, 0, 0, 0))
        scene.addItem(self._current_item)
        event.accept()

    def mouse_move(self, scene: QGraphicsScene, event: QGraphicsSceneMouseEvent) -> None:
        if self._current_item is None:
            return
        pos = event.scenePos()
        rect = QRectF(QPointF(0, 0), pos - self._start_pos).normalized()
        self._current_item.set_rect(rect)
        event.accept()

    def mouse_release(self, scene: QGraphicsScene, event: QGraphicsSceneMouseEvent) -> None:
        if self._current_item is None:
            return
        if self._current_item._rect.width() < 5 and self._current_item._rect.height() < 5:
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
