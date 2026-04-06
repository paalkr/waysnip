"""Annotation tools package.

Importing this module registers all item types for deserialization.
"""

from __future__ import annotations

from waysnip.editor.tools.base import BaseTool, BaseAnnotationItem, register_item_type, ResizeHandle
from waysnip.editor.tools.select_tool import SelectTool
from waysnip.editor.tools.rectangle import RectangleTool, RectangleItem
from waysnip.editor.tools.ellipse import EllipseTool, EllipseItem
from waysnip.editor.tools.arrow import ArrowTool, ArrowItem
from waysnip.editor.tools.line import LineTool, LineItem
from waysnip.editor.tools.text import TextTool, TextItem
from waysnip.editor.tools.numbered_marker import NumberedMarkerTool, NumberedMarkerItem
from waysnip.editor.tools.freehand import FreehandTool, FreehandItem
from waysnip.editor.tools.highlight import HighlightTool, HighlightItem
from waysnip.editor.tools.blur import BlurTool, BlurItem
from waysnip.editor.tools.crop import CropTool

__all__ = [
    "BaseTool",
    "BaseAnnotationItem",
    "ResizeHandle",
    "register_item_type",
    "SelectTool",
    "RectangleTool",
    "RectangleItem",
    "EllipseTool",
    "EllipseItem",
    "ArrowTool",
    "ArrowItem",
    "LineTool",
    "LineItem",
    "TextTool",
    "TextItem",
    "NumberedMarkerTool",
    "NumberedMarkerItem",
    "FreehandTool",
    "FreehandItem",
    "HighlightTool",
    "HighlightItem",
    "BlurTool",
    "BlurItem",
    "CropTool",
]
