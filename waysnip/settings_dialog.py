"""Settings dialog — tabbed preferences UI."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFontComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from waysnip.config import AppConfig
from waysnip.constants import APP_DISPLAY_NAME, APP_VERSION, CONFIG_FILE

if TYPE_CHECKING:
    pass


class _ColorButton(QPushButton):
    """Small push-button that shows a colour swatch and opens a colour picker."""

    color_changed = pyqtSignal(str)

    def __init__(self, initial: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._color = initial
        self.setFixedSize(40, 24)
        self._update_swatch()
        self.clicked.connect(self._pick)

    def color(self) -> str:
        return self._color

    def set_color(self, hex_color: str) -> None:
        self._color = hex_color
        self._update_swatch()

    def _update_swatch(self) -> None:
        self.setStyleSheet(
            f"background-color: {self._color}; border: 1px solid #888; border-radius: 3px;"
        )

    def _pick(self) -> None:
        current = QColor(self._color)
        options = QColorDialog.ColorDialogOption.ShowAlphaChannel
        chosen = QColorDialog.getColor(current, self, "Pick colour", options)
        if chosen.isValid():
            self._color = chosen.name(QColor.NameFormat.HexArgb) if chosen.alpha() < 255 else chosen.name()
            self._update_swatch()
            self.color_changed.emit(self._color)


class SettingsDialog(QDialog):
    """Preferences window with tabbed sections."""

    config_saved = pyqtSignal()

    def __init__(self, config: AppConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"{APP_DISPLAY_NAME} Settings")
        self.setMinimumSize(480, 400)

        self._config = config

        layout = QVBoxLayout(self)
        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)

        self._build_capture_tab()
        self._build_save_tab()
        self._build_editor_tab()
        self._build_tray_tab()
        self._build_about_tab()

        # Button box
        bbox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Apply
        )
        bbox.accepted.connect(self._on_ok)
        bbox.rejected.connect(self.reject)
        apply_btn = bbox.button(QDialogButtonBox.StandardButton.Apply)
        if apply_btn:
            apply_btn.clicked.connect(self._on_apply)
        layout.addWidget(bbox)

    # ---- Tab builders ------------------------------------------------------

    def _build_capture_tab(self) -> None:
        w = QWidget()
        form = QFormLayout(w)

        self._after_capture = QComboBox()
        self._after_capture.addItems([
            "Open editor",
            "Copy to clipboard",
            "Save only",
            "Clipboard + Save",
        ])
        _after_capture_map = {"editor": 0, "clipboard": 1, "save": 2, "clipboard+save": 3}
        self._after_capture.setCurrentIndex(
            _after_capture_map.get(self._config.capture.after_capture, 0)
        )
        form.addRow("After capture:", self._after_capture)

        self._show_cursor = QCheckBox()
        self._show_cursor.setChecked(self._config.capture.show_cursor)
        form.addRow("Show cursor:", self._show_cursor)

        self._magnifier_enabled = QCheckBox()
        self._magnifier_enabled.setChecked(self._config.magnifier.enabled)
        form.addRow("Magnifier enabled:", self._magnifier_enabled)

        self._magnifier_zoom = QSpinBox()
        self._magnifier_zoom.setRange(2, 10)
        self._magnifier_zoom.setValue(self._config.magnifier.zoom)
        form.addRow("Magnifier zoom:", self._magnifier_zoom)

        self._magnifier_size = QSpinBox()
        self._magnifier_size.setRange(50, 300)
        self._magnifier_size.setValue(self._config.magnifier.size)
        form.addRow("Magnifier size:", self._magnifier_size)

        self._tabs.addTab(w, "Capture")

    def _build_save_tab(self) -> None:
        w = QWidget()
        form = QFormLayout(w)

        # Directory row
        dir_layout = QHBoxLayout()
        self._save_dir = QLineEdit(self._config.save.directory)
        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self._browse_save_dir)
        dir_layout.addWidget(self._save_dir)
        dir_layout.addWidget(browse_btn)
        form.addRow("Directory:", dir_layout)

        # Filename pattern
        self._pattern = QLineEdit(self._config.save.pattern)
        form.addRow("Filename pattern:", self._pattern)

        # Live preview
        self._pattern_preview = QLabel()
        self._pattern_preview.setStyleSheet("color: #888;")
        self._update_pattern_preview()
        self._pattern.textChanged.connect(self._update_pattern_preview)
        form.addRow("Preview:", self._pattern_preview)

        # Save mode
        self._save_mode = QComboBox()
        self._save_mode.addItems([
            "Annotated (recommended)",
            "Editable (smaller files)",
        ])
        self._save_mode.setCurrentIndex(0 if self._config.save.mode == "annotated" else 1)
        form.addRow("Save mode:", self._save_mode)

        self._tabs.addTab(w, "Save")

    def _build_editor_tab(self) -> None:
        w = QWidget()
        form = QFormLayout(w)

        self._pen_color = _ColorButton(self._config.editor.default_pen_color)
        form.addRow("Default pen color:", self._pen_color)

        self._fill_color = _ColorButton(self._config.editor.default_fill_color)
        form.addRow("Default fill color:", self._fill_color)

        self._pen_width = QSpinBox()
        self._pen_width.setRange(1, 50)
        self._pen_width.setValue(self._config.editor.default_pen_width)
        form.addRow("Default pen width:", self._pen_width)

        self._font_combo = QFontComboBox()
        self._font_combo.setCurrentFont(self._font_combo.font())
        # Try to match saved font
        from PyQt6.QtGui import QFont

        self._font_combo.setCurrentFont(QFont(self._config.editor.default_font))
        form.addRow("Default font:", self._font_combo)

        self._font_size = QSpinBox()
        self._font_size.setRange(6, 200)
        self._font_size.setValue(self._config.editor.default_font_size)
        form.addRow("Default font size:", self._font_size)

        self._tabs.addTab(w, "Editor")

    def _build_tray_tab(self) -> None:
        w = QWidget()
        form = QFormLayout(w)

        self._tray_enabled = QCheckBox()
        self._tray_enabled.setChecked(self._config.tray.enabled)
        form.addRow("Enable tray icon:", self._tray_enabled)

        self._left_click = QComboBox()
        self._left_click.addItems(["Region", "Window", "Fullscreen", "Gallery"])
        _lc_map = {"region": 0, "window": 1, "fullscreen": 2, "gallery": 3}
        self._left_click.setCurrentIndex(
            _lc_map.get(self._config.tray.left_click_action, 0)
        )
        form.addRow("Left-click action:", self._left_click)

        self._tabs.addTab(w, "Tray")

    def _build_about_tab(self) -> None:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addStretch()

        title = QLabel(f"<b>{APP_DISPLAY_NAME}</b>")
        title.setStyleSheet("font-size: 18px;")
        layout.addWidget(title)

        layout.addWidget(QLabel(f"Version {APP_VERSION}"))
        layout.addWidget(QLabel("Lightweight Wayland screenshot and annotation tool."))
        layout.addSpacing(16)

        config_label = QLabel(f"Configuration file: <code>{CONFIG_FILE}</code>")
        config_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        layout.addWidget(config_label)

        layout.addStretch()
        self._tabs.addTab(w, "About")

    # ---- Helpers -----------------------------------------------------------

    def _browse_save_dir(self) -> None:
        d = QFileDialog.getExistingDirectory(
            self, "Select save directory", self._save_dir.text()
        )
        if d:
            self._save_dir.setText(d)

    def _update_pattern_preview(self) -> None:
        try:
            preview = datetime.now().strftime(self._pattern.text())
        except Exception:
            preview = "(invalid pattern)"
        self._pattern_preview.setText(preview)

    def _collect_values(self) -> None:
        """Write widget values back into the config object."""
        after_map = {0: "editor", 1: "clipboard", 2: "save", 3: "clipboard+save"}
        self._config.capture.after_capture = after_map.get(
            self._after_capture.currentIndex(), "editor"
        )
        self._config.capture.show_cursor = self._show_cursor.isChecked()

        self._config.magnifier.enabled = self._magnifier_enabled.isChecked()
        self._config.magnifier.zoom = self._magnifier_zoom.value()
        self._config.magnifier.size = self._magnifier_size.value()

        self._config.save.directory = self._save_dir.text()
        self._config.save.pattern = self._pattern.text()
        self._config.save.mode = "annotated" if self._save_mode.currentIndex() == 0 else "editable"

        self._config.editor.default_pen_color = self._pen_color.color()
        self._config.editor.default_fill_color = self._fill_color.color()
        self._config.editor.default_pen_width = self._pen_width.value()
        self._config.editor.default_font = self._font_combo.currentFont().family()
        self._config.editor.default_font_size = self._font_size.value()

        self._config.tray.enabled = self._tray_enabled.isChecked()
        lc_map = {0: "region", 1: "window", 2: "fullscreen", 3: "gallery"}
        self._config.tray.left_click_action = lc_map.get(
            self._left_click.currentIndex(), "region"
        )

    def _on_ok(self) -> None:
        self._on_apply()
        self.accept()

    def _on_apply(self) -> None:
        self._collect_values()
        self._config.save_to_disk()
        self.config_saved.emit()
