"""Editor module — annotation editor for screenshots."""

from __future__ import annotations

from waysnip.editor.scene import AnnotationScene
from waysnip.editor.canvas import AnnotationCanvas
from waysnip.editor.editor_window import EditorWindow
from waysnip.editor.toolbar import AnnotationToolbar
from waysnip.editor.properties_panel import PropertiesPanel
from waysnip.editor.commands import (
    AddItemCommand,
    RemoveItemCommand,
    MoveItemCommand,
    ResizeItemCommand,
    ChangePropertyCommand,
)

__all__ = [
    "AnnotationScene",
    "AnnotationCanvas",
    "EditorWindow",
    "AnnotationToolbar",
    "PropertiesPanel",
    "AddItemCommand",
    "RemoveItemCommand",
    "MoveItemCommand",
    "ResizeItemCommand",
    "ChangePropertyCommand",
]
