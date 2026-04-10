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

# Z-value reserved for blur items — they always sit below regular annotations
BLUR_Z = -500


class AnnotationScene(QGraphicsScene):
    """Graphics scene that holds the background screenshot and annotation items."""

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self._background_item: QGraphicsPixmapItem | None = None
        self._background_pixmap: QPixmap | None = None
        self._active_tool: BaseTool | None = None
        self._undo_stack = QUndoStack(self)
        self._next_z: float = 1.0

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

    # --- Z-order management ---

    def addItem(self, item) -> None:
        """Override to auto-assign z-values to new annotation items."""
        super().addItem(item)
        if isinstance(item, BaseAnnotationItem):
            from waysnip.editor.tools.blur import BlurItem
            if isinstance(item, BlurItem):
                return  # Blur items manage their own z-value
            # If the item already has a z-value > 0 (e.g. from deserialization),
            # just ensure _next_z stays ahead of it
            if item.zValue() > 0:
                self._next_z = max(self._next_z, item.zValue() + 1)
            else:
                item.setZValue(self._next_z)
                self._next_z += 1

    def _sorted_annotations(self) -> list[BaseAnnotationItem]:
        """Return non-blur annotations sorted by z-value (lowest first)."""
        from waysnip.editor.tools.blur import BlurItem
        return sorted(
            (i for i in self.items() if isinstance(i, BaseAnnotationItem) and not isinstance(i, BlurItem)),
            key=lambda i: i.zValue(),
        )

    def bring_to_front(self, item: BaseAnnotationItem) -> float | None:
        """Move item above all others. Returns new z-value, or None if already on top."""
        annotations = self._sorted_annotations()
        if not annotations or item is annotations[-1]:
            return None
        new_z = self._next_z
        self._next_z += 1
        return new_z

    def send_to_back(self, item: BaseAnnotationItem) -> float | None:
        """Move item below all others. Returns new z-value, or None if already at back."""
        annotations = self._sorted_annotations()
        if not annotations or item is annotations[0]:
            return None
        new_z = annotations[0].zValue() - 1
        if new_z <= BLUR_Z:
            # Renumber everything to make room
            self._renumber_z_values()
            new_z = 0.5
        return new_z

    def move_up(self, item: BaseAnnotationItem) -> tuple[float, BaseAnnotationItem, float] | None:
        """Swap item with the one above it. Returns (new_z, other_item, other_new_z) or None."""
        annotations = self._sorted_annotations()
        try:
            idx = annotations.index(item)
        except ValueError:
            return None
        if idx >= len(annotations) - 1:
            return None  # Already on top
        other = annotations[idx + 1]
        return (other.zValue(), other, item.zValue())

    def move_down(self, item: BaseAnnotationItem) -> tuple[float, BaseAnnotationItem, float] | None:
        """Swap item with the one below it. Returns (new_z, other_item, other_new_z) or None."""
        annotations = self._sorted_annotations()
        try:
            idx = annotations.index(item)
        except ValueError:
            return None
        if idx <= 0:
            return None  # Already at back
        other = annotations[idx - 1]
        return (other.zValue(), other, item.zValue())

    def _renumber_z_values(self) -> None:
        """Reassign z-values sequentially starting from 1."""
        for i, item in enumerate(self._sorted_annotations(), start=1):
            item.setZValue(float(i))
        self._next_z = float(len(self._sorted_annotations()) + 1)

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
