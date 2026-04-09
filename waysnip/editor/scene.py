"""Annotation scene — holds the background screenshot and manages tools/items."""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QPixmap, QPainter, QColor, QUndoStack
from PyQt6.QtWidgets import (
    QGraphicsScene,
    QGraphicsPixmapItem,
    QGraphicsSceneMouseEvent,
)

from waysnip.editor.tool_properties import ToolPropertyStore
from waysnip.editor.tools.base import BaseAnnotationItem, BaseTool


class AnnotationScene(QGraphicsScene):
    """Graphics scene that holds the background screenshot and annotation items."""

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self._background_item: QGraphicsPixmapItem | None = None
        self._background_pixmap: QPixmap | None = None
        self._active_tool: BaseTool | None = None
        self._undo_stack = QUndoStack(self)

        self._tool_store: ToolPropertyStore | None = None
        self._active_tool_name: str = "select"

    # --- Background ---

    def set_background_pixmap(self, pixmap: QPixmap) -> None:
        """Set the background screenshot image."""
        if self._background_item is not None:
            self.removeItem(self._background_item)
        self._background_pixmap = pixmap
        self._background_item = QGraphicsPixmapItem(pixmap)
        self._background_item.setZValue(-1000)
        self._background_item.setTransformationMode(
            Qt.TransformationMode.SmoothTransformation
        )
        self._background_item.setFlag(
            QGraphicsPixmapItem.GraphicsItemFlag.ItemIsMovable, False
        )
        self._background_item.setFlag(
            QGraphicsPixmapItem.GraphicsItemFlag.ItemIsSelectable, False
        )
        self.addItem(self._background_item)
        self.setSceneRect(QRectF(pixmap.rect().toRectF()))

    @property
    def background_pixmap(self) -> QPixmap | None:
        return self._background_pixmap

    # --- Tool management ---

    @property
    def active_tool(self) -> BaseTool | None:
        return self._active_tool

    def set_active_tool(self, tool: BaseTool | None) -> None:
        if self._active_tool is not None:
            self._active_tool.deactivate(self)
        self._active_tool = tool
        if self._active_tool is not None:
            self._active_tool.activate(self)

    def set_tool_property_store(self, store: ToolPropertyStore) -> None:
        self._tool_store = store

    def set_active_tool_name(self, name: str) -> None:
        self._active_tool_name = name

    @property
    def drawing_properties(self) -> dict[str, Any]:
        """Return properties for the currently active tool, with QColor conversion."""
        if self._tool_store is None:
            return {}
        raw = self._tool_store.get(self._active_tool_name)
        result: dict[str, Any] = {}
        for k, v in raw.items():
            if k in ("pen_color", "fill_color") and isinstance(v, str):
                result[k] = QColor(v)
            else:
                result[k] = v
        return result

    # --- Undo stack ---

    @property
    def undo_stack(self) -> QUndoStack:
        return self._undo_stack

    # --- Query helpers ---

    def get_all_annotations(self) -> list[BaseAnnotationItem]:
        """Return all annotation items (excluding the background)."""
        items: list[BaseAnnotationItem] = []
        for item in self.items():
            if isinstance(item, BaseAnnotationItem):
                items.append(item)
        return items

    def render_to_pixmap(self) -> QPixmap:
        """Flatten the entire scene (background + annotations) to a QPixmap."""
        rect = self.sceneRect()
        pixmap = QPixmap(int(rect.width()), int(rect.height()))
        pixmap.fill(QColor(0, 0, 0, 0))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Deselect all items so handles don't render
        self.clearSelection()
        self.render(painter, source=rect)
        painter.end()
        return pixmap

    # --- Mouse event delegation ---

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if self._active_tool is not None:
            self._active_tool.mouse_press(self, event)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if self._active_tool is not None:
            self._active_tool.mouse_move(self, event)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if self._active_tool is not None:
            self._active_tool.mouse_release(self, event)
        else:
            super().mouseReleaseEvent(event)
