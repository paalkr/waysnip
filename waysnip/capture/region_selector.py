"""Fullscreen overlay for rubber-band region selection with magnifier."""

from __future__ import annotations

from enum import Enum, auto

from PyQt6.QtCore import (
    QPoint,
    QPointF,
    QRect,
    QRectF,
    QSize,
    Qt,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PyQt6.QtWidgets import QApplication, QWidget

from waysnip.constants import HANDLE_SIZE, HANDLE_HALF

_OVERLAY_COLOR = QColor(0, 0, 0, 128)
_SELECTION_BORDER = QColor(255, 255, 255, 220)
_HANDLE_FILL = QColor(255, 255, 255, 240)
_HANDLE_BORDER = QColor(60, 60, 60, 200)
_DIM_LABEL_BG = QColor(0, 0, 0, 180)
_DIM_LABEL_FG = QColor(255, 255, 255, 230)

_MAGNIFIER_SIZE = 150
_MAGNIFIER_ZOOM = 5
_MAGNIFIER_OFFSET = 20
_GRID_COLOR = QColor(200, 200, 200, 80)
_CROSSHAIR_COLOR = QColor(255, 0, 0, 160)


class _Handle(Enum):
    """Resize handle positions."""

    TOP_LEFT = auto()
    TOP = auto()
    TOP_RIGHT = auto()
    RIGHT = auto()
    BOTTOM_RIGHT = auto()
    BOTTOM = auto()
    BOTTOM_LEFT = auto()
    LEFT = auto()


class _Phase(Enum):
    IDLE = auto()
    DRAWING = auto()
    DRAWN = auto()       # selection complete, handles visible
    RESIZING = auto()
    MOVING = auto()


class RegionSelector(QWidget):
    """Fullscreen overlay that lets the user select a rectangular region."""

    region_selected = pyqtSignal(QPixmap)
    cancelled = pyqtSignal()

    def __init__(self, screenshot: QPixmap, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._screenshot = screenshot
        self._phase = _Phase.IDLE

        # Selection rectangle (in widget coordinates).
        self._selection = QRect()
        self._origin = QPoint()

        # Resize / move state.
        self._active_handle: _Handle | None = None
        self._drag_start = QPoint()
        self._selection_at_drag_start = QRect()

        # Mouse tracking for magnifier.
        self._cursor_pos = QPoint()

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)

        # Cover all monitors.
        screen = QApplication.primaryScreen()
        if screen is not None:
            vg = screen.virtualGeometry()
            self.setGeometry(vg)

    # ------------------------------------------------------------------
    # Handle geometry helpers
    # ------------------------------------------------------------------

    def _handle_rects(self) -> dict[_Handle, QRect]:
        """Return a dict mapping each handle enum to its screen rect."""
        r = self._selection.normalized()
        hs = int(HANDLE_SIZE)
        hh = int(HANDLE_HALF)

        cx = r.x() + r.width() // 2
        cy = r.y() + r.height() // 2

        return {
            _Handle.TOP_LEFT: QRect(r.left() - hh, r.top() - hh, hs, hs),
            _Handle.TOP: QRect(cx - hh, r.top() - hh, hs, hs),
            _Handle.TOP_RIGHT: QRect(r.right() - hh, r.top() - hh, hs, hs),
            _Handle.RIGHT: QRect(r.right() - hh, cy - hh, hs, hs),
            _Handle.BOTTOM_RIGHT: QRect(r.right() - hh, r.bottom() - hh, hs, hs),
            _Handle.BOTTOM: QRect(cx - hh, r.bottom() - hh, hs, hs),
            _Handle.BOTTOM_LEFT: QRect(r.left() - hh, r.bottom() - hh, hs, hs),
            _Handle.LEFT: QRect(r.left() - hh, cy - hh, hs, hs),
        }

    def _handle_at(self, pos: QPoint) -> _Handle | None:
        """Return the handle under *pos*, or None."""
        for handle, rect in self._handle_rects().items():
            if rect.adjusted(-2, -2, 2, 2).contains(pos):
                return handle
        return None

    def _cursor_for_handle(self, handle: _Handle) -> Qt.CursorShape:
        mapping = {
            _Handle.TOP_LEFT: Qt.CursorShape.SizeFDiagCursor,
            _Handle.TOP: Qt.CursorShape.SizeVerCursor,
            _Handle.TOP_RIGHT: Qt.CursorShape.SizeBDiagCursor,
            _Handle.RIGHT: Qt.CursorShape.SizeHorCursor,
            _Handle.BOTTOM_RIGHT: Qt.CursorShape.SizeFDiagCursor,
            _Handle.BOTTOM: Qt.CursorShape.SizeVerCursor,
            _Handle.BOTTOM_LEFT: Qt.CursorShape.SizeBDiagCursor,
            _Handle.LEFT: Qt.CursorShape.SizeHorCursor,
        }
        return mapping[handle]

    # ------------------------------------------------------------------
    # Paint
    # ------------------------------------------------------------------

    def paintEvent(self, event) -> None:  # noqa: ANN001
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw the frozen screenshot as background.
        p.drawPixmap(0, 0, self._screenshot)

        sel = self._selection.normalized()

        if sel.isValid() and sel.width() > 0 and sel.height() > 0:
            # Dark overlay outside selection.
            overlay = QPainterPath()
            overlay.addRect(QRectF(self.rect()))
            hole = QPainterPath()
            hole.addRect(QRectF(sel))
            overlay = overlay.subtracted(hole)
            p.fillPath(overlay, _OVERLAY_COLOR)

            # Selection border.
            pen = QPen(_SELECTION_BORDER, 1, Qt.PenStyle.DashLine)
            p.setPen(pen)
            p.drawRect(sel)

            # Dimension label.
            self._draw_dimension_label(p, sel)

            # Resize handles (only in DRAWN / RESIZING phase).
            if self._phase in (_Phase.DRAWN, _Phase.RESIZING, _Phase.MOVING):
                self._draw_handles(p)
        else:
            # No selection yet — full overlay.
            p.fillRect(self.rect(), _OVERLAY_COLOR)

        # Magnifier (shown during IDLE and DRAWING).
        if self._phase in (_Phase.IDLE, _Phase.DRAWING):
            self._draw_magnifier(p)

        p.end()

    def _draw_dimension_label(self, p: QPainter, sel: QRect) -> None:
        text = f"{sel.width()} × {sel.height()}"
        font = QFont("Sans", 10)
        p.setFont(font)
        fm = p.fontMetrics()
        tw = fm.horizontalAdvance(text) + 12
        th = fm.height() + 6

        lx = sel.x() + (sel.width() - tw) // 2
        ly = sel.bottom() + 6
        if ly + th > self.height():
            ly = sel.top() - th - 4

        label_rect = QRect(lx, ly, tw, th)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(_DIM_LABEL_BG)
        p.drawRoundedRect(label_rect, 3, 3)
        p.setPen(_DIM_LABEL_FG)
        p.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, text)

    def _draw_handles(self, p: QPainter) -> None:
        for rect in self._handle_rects().values():
            p.setPen(QPen(_HANDLE_BORDER, 1))
            p.setBrush(QBrush(_HANDLE_FILL))
            p.drawRect(rect)

    def _draw_magnifier(self, p: QPainter) -> None:
        """Draw a circular magnifier loupe near the cursor."""
        radius = _MAGNIFIER_SIZE // 2
        src_half = radius // _MAGNIFIER_ZOOM  # pixels around cursor to sample

        cx, cy = self._cursor_pos.x(), self._cursor_pos.y()

        # Determine loupe position — bottom-right by default, flip if near edge.
        lx = cx + _MAGNIFIER_OFFSET
        ly = cy + _MAGNIFIER_OFFSET
        if lx + _MAGNIFIER_SIZE > self.width():
            lx = cx - _MAGNIFIER_OFFSET - _MAGNIFIER_SIZE
        if ly + _MAGNIFIER_SIZE > self.height():
            ly = cy - _MAGNIFIER_OFFSET - _MAGNIFIER_SIZE

        center = QPointF(lx + radius, ly + radius)

        # Clip to circle.
        clip_path = QPainterPath()
        clip_path.addEllipse(center, radius, radius)
        p.save()
        p.setClipPath(clip_path)

        # Draw zoomed region.
        src_rect = QRect(cx - src_half, cy - src_half, src_half * 2, src_half * 2)
        dst_rect = QRect(lx, ly, _MAGNIFIER_SIZE, _MAGNIFIER_SIZE)
        p.drawPixmap(dst_rect, self._screenshot, src_rect)

        # Grid lines.
        pixel_size = _MAGNIFIER_SIZE / (src_half * 2)
        grid_pen = QPen(_GRID_COLOR, 0.5)
        p.setPen(grid_pen)
        if pixel_size >= 4:
            for i in range(src_half * 2 + 1):
                x = lx + i * pixel_size
                p.drawLine(QPointF(x, ly), QPointF(x, ly + _MAGNIFIER_SIZE))
                y = ly + i * pixel_size
                p.drawLine(QPointF(lx, y), QPointF(lx + _MAGNIFIER_SIZE, y))

        # Crosshair.
        cross_pen = QPen(_CROSSHAIR_COLOR, 1)
        p.setPen(cross_pen)
        p.drawLine(QPointF(center.x(), ly), QPointF(center.x(), ly + _MAGNIFIER_SIZE))
        p.drawLine(QPointF(lx, center.y()), QPointF(lx + _MAGNIFIER_SIZE, center.y()))

        p.restore()

        # Circle border.
        p.setPen(QPen(_SELECTION_BORDER, 2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(center, radius, radius)

    # ------------------------------------------------------------------
    # Mouse events
    # ------------------------------------------------------------------

    def mousePressEvent(self, event) -> None:  # noqa: ANN001
        pos = event.position().toPoint()

        if event.button() != Qt.MouseButton.LeftButton:
            return

        if self._phase in (_Phase.DRAWN,):
            # Check for handle grab.
            handle = self._handle_at(pos)
            if handle is not None:
                self._active_handle = handle
                self._phase = _Phase.RESIZING
                self._drag_start = pos
                self._selection_at_drag_start = QRect(self._selection.normalized())
                return

            # Check for move (click inside selection).
            if self._selection.normalized().contains(pos):
                self._phase = _Phase.MOVING
                self._drag_start = pos
                self._selection_at_drag_start = QRect(self._selection.normalized())
                return

        # Start a new selection.
        self._origin = pos
        self._selection = QRect(pos, QSize(0, 0))
        self._phase = _Phase.DRAWING
        self.update()

    def mouseMoveEvent(self, event) -> None:  # noqa: ANN001
        pos = event.position().toPoint()
        self._cursor_pos = pos

        if self._phase == _Phase.DRAWING:
            self._selection = QRect(self._origin, pos).normalized()
            self.update()
            return

        if self._phase == _Phase.RESIZING:
            self._apply_resize(pos)
            self.update()
            return

        if self._phase == _Phase.MOVING:
            delta = pos - self._drag_start
            self._selection = self._selection_at_drag_start.translated(delta)
            self.update()
            return

        # IDLE or DRAWN — update cursor shape and magnifier.
        if self._phase == _Phase.DRAWN:
            handle = self._handle_at(pos)
            if handle is not None:
                self.setCursor(self._cursor_for_handle(handle))
            elif self._selection.normalized().contains(pos):
                self.setCursor(Qt.CursorShape.SizeAllCursor)
            else:
                self.setCursor(Qt.CursorShape.CrossCursor)

        # Repaint magnifier region only during IDLE.
        if self._phase == _Phase.IDLE:
            self.update()

    def mouseReleaseEvent(self, event) -> None:  # noqa: ANN001
        if event.button() != Qt.MouseButton.LeftButton:
            return

        if self._phase == _Phase.DRAWING:
            sel = self._selection.normalized()
            if sel.width() < 2 or sel.height() < 2:
                self._phase = _Phase.IDLE
                self._selection = QRect()
            else:
                self._phase = _Phase.DRAWN
            self.update()
            return

        if self._phase in (_Phase.RESIZING, _Phase.MOVING):
            self._phase = _Phase.DRAWN
            self._active_handle = None
            self.update()

    # ------------------------------------------------------------------
    # Keyboard events
    # ------------------------------------------------------------------

    def keyPressEvent(self, event) -> None:  # noqa: ANN001
        if event.key() == Qt.Key.Key_Escape:
            self.cancelled.emit()
            self.close()
            return

        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self._phase == _Phase.DRAWN:
                self._confirm_selection()
            return

    # ------------------------------------------------------------------
    # Resize logic
    # ------------------------------------------------------------------

    def _apply_resize(self, pos: QPoint) -> None:
        """Adjust the selection rectangle based on the active handle drag."""
        r = QRect(self._selection_at_drag_start)
        dx = pos.x() - self._drag_start.x()
        dy = pos.y() - self._drag_start.y()
        h = self._active_handle

        if h in (_Handle.TOP_LEFT, _Handle.TOP, _Handle.TOP_RIGHT):
            r.setTop(r.top() + dy)
        if h in (_Handle.BOTTOM_LEFT, _Handle.BOTTOM, _Handle.BOTTOM_RIGHT):
            r.setBottom(r.bottom() + dy)
        if h in (_Handle.TOP_LEFT, _Handle.LEFT, _Handle.BOTTOM_LEFT):
            r.setLeft(r.left() + dx)
        if h in (_Handle.TOP_RIGHT, _Handle.RIGHT, _Handle.BOTTOM_RIGHT):
            r.setRight(r.right() + dx)

        self._selection = r

    # ------------------------------------------------------------------
    # Confirm
    # ------------------------------------------------------------------

    def _confirm_selection(self) -> None:
        sel = self._selection.normalized()
        if sel.width() < 1 or sel.height() < 1:
            return
        cropped = self._screenshot.copy(sel)
        self.region_selected.emit(cropped)
        self.close()
