"""Annotation toolbar — tool buttons for all annotation tools."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal, Qt, QPointF, QRectF
from PyQt6.QtGui import (
    QAction, QActionGroup, QPixmap, QColor, QPainter, QIcon,
    QPen, QBrush, QFont, QPainterPath, QPolygonF,
)
from PyQt6.QtWidgets import QToolBar, QWidget

from waysnip.constants import TOOL_SHORTCUTS


def _icon(size: int = 28) -> tuple[QPixmap, QPainter]:
    """Create a transparent pixmap and painter for icon drawing."""
    pm = QPixmap(size, size)
    pm.fill(QColor(0, 0, 0, 0))
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    return pm, p


def _make_select_icon() -> QIcon:
    pm, p = _icon()
    pen = QPen(QColor(220, 220, 220), 2)
    p.setPen(pen)
    # Arrow cursor shape
    path = QPainterPath()
    path.moveTo(6, 4)
    path.lineTo(6, 22)
    path.lineTo(11, 17)
    path.lineTo(16, 24)
    path.lineTo(19, 22)
    path.lineTo(14, 15)
    path.lineTo(20, 15)
    path.closeSubpath()
    p.setBrush(QBrush(QColor(220, 220, 220)))
    p.setPen(QPen(QColor(60, 60, 60), 1))
    p.drawPath(path)
    p.end()
    return QIcon(pm)


def _make_rectangle_icon() -> QIcon:
    pm, p = _icon()
    p.setPen(QPen(QColor(220, 60, 60), 2))
    p.setBrush(QBrush(QColor(220, 60, 60, 40)))
    p.drawRect(4, 6, 20, 16)
    p.end()
    return QIcon(pm)


def _make_ellipse_icon() -> QIcon:
    pm, p = _icon()
    p.setPen(QPen(QColor(60, 140, 220), 2))
    p.setBrush(QBrush(QColor(60, 140, 220, 40)))
    p.drawEllipse(3, 5, 22, 18)
    p.end()
    return QIcon(pm)


def _make_arrow_icon() -> QIcon:
    pm, p = _icon()
    pen = QPen(QColor(220, 140, 30), 2)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    p.drawLine(5, 23, 22, 6)
    # Arrowhead
    p.setBrush(QBrush(QColor(220, 140, 30)))
    head = QPolygonF([QPointF(22, 6), QPointF(15, 7), QPointF(21, 13)])
    p.drawPolygon(head)
    p.end()
    return QIcon(pm)


def _make_line_icon() -> QIcon:
    pm, p = _icon()
    pen = QPen(QColor(100, 180, 60), 2.5)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    p.drawLine(5, 23, 23, 5)
    p.end()
    return QIcon(pm)


def _make_text_icon() -> QIcon:
    pm, p = _icon()
    p.setPen(QPen(QColor(180, 60, 220)))
    font = QFont("Sans", 16, QFont.Weight.Bold)
    p.setFont(font)
    p.drawText(QRectF(0, 0, 28, 28), Qt.AlignmentFlag.AlignCenter, "T")
    p.end()
    return QIcon(pm)


def _make_marker_icon() -> QIcon:
    pm, p = _icon()
    p.setPen(QPen(QColor(40, 40, 40), 1))
    p.setBrush(QBrush(QColor(220, 40, 40)))
    p.drawEllipse(3, 3, 22, 22)
    p.setPen(QPen(QColor(255, 255, 255)))
    font = QFont("Sans", 12, QFont.Weight.Bold)
    p.setFont(font)
    p.drawText(QRectF(3, 3, 22, 22), Qt.AlignmentFlag.AlignCenter, "1")
    p.end()
    return QIcon(pm)


def _make_pencil_icon() -> QIcon:
    pm, p = _icon()
    pen = QPen(QColor(220, 220, 220), 2)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    path = QPainterPath()
    path.moveTo(5, 20)
    path.cubicTo(8, 10, 14, 22, 23, 8)
    p.drawPath(path)
    p.end()
    return QIcon(pm)


def _make_highlight_icon() -> QIcon:
    pm, p = _icon()
    pen = QPen(QColor(255, 255, 0, 160), 8)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    p.drawLine(4, 18, 24, 10)
    p.end()
    return QIcon(pm)


def _make_blur_icon() -> QIcon:
    pm, p = _icon()
    # Grid pattern suggesting pixelation
    colors = [QColor(80, 80, 80), QColor(140, 140, 140)]
    sz = 5
    for row in range(5):
        for col in range(5):
            c = colors[(row + col) % 2]
            p.fillRect(2 + col * sz, 2 + row * sz, sz, sz, c)
    p.end()
    return QIcon(pm)


def _make_crop_icon() -> QIcon:
    pm, p = _icon()
    pen = QPen(QColor(60, 180, 140), 2)
    p.setPen(pen)
    # Crop marks (L-shapes at corners)
    # Top-left
    p.drawLine(4, 10, 4, 4)
    p.drawLine(4, 4, 10, 4)
    # Top-right
    p.drawLine(18, 4, 24, 4)
    p.drawLine(24, 4, 24, 10)
    # Bottom-right
    p.drawLine(24, 18, 24, 24)
    p.drawLine(24, 24, 18, 24)
    # Bottom-left
    p.drawLine(10, 24, 4, 24)
    p.drawLine(4, 24, 4, 18)
    p.end()
    return QIcon(pm)


# Tool definitions: (name, display_name, icon_factory)
_TOOL_DEFS = [
    ("select", "Select", _make_select_icon),
    ("rectangle", "Rectangle", _make_rectangle_icon),
    ("ellipse", "Ellipse", _make_ellipse_icon),
    ("arrow", "Arrow", _make_arrow_icon),
    ("line", "Line", _make_line_icon),
    ("text", "Text", _make_text_icon),
    ("numbered_marker", "Marker", _make_marker_icon),
    ("freehand", "Pencil", _make_pencil_icon),
    ("highlight", "Highlight", _make_highlight_icon),
    ("blur", "Blur", _make_blur_icon),
    ("crop", "Crop", _make_crop_icon),
]


class AnnotationToolbar(QToolBar):
    """Toolbar with exclusive tool selection buttons."""

    tool_changed = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Tools", parent)
        self.setMovable(False)

        self._action_group = QActionGroup(self)
        self._action_group.setExclusive(True)
        self._actions: dict[str, QAction] = {}

        for name, display, icon_factory in _TOOL_DEFS:
            action = QAction(icon_factory(), display, self)
            action.setCheckable(True)
            action.setData(name)
            shortcut = TOOL_SHORTCUTS.get(name, "")
            if shortcut:
                action.setShortcut(shortcut)
                action.setToolTip(f"{display} ({shortcut})")
            else:
                action.setToolTip(display)
            self._action_group.addAction(action)
            self.addAction(action)
            self._actions[name] = action

        # Default to select tool
        if "select" in self._actions:
            self._actions["select"].setChecked(True)

        self._action_group.triggered.connect(self._on_action_triggered)

    def _on_action_triggered(self, action: QAction) -> None:
        name = action.data()
        if name:
            self.tool_changed.emit(name)

    def set_active_tool(self, name: str) -> None:
        """Programmatically set the active tool button."""
        action = self._actions.get(name)
        if action:
            action.setChecked(True)

    def current_tool_name(self) -> str:
        action = self._action_group.checkedAction()
        if action:
            return action.data() or "select"
        return "select"
