"""Editor window — main window for annotating screenshots."""

from __future__ import annotations


from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import (
    QAction,
    QCloseEvent,
    QKeyEvent,
    QKeySequence,
    QPixmap,
    QGuiApplication,
)
from PyQt6.QtWidgets import (
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QStatusBar,
    QWidget,
)

from waysnip.config import AppConfig
from waysnip.constants import APP_DISPLAY_NAME
from waysnip.editor.canvas import AnnotationCanvas
from waysnip.editor.scene import AnnotationScene
from waysnip.editor.toolbar import AnnotationToolbar
from waysnip.editor.properties_panel import PropertiesPanel
from waysnip.editor.tools.base import BaseAnnotationItem, BaseTool
from waysnip.editor.tools.select_tool import SelectTool
from waysnip.editor.tools.rectangle import RectangleTool
from waysnip.editor.tools.ellipse import EllipseTool
from waysnip.editor.tools.arrow import ArrowTool
from waysnip.editor.tools.line import LineTool
from waysnip.editor.tools.text import TextTool
from waysnip.editor.tools.numbered_marker import NumberedMarkerTool, NumberedMarkerItem
from waysnip.editor.tools.freehand import FreehandTool
from waysnip.editor.tools.highlight import HighlightTool
from waysnip.editor.tools.blur import BlurTool
from waysnip.editor.tools.crop import CropTool
from waysnip.editor.commands import RemoveItemCommand, AddItemCommand


class EditorWindow(QMainWindow):
    """Main annotation editor window."""

    image_saved = pyqtSignal(str)

    def __init__(self, pixmap: QPixmap, config: AppConfig | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._config = config or AppConfig.load()
        self._saved = False
        self._save_path: str | None = None

        self.setWindowTitle(f"{APP_DISPLAY_NAME} - Editor")
        self.resize(1200, 800)

        # Scene and canvas
        self._scene = AnnotationScene(self)
        self._scene.set_background_pixmap(pixmap)
        self._canvas = AnnotationCanvas(self._scene, self)
        self.setCentralWidget(self._canvas)

        # Tools
        self._tools: dict[str, BaseTool] = {
            "select": SelectTool(),
            "rectangle": RectangleTool(),
            "ellipse": EllipseTool(),
            "arrow": ArrowTool(),
            "line": LineTool(),
            "text": TextTool(),
            "numbered_marker": NumberedMarkerTool(),
            "freehand": FreehandTool(),
            "highlight": HighlightTool(),
            "blur": BlurTool(),
            "crop": CropTool(),
        }

        # Toolbar
        self._toolbar = AnnotationToolbar(self)
        self._toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self._toolbar)
        self._toolbar.tool_changed.connect(self._on_tool_changed)

        # Properties panel
        self._properties = PropertiesPanel(self._config, self)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._properties)
        self._properties.properties_changed.connect(self._on_properties_changed)

        # Menu bar
        self._setup_menus()

        # Status bar
        self._status_bar = QStatusBar(self)
        self.setStatusBar(self._status_bar)
        self._update_status()

        # Listen for selection changes to update properties panel
        self._scene.selectionChanged.connect(self._on_selection_changed)

        # Activate default tool
        self._on_tool_changed("select")

    # --- Menu setup ---

    def _setup_menus(self) -> None:
        menu_bar = self.menuBar()

        # File menu
        file_menu = menu_bar.addMenu("&File")

        save_action = QAction("&Save", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self._save)
        file_menu.addAction(save_action)

        save_as_action = QAction("Save &As...", self)
        save_as_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        save_as_action.triggered.connect(self._save_as)
        file_menu.addAction(save_as_action)

        copy_action = QAction("&Copy to Clipboard", self)
        copy_action.setShortcut(QKeySequence("Ctrl+C"))
        copy_action.triggered.connect(self._copy_to_clipboard)
        file_menu.addAction(copy_action)

        file_menu.addSeparator()

        close_action = QAction("C&lose", self)
        close_action.setShortcut(QKeySequence("Ctrl+W"))
        close_action.triggered.connect(self.close)
        file_menu.addAction(close_action)

        # Edit menu
        edit_menu = menu_bar.addMenu("&Edit")

        undo_action = QAction("&Undo", self)
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        undo_action.triggered.connect(self._scene.undo_stack.undo)
        edit_menu.addAction(undo_action)

        redo_action = QAction("&Redo", self)
        redo_action.setShortcut(QKeySequence("Ctrl+Y"))
        redo_action.triggered.connect(self._scene.undo_stack.redo)
        edit_menu.addAction(redo_action)

        edit_menu.addSeparator()

        select_all_action = QAction("Select &All", self)
        select_all_action.setShortcut(QKeySequence.StandardKey.SelectAll)
        select_all_action.triggered.connect(self._select_all)
        edit_menu.addAction(select_all_action)

        delete_action = QAction("&Delete", self)
        delete_action.setShortcut(QKeySequence.StandardKey.Delete)
        delete_action.triggered.connect(self._delete_selected)
        edit_menu.addAction(delete_action)

        clone_action = QAction("Clo&ne", self)
        clone_action.setShortcut(QKeySequence("Ctrl+D"))
        clone_action.triggered.connect(self._clone_selected)
        edit_menu.addAction(clone_action)

        # View menu
        view_menu = menu_bar.addMenu("&View")

        zoom_in_action = QAction("Zoom &In", self)
        zoom_in_action.setShortcut(QKeySequence.StandardKey.ZoomIn)
        zoom_in_action.triggered.connect(self._zoom_in)
        view_menu.addAction(zoom_in_action)

        zoom_out_action = QAction("Zoom &Out", self)
        zoom_out_action.setShortcut(QKeySequence.StandardKey.ZoomOut)
        zoom_out_action.triggered.connect(self._zoom_out)
        view_menu.addAction(zoom_out_action)

        fit_action = QAction("&Fit to Window", self)
        fit_action.setShortcut(QKeySequence("Ctrl+0"))
        fit_action.triggered.connect(self._canvas.fit_in_view_on_show)
        view_menu.addAction(fit_action)

    # --- Tool switching ---

    def _on_tool_changed(self, name: str) -> None:
        tool = self._tools.get(name)
        if tool:
            self._scene.set_active_tool(tool)
            cursor = tool.cursor_shape
            self._canvas.setCursor(cursor)
            self._properties.set_tool_name(name)
            self._update_status()

    # --- Selection ---

    def _on_selection_changed(self) -> None:
        """Update properties panel to reflect the selected item(s)."""
        from waysnip.editor.tools.blur import BlurItem
        from waysnip.editor.tools.text import TextItem

        selected = [
            item for item in self._scene.selectedItems()
            if isinstance(item, BaseAnnotationItem)
        ]
        if len(selected) == 1:
            item = selected[0]
            # Show appropriate controls based on item type
            is_blur = isinstance(item, BlurItem)
            is_text = isinstance(item, TextItem)
            self._properties._blur_group.setVisible(is_blur)
            self._properties._font_group.setVisible(is_text)
            self._properties._stroke_group.setVisible(not is_blur)
            self._properties._color_group.setVisible(not is_blur)

            # Update panel values to match selected item
            self._properties.set_pen_color(item.pen_color)
            self._properties.set_fill_color(item.fill_color)
            self._properties.set_pen_width(item.pen_width)
            self._properties.set_opacity(item.item_opacity)
            if is_blur:
                self._properties._block_size_spin.setValue(item.block_size)

    # --- Properties ---

    def _on_properties_changed(self, props: dict) -> None:
        """Apply changed properties to selected items and update drawing defaults."""
        # Update the scene's drawing properties so new items use these values
        self._scene.drawing_properties.update(props)

        # Also apply to currently selected items
        for item in self._scene.selectedItems():
            if isinstance(item, BaseAnnotationItem):
                for key, value in props.items():
                    if hasattr(item, key):
                        setattr(item, key, value)

    # --- Actions ---

    def _select_all(self) -> None:
        for item in self._scene.get_all_annotations():
            item.setSelected(True)

    def _delete_selected(self) -> None:
        selected = [
            item for item in self._scene.selectedItems()
            if isinstance(item, BaseAnnotationItem)
        ]
        for item in selected:
            cmd = RemoveItemCommand(self._scene, item)
            self._scene.undo_stack.push(cmd)

        # Renumber markers if any were deleted
        has_markers = any(isinstance(item, NumberedMarkerItem) for item in selected)
        if has_markers:
            NumberedMarkerItem.renumber_all(self._scene)

    def _clone_selected(self) -> None:
        selected = [
            item for item in self._scene.selectedItems()
            if isinstance(item, BaseAnnotationItem)
        ]
        self._scene.clearSelection()
        for item in selected:
            cloned = item.clone()
            if cloned:
                cmd = AddItemCommand(self._scene, cloned)
                self._scene.undo_stack.push(cmd)
                cloned.setSelected(True)

    def _zoom_in(self) -> None:
        self._canvas.zoom_to(self._canvas.zoom_factor * 1.25)

    def _zoom_out(self) -> None:
        self._canvas.zoom_to(self._canvas.zoom_factor / 1.25)

    def _copy_to_clipboard(self) -> None:
        pixmap = self._scene.render_to_pixmap()
        clipboard = QGuiApplication.clipboard()
        if clipboard:
            clipboard.setPixmap(pixmap)
        self._status_bar.showMessage("Copied to clipboard", 2000)

    def _save(self) -> None:
        if self._save_path:
            self._do_save(self._save_path)
        else:
            self._save_as()

    def _save_as(self) -> None:
        save_dir = self._config.get_save_directory()
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Screenshot",
            str(save_dir / "screenshot.png"),
            "PNG Image (*.png);;All Files (*)",
        )
        if path:
            self._do_save(path)

    def _do_save(self, path: str) -> None:
        pixmap = self._scene.render_to_pixmap()
        pixmap.save(path, "PNG")
        self._save_path = path
        self._saved = True
        self.image_saved.emit(path)
        self._status_bar.showMessage(f"Saved to {path}", 3000)

    # --- Status bar ---

    def _update_status(self) -> None:
        bg = self._scene.background_pixmap
        if bg:
            dims = f"{bg.width()}x{bg.height()}"
        else:
            dims = "No image"
        zoom = f"{self._canvas.zoom_factor * 100:.0f}%"
        tool_name = self._toolbar.current_tool_name()
        self._status_bar.showMessage(f"{dims} | Zoom: {zoom} | Tool: {tool_name}")

    # --- Key events ---

    def keyPressEvent(self, event: QKeyEvent) -> None:
        # Handle crop confirm/cancel
        active = self._scene.active_tool
        if isinstance(active, CropTool):
            if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
                if active.has_crop_selection:
                    active.confirm(self._scene)
                    self._update_status()
                    event.accept()
                    return
            elif event.key() == Qt.Key.Key_Escape:
                active._cancel(self._scene)
                event.accept()
                return

        # Delete key
        if event.key() == Qt.Key.Key_Delete or event.key() == Qt.Key.Key_Backspace:
            if not isinstance(active, (TextTool,)):  # Don't intercept during text editing
                self._delete_selected()
                event.accept()
                return

        super().keyPressEvent(event)

    # --- Close ---

    def closeEvent(self, event: QCloseEvent) -> None:
        annotations = self._scene.get_all_annotations()
        if annotations and not self._saved:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved annotations. Close anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return
        event.accept()
