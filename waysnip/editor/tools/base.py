"""Base classes for annotation tools and items.

This module defines the interface contract that all annotation tools and items
must implement. Build agents work against these real classes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import QColor, QCursor, QPen, QBrush
from PyQt6.QtWidgets import (
    QGraphicsItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSceneMouseEvent,
)

from waysnip.constants import HANDLE_SIZE, HANDLE_HALF


class BaseTool(ABC):
    """Abstract base for all annotation tools.

    Each tool handles mouse interaction on the scene and creates/modifies
    annotation items.
    """

    name: str = ""
    icon: str = ""
    shortcut: str = ""
    cursor_shape: Qt.CursorShape = Qt.CursorShape.CrossCursor

    @abstractmethod
    def mouse_press(self, scene: QGraphicsScene, event: QGraphicsSceneMouseEvent) -> None:
        """Handle mouse press on the scene."""

    @abstractmethod
    def mouse_move(self, scene: QGraphicsScene, event: QGraphicsSceneMouseEvent) -> None:
        """Handle mouse move on the scene."""

    @abstractmethod
    def mouse_release(self, scene: QGraphicsScene, event: QGraphicsSceneMouseEvent) -> None:
        """Handle mouse release on the scene."""

    def activate(self, scene: QGraphicsScene) -> None:
        """Called when this tool becomes the active tool."""

    def deactivate(self, scene: QGraphicsScene) -> None:
        """Called when switching away from this tool."""


class ResizeHandle(QGraphicsRectItem):
    """Small square handle for resizing annotation items.

    Handles are positioned at corners and edge midpoints of the parent item's
    bounding rect. The `position` attribute indicates which handle this is.

    Positions: "top-left", "top", "top-right", "right",
               "bottom-right", "bottom", "bottom-left", "left"
    """

    def __init__(self, position: str, parent: BaseAnnotationItem) -> None:
        super().__init__(-HANDLE_HALF, -HANDLE_HALF, HANDLE_SIZE, HANDLE_SIZE, parent)
        self.position = position
        self.setBrush(QBrush(QColor(255, 255, 255)))
        self.setPen(QPen(QColor(0, 120, 215), 1))
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        self.setCursor(self._cursor_for_position(position))
        self.setZValue(1000)
        self.setVisible(False)

    @staticmethod
    def _cursor_for_position(position: str) -> QCursor:
        mapping = {
            "top-left": Qt.CursorShape.SizeFDiagCursor,
            "top": Qt.CursorShape.SizeVerCursor,
            "top-right": Qt.CursorShape.SizeBDiagCursor,
            "right": Qt.CursorShape.SizeHorCursor,
            "bottom-right": Qt.CursorShape.SizeFDiagCursor,
            "bottom": Qt.CursorShape.SizeVerCursor,
            "bottom-left": Qt.CursorShape.SizeBDiagCursor,
            "left": Qt.CursorShape.SizeHorCursor,
        }
        return QCursor(mapping.get(position, Qt.CursorShape.ArrowCursor))

    def update_position(self, rect: QRectF) -> None:
        """Reposition this handle based on the parent's bounding rect."""
        positions = {
            "top-left": rect.topLeft(),
            "top": QPointF(rect.center().x(), rect.top()),
            "top-right": rect.topRight(),
            "right": QPointF(rect.right(), rect.center().y()),
            "bottom-right": rect.bottomRight(),
            "bottom": QPointF(rect.center().x(), rect.bottom()),
            "bottom-left": rect.bottomLeft(),
            "left": QPointF(rect.left(), rect.center().y()),
        }
        pos = positions.get(self.position, rect.center())
        self.setPos(pos)


class BaseAnnotationItem(QGraphicsItem):
    """Abstract base for all annotation items on the scene.

    Subclasses must implement paint() and boundingRect(). They get:
    - Configurable pen/fill colors, opacity, pen width, rotation
    - Resize handles shown when selected
    - clone() for duplication
    - serialize()/deserialize() for persistence in PNG metadata
    """

    # Type identifier for serialization — subclasses must override
    item_type: str = ""

    def __init__(self, parent: QGraphicsItem | None = None) -> None:
        super().__init__(parent)

        # Visual properties
        self._pen_color = QColor(255, 0, 0)
        self._fill_color = QColor(0, 0, 0, 0)  # transparent
        self._pen_width: int = 3
        self._opacity: float = 1.0
        self._rotation_angle: float = 0.0

        # Interaction flags
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)

        # Resize handles
        self._handles: list[ResizeHandle] = []
        handle_positions = [
            "top-left", "top", "top-right", "right",
            "bottom-right", "bottom", "bottom-left", "left",
        ]
        for pos in handle_positions:
            self._handles.append(ResizeHandle(pos, self))

    # --- Property accessors ---

    @property
    def pen_color(self) -> QColor:
        return self._pen_color

    @pen_color.setter
    def pen_color(self, color: QColor) -> None:
        self._pen_color = color
        self.update()

    @property
    def fill_color(self) -> QColor:
        return self._fill_color

    @fill_color.setter
    def fill_color(self, color: QColor) -> None:
        self._fill_color = color
        self.update()

    @property
    def pen_width(self) -> int:
        return self._pen_width

    @pen_width.setter
    def pen_width(self, width: int) -> None:
        self._pen_width = max(1, width)
        self.update()

    @property
    def item_opacity(self) -> float:
        return self._opacity

    @item_opacity.setter
    def item_opacity(self, opacity: float) -> None:
        self._opacity = max(0.0, min(1.0, opacity))
        self.setOpacity(self._opacity)

    @property
    def rotation_angle(self) -> float:
        return self._rotation_angle

    @rotation_angle.setter
    def rotation_angle(self, angle: float) -> None:
        self._rotation_angle = angle
        self.setRotation(angle)

    # --- Pen/brush helpers ---

    def apply_drawing_properties(self, props: dict) -> None:
        """Apply properties from scene.drawing_properties to this item."""
        if "pen_color" in props:
            self._pen_color = QColor(props["pen_color"])
        if "fill_color" in props:
            self._fill_color = QColor(props["fill_color"])
        if "pen_width" in props:
            self._pen_width = max(1, props["pen_width"])
        if "item_opacity" in props:
            self.item_opacity = props["item_opacity"]

    def make_pen(self) -> QPen:
        """Create a QPen from the current pen color and width."""
        pen = QPen(self._pen_color, self._pen_width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        return pen

    def make_brush(self) -> QBrush:
        """Create a QBrush from the current fill color."""
        return QBrush(self._fill_color)

    # --- Handle management ---

    def _update_handles(self) -> None:
        """Reposition resize handles to match current bounding rect."""
        rect = self._content_rect()
        visible = self.isSelected()
        for handle in self._handles:
            handle.update_position(rect)
            handle.setVisible(visible)

    def _content_rect(self) -> QRectF:
        """Return the content rect (without handle margins).

        Subclasses should override this to return their actual shape rect.
        Default returns boundingRect() shrunk by handle margins.
        """
        r = self.boundingRect()
        margin = HANDLE_HALF
        return r.adjusted(margin, margin, -margin, -margin)

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value: Any) -> Any:
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            self._update_handles()
        elif change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self._update_handles()
        return super().itemChange(change, value)

    # --- Serialization ---

    def serialize(self) -> dict[str, Any]:
        """Serialize this item to a dict for PNG metadata storage.

        Subclasses should call super().serialize() and add their own fields.
        """
        return {
            "type": self.item_type,
            "x": self.pos().x(),
            "y": self.pos().y(),
            "pen_color": self._pen_color.name(QColor.NameFormat.HexArgb),
            "fill_color": self._fill_color.name(QColor.NameFormat.HexArgb),
            "pen_width": self._pen_width,
            "opacity": self._opacity,
            "rotation": self._rotation_angle,
        }

    @classmethod
    def deserialize(cls, data: dict[str, Any]) -> BaseAnnotationItem | None:
        """Create an item from serialized data.

        This is a dispatch method — it looks up the correct subclass by
        item_type. Subclasses must register themselves via _register_type().
        """
        item_type = data.get("type", "")
        subclass = _ITEM_REGISTRY.get(item_type)
        if subclass is None:
            return None
        item = subclass._from_data(data)
        return item

    @classmethod
    def _from_data(cls, data: dict[str, Any]) -> BaseAnnotationItem:
        """Reconstruct this specific item type from serialized data.

        Subclasses must override this to restore their geometry/content.
        """
        item = cls()
        item._apply_base_data(data)
        return item

    def _apply_base_data(self, data: dict[str, Any]) -> None:
        """Apply common serialized fields to this item."""
        self.setPos(data.get("x", 0), data.get("y", 0))
        self._pen_color = QColor(data.get("pen_color", "#ffff0000"))
        self._fill_color = QColor(data.get("fill_color", "#00000000"))
        self._pen_width = data.get("pen_width", 3)
        self.item_opacity = data.get("opacity", 1.0)
        self.rotation_angle = data.get("rotation", 0.0)

    # --- Duplication ---

    def clone(self) -> BaseAnnotationItem:
        """Create a duplicate of this item, offset slightly."""
        data = self.serialize()
        data["x"] = data.get("x", 0) + 20
        data["y"] = data.get("y", 0) + 20
        return BaseAnnotationItem.deserialize(data)


# --- Type registry for deserialization ---

_ITEM_REGISTRY: dict[str, type[BaseAnnotationItem]] = {}


def register_item_type(cls: type[BaseAnnotationItem]) -> type[BaseAnnotationItem]:
    """Class decorator to register an annotation item type for deserialization."""
    if cls.item_type:
        _ITEM_REGISTRY[cls.item_type] = cls
    return cls
