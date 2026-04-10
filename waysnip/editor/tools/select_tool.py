"""Select tool — click to select, drag to move, rubber-band multi-select."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import QColor, QPen, QBrush
from PyQt6.QtWidgets import (
    QGraphicsScene,
    QGraphicsSceneMouseEvent,
    QGraphicsRectItem,
)

from waysnip.editor.tools.base import BaseTool, BaseAnnotationItem, ResizeHandle


class SelectTool(BaseTool):
    """Select, move, and resize annotation items."""

    name = "select"
    icon = "select"
    shortcut = "V"
    cursor_shape = Qt.CursorShape.ArrowCursor

    def __init__(self) -> None:
        self._dragging: bool = False
        self._drag_item: BaseAnnotationItem | None = None
        self._drag_start_pos: QPointF = QPointF()
        self._drag_item_start: QPointF = QPointF()
        self._rubber_band: QGraphicsRectItem | None = None
        self._rubber_origin: QPointF = QPointF()
        self._resizing: bool = False
        self._resize_handle: ResizeHandle | None = None
        self._resize_item: BaseAnnotationItem | None = None
        self._resize_start_rect: QRectF = QRectF()
        self._resize_start_pos: QPointF = QPointF()

    def activate(self, scene: QGraphicsScene) -> None:
        pass

    def deactivate(self, scene: QGraphicsScene) -> None:
        self._cleanup_rubber_band(scene)

    def mouse_press(self, scene: QGraphicsScene, event: QGraphicsSceneMouseEvent) -> None:
        # Only act on left-click — right-click is reserved for context menu
        if event.button() != Qt.MouseButton.LeftButton:
            return

        pos = event.scenePos()
        item_at = scene.itemAt(pos, scene.views()[0].transform() if scene.views() else __import__("PyQt6.QtGui", fromlist=["QTransform"]).QTransform())

        # Check if clicking on a resize handle
        if isinstance(item_at, ResizeHandle):
            parent = item_at.parentItem()
            if isinstance(parent, BaseAnnotationItem):
                self._resizing = True
                self._resize_handle = item_at
                self._resize_item = parent
                self._resize_start_pos = pos
                if hasattr(parent, "_content_rect"):
                    self._resize_start_rect = QRectF(parent._content_rect())
                event.accept()
                return

        # Check if clicking on an annotation item
        if isinstance(item_at, BaseAnnotationItem):
            if not (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
                if not item_at.isSelected():
                    scene.clearSelection()
            item_at.setSelected(True)
            self._dragging = True
            self._drag_item = item_at
            self._drag_start_pos = pos
            self._drag_item_start = QPointF(item_at.pos())
            event.accept()
            return

        # Start rubber-band selection
        if not (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            scene.clearSelection()
        self._rubber_origin = pos
        self._rubber_band = QGraphicsRectItem()
        self._rubber_band.setPen(QPen(QColor(0, 120, 215), 1, Qt.PenStyle.DashLine))
        self._rubber_band.setBrush(QBrush(QColor(0, 120, 215, 40)))
        self._rubber_band.setZValue(10000)
        scene.addItem(self._rubber_band)
        event.accept()

    def mouse_move(self, scene: QGraphicsScene, event: QGraphicsSceneMouseEvent) -> None:
        pos = event.scenePos()

        if self._resizing and self._resize_handle and self._resize_item:
            delta = pos - self._resize_start_pos
            self._apply_resize(delta)
            event.accept()
            return

        if self._dragging and self._drag_item:
            delta = pos - self._drag_start_pos
            # Move all selected items
            for item in scene.selectedItems():
                if isinstance(item, BaseAnnotationItem):
                    item.setPos(item.pos() + delta)
            self._drag_start_pos = pos
            event.accept()
            return

        if self._rubber_band is not None:
            rect = QRectF(self._rubber_origin, pos).normalized()
            self._rubber_band.setRect(rect)
            event.accept()

    def mouse_release(self, scene: QGraphicsScene, event: QGraphicsSceneMouseEvent) -> None:
        if self._resizing:
            from waysnip.editor.commands import ResizeItemCommand

            if self._resize_item and hasattr(self._resize_item, "_content_rect"):
                new_rect = self._resize_item._content_rect()
                if self._resize_start_rect != new_rect:
                    cmd = ResizeItemCommand(
                        scene, self._resize_item, self._resize_start_rect, new_rect
                    )
                    if hasattr(scene, "undo_stack"):
                        scene.undo_stack.push(cmd)
            self._resizing = False
            self._resize_handle = None
            self._resize_item = None
            event.accept()
            return

        if self._dragging and self._drag_item:
            from waysnip.editor.commands import MoveItemCommand

            new_pos = self._drag_item.pos()
            if self._drag_item_start != new_pos:
                cmd = MoveItemCommand(scene, self._drag_item, self._drag_item_start, new_pos)
                if hasattr(scene, "undo_stack"):
                    scene.undo_stack.push(cmd)
            self._dragging = False
            self._drag_item = None
            event.accept()
            return

        if self._rubber_band is not None:
            rect = self._rubber_band.rect()
            self._cleanup_rubber_band(scene)
            # Select items within the rubber band
            for item in scene.items(rect):
                if isinstance(item, BaseAnnotationItem):
                    item.setSelected(True)
            event.accept()

    def _apply_resize(self, delta: QPointF) -> None:
        """Apply a resize delta based on the active handle position."""
        if not self._resize_handle or not self._resize_item:
            return
        if not hasattr(self._resize_item, "set_rect"):
            return

        rect = QRectF(self._resize_start_rect)
        pos = self._resize_handle.position

        if "left" in pos:
            rect.setLeft(rect.left() + delta.x())
        if "right" in pos:
            rect.setRight(rect.right() + delta.x())
        if "top" in pos:
            rect.setTop(rect.top() + delta.y())
        if "bottom" in pos:
            rect.setBottom(rect.bottom() + delta.y())

        # Ensure minimum size
        if rect.width() < 5:
            rect.setWidth(5)
        if rect.height() < 5:
            rect.setHeight(5)

        self._resize_item.set_rect(rect.normalized())

    def _cleanup_rubber_band(self, scene: QGraphicsScene) -> None:
        if self._rubber_band is not None:
            scene.removeItem(self._rubber_band)
            self._rubber_band = None
