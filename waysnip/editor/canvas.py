"""Annotation canvas — QGraphicsView with zoom and pan support."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QPointF, QTimer, pyqtSignal
from PyQt6.QtGui import QPainter, QWheelEvent, QMouseEvent, QKeyEvent
from PyQt6.QtWidgets import QGraphicsView

from waysnip.editor.scene import AnnotationScene


class AnnotationCanvas(QGraphicsView):
    """Graphics view with Ctrl+scroll zoom, middle-button/space pan, and antialiasing."""

    _MIN_ZOOM = 0.1
    _MAX_ZOOM = 10.0

    zoom_changed = pyqtSignal(float)

    def __init__(self, scene: AnnotationScene, parent=None) -> None:
        super().__init__(scene, parent)
        self._zoom_factor: float = 1.0
        self._user_zoomed: bool = False  # True once the user manually zooms
        self._panning: bool = False
        self._pan_start: QPointF = QPointF()
        self._space_held: bool = False

        # Rendering
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.NoAnchor)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.NoAnchor)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

    # --- Zoom ---

    @property
    def zoom_factor(self) -> float:
        return self._zoom_factor

    def fit_in_view(self) -> None:
        """Fit the scene into the viewport, capped at 100%.

        Small images stay at 100% (no upscaling). Large images zoom out to fit.
        """
        if self.scene() is None:
            return
        self.fitInView(self.scene().sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        fitted = self.transform().m11()
        if fitted > 1.0:
            self.resetTransform()
            self._zoom_factor = 1.0
        else:
            self._zoom_factor = fitted
        self._user_zoomed = False
        self.zoom_changed.emit(self._zoom_factor)

    # Keep old name as alias for compatibility.
    fit_in_view_on_show = fit_in_view

    def zoom_to_actual(self) -> None:
        """Zoom to 100% (1:1 pixels)."""
        self._user_zoomed = True
        self.zoom_to(1.0)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        # Defer fit until the layout is complete — showEvent fires before
        # the viewport has its final size.
        QTimer.singleShot(0, self.fit_in_view)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        # Re-fit when the window is resized, but only if the user hasn't
        # manually zoomed (Ctrl+scroll, menu zoom, etc.).
        if self.scene() is not None and not self._user_zoomed:
            QTimer.singleShot(0, self.fit_in_view)

    def zoom_to(self, factor: float, center: QPointF | None = None) -> None:
        """Set absolute zoom level, optionally around a viewport point."""
        factor = max(self._MIN_ZOOM, min(self._MAX_ZOOM, factor))
        if center is None:
            center = QPointF(self.viewport().width() / 2, self.viewport().height() / 2)

        old_scene_pos = self.mapToScene(center.toPoint())
        scale = factor / self._zoom_factor
        self.scale(scale, scale)
        self._zoom_factor = factor

        new_scene_pos = self.mapToScene(center.toPoint())
        delta = new_scene_pos - old_scene_pos
        self.translate(delta.x(), delta.y())
        self.zoom_changed.emit(self._zoom_factor)

    def wheelEvent(self, event: QWheelEvent) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            angle = event.angleDelta().y()
            if angle > 0:
                new_zoom = self._zoom_factor * 1.15
            elif angle < 0:
                new_zoom = self._zoom_factor / 1.15
            else:
                return
            self._user_zoomed = True
            self.zoom_to(new_zoom, event.position())
            event.accept()
        else:
            super().wheelEvent(event)

    # --- Pan ---

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.MiddleButton or (
            self._space_held and event.button() == Qt.MouseButton.LeftButton
        ):
            self._panning = True
            self._pan_start = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._panning:
            delta = event.position() - self._pan_start
            self._pan_start = event.position()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - int(delta.x())
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - int(delta.y())
            )
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._panning and (
            event.button() == Qt.MouseButton.MiddleButton
            or event.button() == Qt.MouseButton.LeftButton
        ):
            self._panning = False
            self.unsetCursor()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            self._space_held = True
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            self._space_held = False
            if not self._panning:
                self.unsetCursor()
        super().keyReleaseEvent(event)
