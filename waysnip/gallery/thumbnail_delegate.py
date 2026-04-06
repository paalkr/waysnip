"""Custom delegate for gallery thumbnails."""

from __future__ import annotations

from PyQt6.QtCore import QRect, QSize, Qt
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen
from PyQt6.QtWidgets import QStyle, QStyledItemDelegate, QStyleOptionViewItem

from waysnip.gallery.thumbnail_model import ThumbnailRoles

_GRID_W = 220
_GRID_H = 260
_THUMB_SIZE = 200
_MARGIN = (_GRID_W - _THUMB_SIZE) // 2


class ThumbnailDelegate(QStyledItemDelegate):
    def grid_size(self) -> QSize:
        return QSize(_GRID_W, _GRID_H)

    def sizeHint(self, option: QStyleOptionViewItem, index) -> QSize:
        return QSize(_GRID_W, _GRID_H)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = option.rect

        # Selection highlight
        if option.state & QStyle.StateFlag.State_Selected:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#0078d7"))
            painter.setOpacity(0.25)
            painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 6, 6)
            painter.setOpacity(1.0)

        # Thumbnail
        thumb = index.data(Qt.ItemDataRole.DecorationRole)
        if thumb is not None:
            tw, th = thumb.width(), thumb.height()
            tx = rect.x() + (rect.width() - tw) // 2
            ty = rect.y() + _MARGIN

            # Subtle shadow
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(0, 0, 0, 40))
            painter.drawRoundedRect(tx + 2, ty + 2, tw, th, 3, 3)

            # Border
            painter.setPen(QPen(QColor("#555"), 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(tx - 1, ty - 1, tw + 2, th + 2, 3, 3)

            painter.drawPixmap(tx, ty, thumb)

        # Filename
        text_rect = QRect(rect.x() + 4, rect.y() + _MARGIN + _THUMB_SIZE + 4, rect.width() - 8, 18)
        name = index.data(Qt.ItemDataRole.DisplayRole) or ""
        fm = QFontMetrics(option.font)
        elided = fm.elidedText(name, Qt.TextElideMode.ElideMiddle, text_rect.width())
        painter.setPen(QColor("#e0e0e0"))
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignHCenter, elided)

        # Date
        date_val = index.data(ThumbnailRoles.DateRole)
        if date_val is not None:
            date_str = date_val.strftime("%Y-%m-%d %H:%M")
            date_rect = QRect(rect.x() + 4, text_rect.bottom() + 2, rect.width() - 8, 16)
            small_font = QFont(option.font)
            small_font.setPointSize(max(small_font.pointSize() - 2, 7))
            painter.setFont(small_font)
            painter.setPen(QColor("#999"))
            painter.drawText(date_rect, Qt.AlignmentFlag.AlignHCenter, date_str)

        painter.restore()
