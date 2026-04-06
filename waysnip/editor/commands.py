"""Undo/redo command classes for the annotation editor."""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import QPointF, QRectF
from PyQt6.QtGui import QUndoCommand
from PyQt6.QtWidgets import QGraphicsScene

from waysnip.editor.tools.base import BaseAnnotationItem


class AddItemCommand(QUndoCommand):
    """Add an annotation item to the scene."""

    def __init__(self, scene: QGraphicsScene, item: BaseAnnotationItem) -> None:
        super().__init__("Add " + (item.item_type or "item"))
        self._scene = scene
        self._item = item

    def redo(self) -> None:
        self._scene.addItem(self._item)

    def undo(self) -> None:
        self._scene.removeItem(self._item)


class RemoveItemCommand(QUndoCommand):
    """Remove an annotation item from the scene."""

    def __init__(self, scene: QGraphicsScene, item: BaseAnnotationItem) -> None:
        super().__init__("Remove " + (item.item_type or "item"))
        self._scene = scene
        self._item = item

    def redo(self) -> None:
        self._scene.removeItem(self._item)

    def undo(self) -> None:
        self._scene.addItem(self._item)


class MoveItemCommand(QUndoCommand):
    """Move an annotation item to a new position."""

    def __init__(
        self,
        scene: QGraphicsScene,
        item: BaseAnnotationItem,
        old_pos: QPointF,
        new_pos: QPointF,
    ) -> None:
        super().__init__("Move " + (item.item_type or "item"))
        self._scene = scene
        self._item = item
        self._old_pos = old_pos
        self._new_pos = new_pos

    def redo(self) -> None:
        self._item.setPos(self._new_pos)

    def undo(self) -> None:
        self._item.setPos(self._old_pos)


class ResizeItemCommand(QUndoCommand):
    """Resize an annotation item."""

    def __init__(
        self,
        scene: QGraphicsScene,
        item: BaseAnnotationItem,
        old_rect: QRectF,
        new_rect: QRectF,
    ) -> None:
        super().__init__("Resize " + (item.item_type or "item"))
        self._scene = scene
        self._item = item
        self._old_rect = old_rect
        self._new_rect = new_rect

    def redo(self) -> None:
        if hasattr(self._item, "set_rect"):
            self._item.set_rect(self._new_rect)

    def undo(self) -> None:
        if hasattr(self._item, "set_rect"):
            self._item.set_rect(self._old_rect)


class ChangePropertyCommand(QUndoCommand):
    """Change a property on an annotation item."""

    def __init__(
        self,
        scene: QGraphicsScene,
        item: BaseAnnotationItem,
        property_name: str,
        old_value: Any,
        new_value: Any,
    ) -> None:
        super().__init__(f"Change {property_name}")
        self._scene = scene
        self._item = item
        self._property_name = property_name
        self._old_value = old_value
        self._new_value = new_value

    def redo(self) -> None:
        setattr(self._item, self._property_name, self._new_value)

    def undo(self) -> None:
        setattr(self._item, self._property_name, self._old_value)
