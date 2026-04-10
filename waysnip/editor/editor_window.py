"""Editor window — main window for annotating screenshots."""

from __future__ import annotations


from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import (
    QAction,
    QCloseEvent,
    QColor,
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

from typing import Any

from waysnip.config import AppConfig
from waysnip.constants import APP_DISPLAY_NAME
from waysnip.editor.canvas import AnnotationCanvas
from waysnip.editor.scene import AnnotationScene
from waysnip.editor.tool_properties import ToolPropertyStore
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
from waysnip.editor.commands import RemoveItemCommand, AddItemCommand, ReorderItemCommand


class EditorWindow(QMainWindow):
    """Main annotation editor window."""

    image_saved = pyqtSignal(str)

    def __init__(
        self,
        pixmap: QPixmap,
        config: AppConfig | None = None,
        parent: QWidget | None = None,
        annotations: list[dict] | None = None,
        save_path: str | None = None,
    ) -> None:
        super().__init__(parent)
        self._config = config or AppConfig.load()
        self._saved = save_path is not None
        self._save_path: str | None = save_path

        self.setWindowTitle(f"{APP_DISPLAY_NAME} - Editor")
        self._size_window_to_image(pixmap)

        # Scene and canvas
        self._scene = AnnotationScene(self)
        self._scene.set_background_pixmap(pixmap)

        # Per-tool property store (each editor window gets its own copy)
        self._tool_store = ToolPropertyStore.load()
        self._scene.set_tool_property_store(self._tool_store)
        self._current_tool_name: str = "select"
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

        # Update status bar when zoom changes
        self._canvas.zoom_changed.connect(self._on_zoom_changed)

        # Restore annotations if provided (re-editing a saved image)
        if annotations:
            self._restore_annotations(annotations)

        # Activate default tool
        self._on_tool_changed("select")

    # --- Window sizing ---

    def _size_window_to_image(self, pixmap: QPixmap) -> None:
        """Resize the editor window to fit the image at 100% if possible."""
        # Approximate chrome overhead (toolbar, statusbar, menubar, properties panel).
        chrome_w = 280
        chrome_h = 100
        min_w, min_h = 900, 500

        ideal_w = pixmap.width() + chrome_w
        ideal_h = pixmap.height() + chrome_h

        screen = self.screen()
        if screen is not None:
            avail = screen.availableGeometry()
            max_w = int(avail.width() * 0.92)
            max_h = int(avail.height() * 0.92)
        else:
            max_w, max_h = 1920, 1080

        w = max(min_w, min(ideal_w, max_w))
        h = max(min_h, min(ideal_h, max_h))
        self.resize(w, h)

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

        edit_menu.addSeparator()

        # Layer ordering
        bring_front_action = QAction("Bring to &Front", self)
        bring_front_action.setShortcut(QKeySequence("Ctrl+Shift+]"))
        bring_front_action.triggered.connect(self._bring_to_front)
        edit_menu.addAction(bring_front_action)

        send_back_action = QAction("Send to &Back", self)
        send_back_action.setShortcut(QKeySequence("Ctrl+Shift+["))
        send_back_action.triggered.connect(self._send_to_back)
        edit_menu.addAction(send_back_action)

        move_up_action = QAction("Move &Up", self)
        move_up_action.setShortcut(QKeySequence("Ctrl+]"))
        move_up_action.triggered.connect(self._move_up)
        edit_menu.addAction(move_up_action)

        move_down_action = QAction("Move Do&wn", self)
        move_down_action.setShortcut(QKeySequence("Ctrl+["))
        move_down_action.triggered.connect(self._move_down)
        edit_menu.addAction(move_down_action)

        edit_menu.addSeparator()

        reset_tools_action = QAction("Reset Tool &Defaults", self)
        reset_tools_action.triggered.connect(self._reset_tool_defaults)
        edit_menu.addAction(reset_tools_action)

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

        actual_size_action = QAction("&Actual Size (100%)", self)
        actual_size_action.setShortcut(QKeySequence("Ctrl+1"))
        actual_size_action.triggered.connect(self._canvas.zoom_to_actual)
        view_menu.addAction(actual_size_action)

        fit_action = QAction("&Fit to Window", self)
        fit_action.setShortcut(QKeySequence("Ctrl+0"))
        fit_action.triggered.connect(self._canvas.fit_in_view)
        view_menu.addAction(fit_action)

    # --- Tool switching ---

    def _on_tool_changed(self, name: str) -> None:
        tool = self._tools.get(name)
        if tool:
            # Clear selection when switching away from select tool so that
            # selected items don't intercept mouse events meant for the new tool.
            if name != "select":
                self._scene.clearSelection()
            self._current_tool_name = name
            self._scene.set_active_tool(tool)
            self._scene.set_active_tool_name(name)
            cursor = tool.cursor_shape
            self._canvas.setCursor(cursor)
            self._properties.set_tool_name(name)
            self._load_tool_properties_into_panel(name)
            self._update_status()

    def _load_tool_properties_into_panel(self, tool_name: str) -> None:
        """Push the stored properties for a tool into the properties panel widgets."""
        props = self._tool_store.get(tool_name)
        if not props:
            return
        self._properties.blockSignals(True)
        try:
            if "pen_color" in props:
                self._properties.set_pen_color(QColor(props["pen_color"]))
            if "fill_color" in props:
                self._properties.set_fill_color(QColor(props["fill_color"]))
            if "pen_width" in props:
                self._properties.set_pen_width(props["pen_width"])
            if "item_opacity" in props:
                self._properties.set_opacity(props["item_opacity"])
            if "font_family" in props:
                self._properties.set_font_family(props["font_family"])
            if "font_size" in props:
                self._properties.set_font_size(props["font_size"])
            if "block_size" in props:
                self._properties.set_block_size(props["block_size"])
        finally:
            self._properties.blockSignals(False)

    # --- Annotation restoration ---

    def _restore_annotations(self, annotations: list[dict]) -> None:
        """Reconstruct annotation items from serialized data."""
        # Ensure all item types are registered by importing the tools package
        import waysnip.editor.tools  # noqa: F401

        for data in annotations:
            item = BaseAnnotationItem.deserialize(data)
            if item is not None:
                self._scene.addItem(item)

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

            # Update panel values to match selected item.
            # Block signals to avoid feedback loops that deselect the item.
            self._properties.blockSignals(True)
            self._properties.set_pen_color(item.pen_color)
            self._properties.set_fill_color(item.fill_color)
            self._properties.set_pen_width(item.pen_width)
            self._properties.set_opacity(item.item_opacity)
            if is_blur:
                self._properties._block_size_spin.setValue(item.block_size)
            self._properties.blockSignals(False)

    # --- Properties ---

    def _on_properties_changed(self, props: dict) -> None:
        """Apply changed properties to selected items and update per-tool defaults."""
        # Convert QColor values to hex strings for storage
        store_props: dict[str, Any] = {}
        for k, v in props.items():
            if isinstance(v, QColor):
                store_props[k] = v.name(QColor.NameFormat.HexArgb)
            else:
                store_props[k] = v
        self._tool_store.update(self._current_tool_name, store_props)

        # Also apply to currently selected items
        for item in self._scene.selectedItems():
            if isinstance(item, BaseAnnotationItem):
                for key, value in props.items():
                    if hasattr(item, key):
                        setattr(item, key, value)

    def _reset_tool_defaults(self) -> None:
        """Reset all tool drawing properties to code defaults."""
        self._tool_store.reset_all()
        self._load_tool_properties_into_panel(self._current_tool_name)

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

    # --- Layer ordering ---

    def _get_single_reorderable(self) -> BaseAnnotationItem | None:
        """Return the single selected non-blur item, or None."""
        from waysnip.editor.tools.blur import BlurItem
        selected = [
            item for item in self._scene.selectedItems()
            if isinstance(item, BaseAnnotationItem) and not isinstance(item, BlurItem)
        ]
        return selected[0] if len(selected) == 1 else None

    def _bring_to_front(self) -> None:
        item = self._get_single_reorderable()
        if item is None:
            return
        new_z = self._scene.bring_to_front(item)
        if new_z is not None:
            cmd = ReorderItemCommand(self._scene, item, item.zValue(), new_z)
            self._scene.undo_stack.push(cmd)

    def _send_to_back(self) -> None:
        item = self._get_single_reorderable()
        if item is None:
            return
        new_z = self._scene.send_to_back(item)
        if new_z is not None:
            cmd = ReorderItemCommand(self._scene, item, item.zValue(), new_z)
            self._scene.undo_stack.push(cmd)

    def _move_up(self) -> None:
        item = self._get_single_reorderable()
        if item is None:
            return
        result = self._scene.move_up(item)
        if result is not None:
            new_z, other, other_new_z = result
            cmd = ReorderItemCommand(
                self._scene, item, item.zValue(), new_z,
                other_item=other, other_old_z=other.zValue(), other_new_z=other_new_z,
            )
            self._scene.undo_stack.push(cmd)

    def _move_down(self) -> None:
        item = self._get_single_reorderable()
        if item is None:
            return
        result = self._scene.move_down(item)
        if result is not None:
            new_z, other, other_new_z = result
            cmd = ReorderItemCommand(
                self._scene, item, item.zValue(), new_z,
                other_item=other, other_old_z=other.zValue(), other_new_z=other_new_z,
            )
            self._scene.undo_stack.push(cmd)

    def _zoom_in(self) -> None:
        self._canvas.zoom_to(self._canvas.zoom_factor * 1.25)

    def _zoom_out(self) -> None:
        self._canvas.zoom_to(self._canvas.zoom_factor / 1.25)

    def _on_zoom_changed(self, factor: float) -> None:
        self._update_status()

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
            self._save_auto()

    def _save_auto(self) -> None:
        """Save using config pattern (no dialog)."""
        from waysnip.save import save_screenshot

        flattened = self._scene.render_to_pixmap()
        annotations = [item.serialize() for item in self._scene.get_all_annotations()]
        original = self._scene.background_pixmap

        path = save_screenshot(flattened, annotations, original, self._config)
        self._save_path = str(path)
        self._saved = True
        self.image_saved.emit(str(path))

        # Copy to clipboard if enabled
        if self._config.editor.copy_on_save:
            from waysnip.capture.clipboard import ClipboardManager
            ClipboardManager.copy_image_from_pixmap(flattened)
            self._status_bar.showMessage(f"Saved to {path.name} (copied to clipboard)", 3000)
        else:
            self._status_bar.showMessage(f"Saved to {path.name}", 3000)

    def _save_as(self) -> None:
        from datetime import datetime

        save_dir = self._config.get_save_directory()
        default_name = datetime.now().strftime(self._config.save.pattern)
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Screenshot",
            str(save_dir / default_name),
            "PNG Image (*.png);;All Files (*)",
        )
        if path:
            self._do_save(path)

    def _do_save(self, path: str) -> None:
        """Save to a specific path (from Save As dialog)."""
        from pathlib import Path as _Path

        flattened = self._scene.render_to_pixmap()
        annotations = [item.serialize() for item in self._scene.get_all_annotations()]
        original = self._scene.background_pixmap

        # Save with metadata embedding
        image = flattened.toImage()
        import json
        from waysnip.constants import META_KEY_ANNOTATIONS, META_KEY_ORIGINAL
        if annotations:
            image.setText(META_KEY_ANNOTATIONS, json.dumps(annotations))
        if original and self._config.save.mode == "annotated":
            from waysnip.save import _pixmap_to_base64
            image.setText(META_KEY_ORIGINAL, _pixmap_to_base64(original))
        image.save(path, "PNG")

        self._save_path = path
        self._saved = True
        self.image_saved.emit(path)

        if self._config.editor.copy_on_save:
            from waysnip.capture.clipboard import ClipboardManager
            ClipboardManager.copy_image_from_pixmap(flattened)
            self._status_bar.showMessage(f"Saved to {_Path(path).name} (copied to clipboard)", 3000)
        else:
            self._status_bar.showMessage(f"Saved to {_Path(path).name}", 3000)

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
        self._tool_store.save()
        event.accept()
