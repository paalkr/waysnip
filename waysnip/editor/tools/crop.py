"""Crop tool — non-persistent overlay for cropping the screenshot."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QColor, QPen, QBrush, QPainterPath
from PyQt6.QtWidgets import (
    QGraphicsScene,
    QGraphicsSceneMouseEvent,
    QGraphicsPathItem,
    QGraphicsRectItem,
)

from waysnip.editor.tools.base import BaseTool


class _CropOverlay(QGraphicsPathItem):
    """Dark overlay with a clear crop region cut out."""

    def __init__(self, scene_rect: QRectF, crop_rect: QRectF) -> None:
        super().__init__()
        self.setZValue(5000)
        self.update_rects(scene_rect, crop_rect)

    def update_rects(self, scene_rect: QRectF, crop_rect: QRectF) -> None:
        path = QPainterPath()
        path.addRect(scene_rect)
        path.addRect(crop_rect)
        # setFillRule to create the "hole"
        path.setFillRule(Qt.FillRule.OddEvenFill)
        self.setPath(path)
        self.setBrush(QBrush(QColor(0, 0, 0, 128)))
        self.setPen(QPen(Qt.PenStyle.NoPen))


class _CropBorder(QGraphicsRectItem):
    """Dashed border around the crop region."""

    def __init__(self, crop_rect: QRectF) -> None:
        super().__init__(crop_rect)
        self.setZValue(5001)
        self.setPen(QPen(QColor(255, 255, 255), 1, Qt.PenStyle.DashLine))
        self.setBrush(QBrush(Qt.BrushStyle.NoBrush))

    def update_rect(self, crop_rect: QRectF) -> None:
        self.setRect(crop_rect)


class CropTool(BaseTool):
    """Tool for cropping the screenshot. Confirm with Enter, cancel with Escape."""

    name = "crop"
    icon = "crop"
    shortcut = "C"
    cursor_shape = Qt.CursorShape.CrossCursor

    def __init__(self) -> None:
        self._overlay: _CropOverlay | None = None
        self._border: _CropBorder | None = None
        self._crop_rect: QRectF = QRectF()
        self._start_pos: QPointF = QPointF()
        self._drawing: bool = False
        self._scene: QGraphicsScene | None = None

    def activate(self, scene: QGraphicsScene) -> None:
        self._scene = scene
        scene.clearSelection()

    def deactivate(self, scene: QGraphicsScene) -> None:
        self._cancel(scene)

    def mouse_press(self, scene: QGraphicsScene, event: QGraphicsSceneMouseEvent) -> None:
        # Remove any existing overlay
        self._cleanup(scene)
        self._start_pos = event.scenePos()
        self._crop_rect = QRectF(self._start_pos, self._start_pos)
        self._overlay = _CropOverlay(scene.sceneRect(), self._crop_rect)
        self._border = _CropBorder(self._crop_rect)
        scene.addItem(self._overlay)
        scene.addItem(self._border)
        self._drawing = True
        event.accept()

    def mouse_move(self, scene: QGraphicsScene, event: QGraphicsSceneMouseEvent) -> None:
        if not self._drawing:
            return
        pos = event.scenePos()
        self._crop_rect = QRectF(self._start_pos, pos).normalized()
        # Clamp to scene bounds
        self._crop_rect = self._crop_rect.intersected(scene.sceneRect())
        if self._overlay:
            self._overlay.update_rects(scene.sceneRect(), self._crop_rect)
        if self._border:
            self._border.update_rect(self._crop_rect)
        event.accept()

    def mouse_release(self, scene: QGraphicsScene, event: QGraphicsSceneMouseEvent) -> None:
        self._drawing = False
        if self._crop_rect.width() < 5 or self._crop_rect.height() < 5:
            self._cancel(scene)
        # Otherwise, wait for Enter to confirm or Escape to cancel.
        # The editor window handles keyPressEvent and calls confirm/cancel.
        event.accept()

    def confirm(self, scene: QGraphicsScene) -> None:
        """Apply the crop — crop the background pixmap and adjust scene rect."""
        if self._crop_rect.isNull() or self._crop_rect.width() < 5:
            self._cancel(scene)
            return

        # Import here to avoid circular imports
        from waysnip.editor.scene import AnnotationScene

        if not isinstance(scene, AnnotationScene):
            self._cleanup(scene)
            return

        bg = scene.background_pixmap
        if bg is not None:
            cropped = bg.copy(self._crop_rect.toRect())
            # Adjust all item positions relative to the crop
            offset = self._crop_rect.topLeft()
            for item in scene.get_all_annotations():
                item.setPos(item.pos() - offset)

            self._cleanup(scene)
            scene.set_background_pixmap(cropped)
        else:
            self._cleanup(scene)

    def _cancel(self, scene: QGraphicsScene) -> None:
        """Cancel crop operation."""
        self._cleanup(scene)
        self._crop_rect = QRectF()

    def _cleanup(self, scene: QGraphicsScene) -> None:
        if self._overlay is not None:
            scene.removeItem(self._overlay)
            self._overlay = None
        if self._border is not None:
            scene.removeItem(self._border)
            self._border = None
        self._drawing = False

    @property
    def has_crop_selection(self) -> bool:
        return (
            self._overlay is not None
            and not self._crop_rect.isNull()
            and self._crop_rect.width() >= 5
        )
