"""Gallery window — browse and manage saved screenshots."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFileDialog,
    QListView,
    QMainWindow,
    QMenu,
    QMessageBox,
    QToolBar,
)

from waysnip.constants import APP_DISPLAY_NAME
from waysnip.gallery.thumbnail_delegate import ThumbnailDelegate
from waysnip.gallery.thumbnail_model import ThumbnailModel, ThumbnailRoles

if TYPE_CHECKING:
    from PyQt6.QtCore import QModelIndex, QPoint

    from waysnip.config import AppConfig


class GalleryWindow(QMainWindow):
    def __init__(self, config: AppConfig, parent=None) -> None:
        super().__init__(parent)
        self._config = config
        self.setWindowTitle(f"{APP_DISPLAY_NAME} Gallery")
        self.resize(800, 600)

        self._save_dir = Path(config.save.directory).expanduser()

        # Model / View
        self._model = ThumbnailModel(self._save_dir)
        self._delegate = ThumbnailDelegate()

        self._view = QListView()
        self._view.setModel(self._model)
        self._view.setItemDelegate(self._delegate)
        self._view.setViewMode(QListView.ViewMode.IconMode)
        self._view.setResizeMode(QListView.ResizeMode.Adjust)
        self._view.setGridSize(self._delegate.grid_size())
        self._view.setUniformItemSizes(True)
        self._view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._view.customContextMenuRequested.connect(self._context_menu)
        self._view.doubleClicked.connect(self._open_in_editor)
        self.setCentralWidget(self._view)

        # Toolbar
        tb = QToolBar()
        tb.setMovable(False)
        tb.addAction("Refresh", self._refresh)
        tb.addAction("Open folder", self._open_folder)
        tb.addAction("Settings", self._open_settings)
        self.addToolBar(tb)

        # Status bar
        self._update_status()

        # File watcher
        from PyQt6.QtCore import QFileSystemWatcher

        self._watcher = QFileSystemWatcher([str(self._save_dir)], self)
        self._watcher.directoryChanged.connect(self._refresh)

    # ---- Actions -----------------------------------------------------------

    def refresh(self) -> None:
        """Refresh the gallery (public — called by app when editor saves)."""
        self._model.refresh()
        self._update_status()

    def _refresh(self) -> None:
        self.refresh()

    def _open_folder(self) -> None:
        subprocess.Popen(["xdg-open", str(self._save_dir)])

    def _open_settings(self) -> None:
        # Defer to the app singleton if reachable, otherwise no-op.
        from waysnip.settings_dialog import SettingsDialog

        dlg = SettingsDialog(self._config, self)
        dlg.exec()

    def _update_status(self) -> None:
        count = self._model.rowCount()
        self.statusBar().showMessage(f"{count} screenshot{'s' if count != 1 else ''}")

    # ---- Context menu ------------------------------------------------------

    def _context_menu(self, pos: QPoint) -> None:
        idx = self._view.indexAt(pos)
        if not idx.isValid():
            return

        path_str = idx.data(ThumbnailRoles.PathRole)
        if not path_str:
            return
        path = Path(path_str)

        menu = QMenu(self)
        menu.addAction("Copy image to clipboard", lambda: self._copy_to_clipboard(path))
        menu.addAction("Open in editor", lambda: self._open_in_editor(idx))
        menu.addAction("Open with default app", lambda: subprocess.Popen(["xdg-open", str(path)]))
        menu.addAction("Reveal in file manager", lambda: subprocess.Popen(["xdg-open", str(path.parent)]))
        menu.addSeparator()
        menu.addAction("Copy filename", lambda: QApplication.clipboard().setText(path.name))
        menu.addAction("Copy full path", lambda: QApplication.clipboard().setText(str(path)))
        menu.addSeparator()
        menu.addAction("Flatten image", lambda: self._flatten(path, in_place=True))
        menu.addAction("Save flattened copy", lambda: self._flatten(path, in_place=False))
        menu.addSeparator()
        menu.addAction("Delete", lambda: self._delete(path))

        menu.exec(self._view.viewport().mapToGlobal(pos))

    # ---- Item operations ---------------------------------------------------

    @staticmethod
    def _copy_to_clipboard(path: Path) -> None:
        pm = QPixmap(str(path))
        if not pm.isNull():
            QApplication.clipboard().setPixmap(pm)

    def _open_in_editor(self, index: QModelIndex) -> None:
        path_str = index.data(ThumbnailRoles.PathRole)
        if not path_str:
            return
        from pathlib import Path as _Path

        from waysnip.editor.editor_window import EditorWindow
        from waysnip.save import load_annotations

        file_path = _Path(path_str)

        # Try to load annotation metadata from the PNG
        original_pm, annotations = load_annotations(file_path)

        if original_pm and not original_pm.isNull() and annotations:
            # Has metadata — open with original background + editable annotations
            pm = original_pm
        else:
            # No metadata — open as a flat image
            pm = QPixmap(path_str)
            annotations = None

        if pm.isNull():
            return

        win = EditorWindow(pm, self._config, annotations=annotations, save_path=path_str)
        # Keep reference so window isn't garbage collected
        if not hasattr(self, "_editor_windows"):
            self._editor_windows = []
        self._editor_windows.append(win)
        win.destroyed.connect(lambda: self._editor_windows.remove(win) if win in self._editor_windows else None)
        win.show()

    def _flatten(self, path: Path, *, in_place: bool) -> None:
        """Flatten annotations into the image (strip metadata layers)."""
        pm = QPixmap(str(path))
        if pm.isNull():
            return
        if in_place:
            pm.save(str(path), "PNG")
        else:
            dest, _ = QFileDialog.getSaveFileName(
                self, "Save flattened copy", str(path.parent / f"flat_{path.name}"), "PNG (*.png)"
            )
            if dest:
                pm.save(dest, "PNG")

    def _delete(self, path: Path) -> None:
        reply = QMessageBox.question(
            self,
            "Delete screenshot",
            f"Delete {path.name}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            path.unlink(missing_ok=True)
            self._refresh()
