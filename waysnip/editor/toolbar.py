"""Annotation toolbar — tool buttons for all annotation tools."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QAction, QActionGroup, QPixmap, QColor, QPainter, QIcon
from PyQt6.QtWidgets import QToolBar, QWidget

from waysnip.constants import TOOL_SHORTCUTS

# Tool definitions: (name, display_name, icon_color)
_TOOL_DEFS = [
    ("select", "Select", QColor(100, 100, 100)),
    ("rectangle", "Rectangle", QColor(220, 60, 60)),
    ("ellipse", "Ellipse", QColor(60, 140, 220)),
    ("arrow", "Arrow", QColor(220, 140, 30)),
    ("line", "Line", QColor(100, 180, 60)),
    ("text", "Text", QColor(180, 60, 220)),
    ("numbered_marker", "Marker", QColor(255, 0, 0)),
    ("freehand", "Pencil", QColor(30, 30, 30)),
    ("highlight", "Highlight", QColor(255, 255, 0)),
    ("blur", "Blur", QColor(128, 128, 128)),
    ("crop", "Crop", QColor(60, 180, 140)),
]


def _make_icon(color: QColor, size: int = 24) -> QIcon:
    """Create a simple colored square icon."""
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(color)
    painter.setPen(QColor(60, 60, 60))
    painter.drawRoundedRect(2, 2, size - 4, size - 4, 3, 3)
    painter.end()
    return QIcon(pixmap)


class AnnotationToolbar(QToolBar):
    """Toolbar with exclusive tool selection buttons."""

    tool_changed = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Tools", parent)
        self.setMovable(False)

        self._action_group = QActionGroup(self)
        self._action_group.setExclusive(True)
        self._actions: dict[str, QAction] = {}

        for name, display, color in _TOOL_DEFS:
            action = QAction(_make_icon(color), display, self)
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
