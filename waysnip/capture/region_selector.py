"""Fullscreen overlay for rubber-band region selection with magnifier.

Uses one fullscreen widget per monitor so the frozen screenshot covers
the GNOME top panel and dock (which constrain non-fullscreen windows).
"""

from __future__ import annotations

from enum import Enum, auto

from PyQt6.QtCore import (
    QObject,
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
    QScreen,
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


# ──────────────────────────────────────────────────────────────────────
# Logical → pixel mapping
#
# The full-layout screenshot is not necessarily 1:1 with Qt's logical
# coordinates.  grim renders the layout at the highest scale factor of
# all outputs, and gnome-screenshot captures physical pixels, so on any
# setup with display scaling the image is larger than the logical
# virtual desktop.  All sampling from the screenshot must go through
# this mapping; widget-space drawing (handles, borders) stays logical.
# ──────────────────────────────────────────────────────────────────────

def compute_screenshot_mapping(image_size: QSize, virtual: QRect) -> tuple[float, QPoint]:
    """Return (scale, origin) mapping logical virtual-desktop coords to image pixels.

    ``scale`` is pixels-per-logical-unit, derived from the image width vs the
    virtual desktop width.  ``origin`` is the logical top-left of the virtual
    desktop, which corresponds to pixel (0, 0) in the image.
    """
    if virtual.width() <= 0 or image_size.width() <= 0:
        return 1.0, QPoint(0, 0)
    return image_size.width() / virtual.width(), virtual.topLeft()


def logical_to_pixel_rect(rect: QRect, scale: float, origin: QPoint) -> QRectF:
    """Map a rect in logical virtual-desktop coords to screenshot pixel coords."""
    return QRectF(
        (rect.x() - origin.x()) * scale,
        (rect.y() - origin.y()) * scale,
        rect.width() * scale,
        rect.height() * scale,
    )


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


# ──────────────────────────────────────────────────────────────────────
# RegionSelector — the public API (same interface as before)
# ──────────────────────────────────────────────────────────────────────

class RegionSelector(QObject):
    """Manages per-screen fullscreen overlays for region selection.

    Usage is unchanged from the old single-widget version::

        selector = RegionSelector(screenshot_pixmap)
        selector.region_selected.connect(on_selected)
        selector.cancelled.connect(on_cancel)
        selector.show()
    """

    region_selected = pyqtSignal(QPixmap)
    cancelled = pyqtSignal()

    def __init__(self, screenshot: QPixmap, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._screenshot = screenshot

        # Shared selection state (virtual screen coordinates).
        self._phase = _Phase.IDLE
        self._selection = QRect()
        self._origin = QPoint()
        self._active_handle: _Handle | None = None
        self._drag_start = QPoint()
        self._selection_at_drag_start = QRect()
        self._cursor_pos = QPoint()

        # Create one overlay per screen.
        self._overlays: list[_ScreenOverlay] = []
        virtual = QRect()
        app = QApplication.instance()
        if app is not None:
            for screen in app.screens():
                virtual = virtual.united(screen.geometry())
                overlay = _ScreenOverlay(screen, self)
                self._overlays.append(overlay)

        # Logical → screenshot-pixel mapping (handles display scaling).
        self._scale, self._origin = compute_screenshot_mapping(screenshot.size(), virtual)

    # ── Public methods ────────────────────────────────────────────────

    def show(self) -> None:
        for overlay in self._overlays:
            overlay.show()

    def close(self) -> None:
        for overlay in self._overlays:
            overlay.close()

    def _update_all(self) -> None:
        for overlay in self._overlays:
            overlay.update()

    # ── Handle geometry helpers ───────────────────────────────────────

    def _handle_rects(self) -> dict[_Handle, QRect]:
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
        for handle, rect in self._handle_rects().items():
            if rect.adjusted(-2, -2, 2, 2).contains(pos):
                return handle
        return None

    @staticmethod
    def _cursor_for_handle(handle: _Handle) -> Qt.CursorShape:
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

    # ── Mouse event handlers (called by overlays, virtual coords) ─────

    def handle_mouse_press(self, vpos: QPoint, overlay: _ScreenOverlay) -> None:
        if self._phase in (_Phase.DRAWN,):
            handle = self._handle_at(vpos)
            if handle is not None:
                self._active_handle = handle
                self._phase = _Phase.RESIZING
                self._drag_start = vpos
                self._selection_at_drag_start = QRect(self._selection.normalized())
                return

            if self._selection.normalized().contains(vpos):
                self._phase = _Phase.MOVING
                self._drag_start = vpos
                self._selection_at_drag_start = QRect(self._selection.normalized())
                return

        self._origin = vpos
        self._selection = QRect(vpos, QSize(0, 0))
        self._phase = _Phase.DRAWING
        self._update_all()

    def handle_mouse_move(self, vpos: QPoint, overlay: _ScreenOverlay) -> None:
        self._cursor_pos = vpos

        if self._phase == _Phase.DRAWING:
            self._selection = QRect(self._origin, vpos).normalized()
            self._update_all()
            return

        if self._phase == _Phase.RESIZING:
            self._apply_resize(vpos)
            self._update_all()
            return

        if self._phase == _Phase.MOVING:
            delta = vpos - self._drag_start
            self._selection = self._selection_at_drag_start.translated(delta)
            self._update_all()
            return

        if self._phase == _Phase.DRAWN:
            handle = self._handle_at(vpos)
            if handle is not None:
                overlay.setCursor(self._cursor_for_handle(handle))
            elif self._selection.normalized().contains(vpos):
                overlay.setCursor(Qt.CursorShape.SizeAllCursor)
            else:
                overlay.setCursor(Qt.CursorShape.CrossCursor)

        if self._phase == _Phase.IDLE:
            self._update_all()

    def handle_mouse_release(self, vpos: QPoint) -> None:
        if self._phase == _Phase.DRAWING:
            sel = self._selection.normalized()
            if sel.width() < 2 or sel.height() < 2:
                self._phase = _Phase.IDLE
                self._selection = QRect()
            else:
                self._phase = _Phase.DRAWN
            self._update_all()
            return

        if self._phase in (_Phase.RESIZING, _Phase.MOVING):
            self._phase = _Phase.DRAWN
            self._active_handle = None
            self._update_all()

    def handle_key_press(self, key: int) -> None:
        if key == Qt.Key.Key_Escape:
            self.cancelled.emit()
            self.close()
            return

        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self._phase == _Phase.DRAWN:
                self._confirm_selection()

    # ── Resize logic ──────────────────────────────────────────────────

    def _apply_resize(self, pos: QPoint) -> None:
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

    # ── Confirm ───────────────────────────────────────────────────────

    def _confirm_selection(self) -> None:
        sel = self._selection.normalized()
        if sel.width() < 1 or sel.height() < 1:
            return
        src = logical_to_pixel_rect(sel, self._scale, self._origin)
        crop = src.toRect().intersected(self._screenshot.rect())
        if crop.width() < 1 or crop.height() < 1:
            return
        cropped = self._screenshot.copy(crop)
        self.region_selected.emit(cropped)
        self.close()


# ──────────────────────────────────────────────────────────────────────
# _ScreenOverlay — thin fullscreen widget for one monitor
# ──────────────────────────────────────────────────────────────────────

class _ScreenOverlay(QWidget):
    """Fullscreen widget covering a single monitor."""

    def __init__(self, screen: QScreen, group: RegionSelector) -> None:
        super().__init__()
        self._screen = screen
        self._group = group
        self._screen_origin = screen.geometry().topLeft()

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)

    def show(self) -> None:
        self.setScreen(self._screen)
        self.move(self._screen.geometry().topLeft())
        self.showFullScreen()

    # ── Coordinate helpers ────────────────────────────────────────────

    def _to_virtual(self, local: QPoint) -> QPoint:
        return local + self._screen_origin

    def _to_local(self, virtual: QPoint) -> QPoint:
        return virtual - self._screen_origin

    # ── Paint ─────────────────────────────────────────────────────────

    def paintEvent(self, event) -> None:  # noqa: ANN001
        g = self._group
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # Draw the portion of the screenshot that belongs to this screen.
        sr = self._screen.geometry()
        src = logical_to_pixel_rect(sr, g._scale, g._origin)
        p.drawPixmap(QRectF(0, 0, sr.width(), sr.height()), g._screenshot, src)

        sel = g._selection.normalized()

        if sel.isValid() and sel.width() > 0 and sel.height() > 0:
            # Dark overlay outside selection.
            overlay_path = QPainterPath()
            overlay_path.addRect(QRectF(self.rect()))

            local_sel = QRect(self._to_local(sel.topLeft()), sel.size())
            hole = QPainterPath()
            hole.addRect(QRectF(local_sel))
            overlay_path = overlay_path.subtracted(hole)
            p.fillPath(overlay_path, _OVERLAY_COLOR)

            # Selection border.
            p.setPen(QPen(_SELECTION_BORDER, 1, Qt.PenStyle.DashLine))
            p.drawRect(local_sel)

            # Dimension label.
            self._draw_dimension_label(p, local_sel, sel)

            # Resize handles.
            if g._phase in (_Phase.DRAWN, _Phase.RESIZING, _Phase.MOVING):
                self._draw_handles(p)
        else:
            p.fillRect(self.rect(), _OVERLAY_COLOR)

        # Magnifier (only on the screen where the cursor is).
        if g._phase in (_Phase.IDLE, _Phase.DRAWING):
            local_cursor = self._to_local(g._cursor_pos)
            if self.rect().contains(local_cursor):
                self._draw_magnifier(p, local_cursor)

        p.end()

    def _draw_dimension_label(self, p: QPainter, local_sel: QRect, virt_sel: QRect) -> None:
        # Show the output pixel size, which is what the saved file will have.
        k = self._group._scale
        text = f"{round(virt_sel.width() * k)} \u00d7 {round(virt_sel.height() * k)}"
        font = QFont("Sans", 10)
        p.setFont(font)
        fm = p.fontMetrics()
        tw = fm.horizontalAdvance(text) + 12
        th = fm.height() + 6

        lx = local_sel.x() + (local_sel.width() - tw) // 2
        ly = local_sel.bottom() + 6
        if ly + th > self.height():
            ly = local_sel.top() - th - 4

        label_rect = QRect(lx, ly, tw, th)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(_DIM_LABEL_BG)
        p.drawRoundedRect(label_rect, 3, 3)
        p.setPen(_DIM_LABEL_FG)
        p.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, text)

    def _draw_handles(self, p: QPainter) -> None:
        for rect in self._group._handle_rects().values():
            local_rect = QRect(self._to_local(rect.topLeft()), rect.size())
            if not self.rect().intersects(local_rect):
                continue
            p.setPen(QPen(_HANDLE_BORDER, 1))
            p.setBrush(QBrush(_HANDLE_FILL))
            p.drawRect(local_rect)

    def _draw_magnifier(self, p: QPainter, local_cursor: QPoint) -> None:
        """Draw a circular magnifier loupe near the cursor."""
        radius = _MAGNIFIER_SIZE // 2
        src_half = radius // _MAGNIFIER_ZOOM

        cx, cy = local_cursor.x(), local_cursor.y()

        lx = cx + _MAGNIFIER_OFFSET
        ly = cy + _MAGNIFIER_OFFSET
        if lx + _MAGNIFIER_SIZE > self.width():
            lx = cx - _MAGNIFIER_OFFSET - _MAGNIFIER_SIZE
        if ly + _MAGNIFIER_SIZE > self.height():
            ly = cy - _MAGNIFIER_OFFSET - _MAGNIFIER_SIZE

        center = QPointF(lx + radius, ly + radius)

        clip_path = QPainterPath()
        clip_path.addEllipse(center, radius, radius)
        p.save()
        p.setClipPath(clip_path)

        # Sample from the full screenshot in virtual coords.
        g = self._group
        vcx = local_cursor.x() + self._screen_origin.x()
        vcy = local_cursor.y() + self._screen_origin.y()
        src_rect = QRect(vcx - src_half, vcy - src_half, src_half * 2, src_half * 2)
        src = logical_to_pixel_rect(src_rect, g._scale, g._origin)
        dst_rect = QRect(lx, ly, _MAGNIFIER_SIZE, _MAGNIFIER_SIZE)
        p.drawPixmap(QRectF(dst_rect), g._screenshot, src)

        # Grid lines.
        pixel_size = _MAGNIFIER_SIZE / (src_half * 2)
        if pixel_size >= 4:
            p.setPen(QPen(_GRID_COLOR, 0.5))
            for i in range(src_half * 2 + 1):
                x = lx + i * pixel_size
                p.drawLine(QPointF(x, ly), QPointF(x, ly + _MAGNIFIER_SIZE))
                y = ly + i * pixel_size
                p.drawLine(QPointF(lx, y), QPointF(lx + _MAGNIFIER_SIZE, y))

        # Crosshair.
        p.setPen(QPen(_CROSSHAIR_COLOR, 1))
        p.drawLine(QPointF(center.x(), ly), QPointF(center.x(), ly + _MAGNIFIER_SIZE))
        p.drawLine(QPointF(lx, center.y()), QPointF(lx + _MAGNIFIER_SIZE, center.y()))

        p.restore()

        # Circle border.
        p.setPen(QPen(_SELECTION_BORDER, 2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(center, radius, radius)

    # ── Mouse events → delegate to group in virtual coords ────────────

    def mousePressEvent(self, event) -> None:  # noqa: ANN001
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self._group.handle_mouse_press(self._to_virtual(event.position().toPoint()), self)

    def mouseMoveEvent(self, event) -> None:  # noqa: ANN001
        self._group.handle_mouse_move(self._to_virtual(event.position().toPoint()), self)

    def mouseReleaseEvent(self, event) -> None:  # noqa: ANN001
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self._group.handle_mouse_release(self._to_virtual(event.position().toPoint()))

    def keyPressEvent(self, event) -> None:  # noqa: ANN001
        self._group.handle_key_press(event.key())
