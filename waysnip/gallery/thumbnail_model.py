"""Thumbnail data model for the gallery view."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QAbstractListModel, QModelIndex, QSize, Qt
from PyQt6.QtGui import QPixmap


class ThumbnailRoles:
    """Custom item-data roles."""

    PathRole = Qt.ItemDataRole.UserRole + 1
    DateRole = Qt.ItemDataRole.UserRole + 2


class _Item:
    """Cached information about one screenshot file."""

    __slots__ = ("path", "name", "modified", "_thumbnail")

    def __init__(self, path: Path) -> None:
        self.path = path
        self.name = path.name
        self.modified = datetime.fromtimestamp(path.stat().st_mtime)
        self._thumbnail: QPixmap | None = None

    def thumbnail(self) -> QPixmap:
        if self._thumbnail is None:
            pm = QPixmap(str(self.path))
            if pm.isNull():
                self._thumbnail = QPixmap(200, 200)
                self._thumbnail.fill(Qt.GlobalColor.darkGray)
            else:
                self._thumbnail = pm.scaled(
                    QSize(200, 200),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
        return self._thumbnail


class ThumbnailModel(QAbstractListModel):
    def __init__(self, directory: Path, parent=None) -> None:
        super().__init__(parent)
        self._dir = directory
        self._items: list[_Item] = []
        self.refresh()

    def refresh(self) -> None:
        self.beginResetModel()
        self._items.clear()
        if self._dir.is_dir():
            for p in sorted(self._dir.rglob("*.png"), key=lambda p: p.stat().st_mtime, reverse=True):
                self._items.append(_Item(p))
        self.endResetModel()

    # ---- QAbstractListModel interface --------------------------------------

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._items)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() >= len(self._items):
            return None

        item = self._items[index.row()]

        if role == Qt.ItemDataRole.DisplayRole:
            return item.name
        if role == Qt.ItemDataRole.DecorationRole:
            return item.thumbnail()
        if role == Qt.ItemDataRole.ToolTipRole:
            return f"{item.path}\n{item.modified:%Y-%m-%d %H:%M:%S}"
        if role == ThumbnailRoles.PathRole:
            return str(item.path)
        if role == ThumbnailRoles.DateRole:
            return item.modified
        return None
