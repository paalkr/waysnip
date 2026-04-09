"""Text annotation tool and item."""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPainter, QColor, QFont, QTextCursor
from PyQt6.QtWidgets import (
    QGraphicsScene,
    QGraphicsSceneMouseEvent,
    QGraphicsTextItem,
    QStyleOptionGraphicsItem,
    QWidget,
)

from waysnip.editor.tools.base import BaseTool, BaseAnnotationItem, register_item_type
from waysnip.constants import (
    HANDLE_HALF,
    DEFAULT_FONT_FAMILY,
    DEFAULT_FONT_SIZE,
)


@register_item_type
class TextItem(BaseAnnotationItem):
    """A text annotation with inline editing support."""

    item_type = "text"

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._font_family: str = DEFAULT_FONT_FAMILY
        self._font_size: int = DEFAULT_FONT_SIZE
        self._text_color = QColor(255, 255, 255)
        self._background_color = QColor(0, 0, 0, 0)
        self._text: str = ""
        self._text_item: QGraphicsTextItem | None = None
        self._editing: bool = False
        # Override default pen color — text items primarily use text_color
        self._pen_color = QColor(255, 255, 255)

    def apply_drawing_properties(self, props: dict) -> None:
        """Apply properties, mapping pen_color to text_color and handling font."""
        super().apply_drawing_properties(props)
        if "pen_color" in props:
            color = props["pen_color"]
            self._text_color = QColor(color) if isinstance(color, str) else color
        if "font_family" in props:
            self._font_family = props["font_family"]
        if "font_size" in props:
            self._font_size = max(6, props["font_size"])
        self._ensure_text_item()

    @property
    def font_family(self) -> str:
        return self._font_family

    @font_family.setter
    def font_family(self, value: str) -> None:
        self._font_family = value
        self._apply_font()
        self.update()

    @property
    def font_size(self) -> int:
        return self._font_size

    @font_size.setter
    def font_size(self, value: int) -> None:
        self._font_size = max(6, value)
        self._apply_font()
        self.update()

    @property
    def text_color(self) -> QColor:
        return self._text_color

    @text_color.setter
    def text_color(self, color: QColor) -> None:
        self._text_color = color
        if self._text_item:
            self._text_item.setDefaultTextColor(color)
        self.update()

    @property
    def background_color(self) -> QColor:
        return self._background_color

    @background_color.setter
    def background_color(self, color: QColor) -> None:
        self._background_color = color
        self.update()

    @property
    def text(self) -> str:
        if self._text_item:
            return self._text_item.toPlainText()
        return self._text

    def _apply_font(self) -> None:
        if self._text_item:
            font = QFont(self._font_family, self._font_size)
            self._text_item.setFont(font)

    def _ensure_text_item(self) -> QGraphicsTextItem:
        if self._text_item is None:
            self._text_item = QGraphicsTextItem(self)
            self._text_item.setDefaultTextColor(self._text_color)
            font = QFont(self._font_family, self._font_size)
            self._text_item.setFont(font)
            if self._text:
                self._text_item.setPlainText(self._text)
        return self._text_item

    def start_editing(self) -> None:
        """Enable inline text editing."""
        text_item = self._ensure_text_item()
        text_item.setTextInteractionFlags(Qt.TextInteractionFlag.TextEditorInteraction)
        text_item.setFocus()
        cursor = text_item.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)
        text_item.setTextCursor(cursor)
        self._editing = True

    def stop_editing(self) -> None:
        """Disable inline text editing."""
        if self._text_item:
            self._text_item.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
            self._text_item.clearFocus()
            self._text = self._text_item.toPlainText()
        self._editing = False

    def _content_rect(self) -> QRectF:
        text_item = self._ensure_text_item()
        br = text_item.boundingRect()
        return QRectF(0, 0, br.width(), br.height())

    def boundingRect(self) -> QRectF:
        margin = HANDLE_HALF
        cr = self._content_rect()
        return cr.adjusted(-margin, -margin, margin, margin)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget | None = None) -> None:
        # Draw background if set
        if self._background_color.alpha() > 0:
            painter.setBrush(self._background_color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(self._content_rect())
        # The QGraphicsTextItem child handles text rendering

    def serialize(self) -> dict[str, Any]:
        data = super().serialize()
        data.update({
            "text": self.text,
            "font_family": self._font_family,
            "font_size": self._font_size,
            "text_color": self._text_color.name(QColor.NameFormat.HexArgb),
            "background_color": self._background_color.name(QColor.NameFormat.HexArgb),
        })
        return data

    @classmethod
    def _from_data(cls, data: dict[str, Any]) -> TextItem:
        item = cls()
        item._apply_base_data(data)
        item._text = data.get("text", "")
        item._font_family = data.get("font_family", DEFAULT_FONT_FAMILY)
        item._font_size = data.get("font_size", DEFAULT_FONT_SIZE)
        item._text_color = QColor(data.get("text_color", "#ffffffff"))
        item._background_color = QColor(data.get("background_color", "#00000000"))
        item._ensure_text_item()
        return item

    def mouseDoubleClickEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """Double-click to start editing."""
        self.start_editing()
        event.accept()

    def focusOutEvent(self, event) -> None:
        """Stop editing when focus is lost."""
        self.stop_editing()
        super().focusOutEvent(event)


class TextTool(BaseTool):
    """Tool for placing text annotations."""

    name = "text"
    icon = "text"
    shortcut = "T"
    cursor_shape = Qt.CursorShape.IBeamCursor

    def __init__(self) -> None:
        self._current_item: TextItem | None = None

    def mouse_press(self, scene: QGraphicsScene, event: QGraphicsSceneMouseEvent) -> None:
        # If we have an active text item being edited, finish it
        if self._current_item is not None:
            self._current_item.stop_editing()
            if not self._current_item.text.strip():
                scene.removeItem(self._current_item)
            self._current_item = None

        scene.clearSelection()
        pos = event.scenePos()

        # Check if clicking on an existing text item to re-edit
        item_at = scene.itemAt(pos, scene.views()[0].transform() if scene.views() else __import__("PyQt6.QtGui", fromlist=["QTransform"]).QTransform())
        if isinstance(item_at, TextItem):
            item_at.start_editing()
            self._current_item = item_at
            event.accept()
            return
        # Also check parent (the QGraphicsTextItem child)
        if item_at and isinstance(item_at.parentItem(), TextItem):
            parent = item_at.parentItem()
            parent.start_editing()
            self._current_item = parent
            event.accept()
            return

        # Create new text item
        item = TextItem()
        item.apply_drawing_properties(scene.drawing_properties)
        item.setPos(pos)
        item._ensure_text_item()

        from waysnip.editor.commands import AddItemCommand

        cmd = AddItemCommand(scene, item)
        if hasattr(scene, "undo_stack"):
            scene.undo_stack.push(cmd)
        else:
            scene.addItem(item)

        item.start_editing()
        self._current_item = item
        event.accept()

    def mouse_move(self, scene: QGraphicsScene, event: QGraphicsSceneMouseEvent) -> None:
        event.accept()

    def mouse_release(self, scene: QGraphicsScene, event: QGraphicsSceneMouseEvent) -> None:
        event.accept()

    def deactivate(self, scene: QGraphicsScene) -> None:
        if self._current_item is not None:
            self._current_item.stop_editing()
            if not self._current_item.text.strip():
                scene.removeItem(self._current_item)
            self._current_item = None
