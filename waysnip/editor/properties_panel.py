"""Properties panel — color, width, opacity, and font controls."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QColor, QPixmap, QPainter, QIcon
from PyQt6.QtWidgets import (
    QDockWidget,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QSlider,
    QPushButton,
    QColorDialog,
    QFontComboBox,
    QGroupBox,
)

from waysnip.config import AppConfig


def _color_icon(color: QColor, size: int = 20) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pixmap)
    painter.setBrush(color)
    painter.setPen(QColor(80, 80, 80))
    painter.drawRect(0, 0, size - 1, size - 1)
    painter.end()
    return QIcon(pixmap)


class _ColorButton(QPushButton):
    """A button that shows a color and opens a color dialog on click."""

    color_changed = pyqtSignal(QColor)

    def __init__(self, color: QColor, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._color = color
        self.setFixedSize(28, 28)
        self._update_icon()
        self.clicked.connect(self._pick_color)

    @property
    def color(self) -> QColor:
        return self._color

    @color.setter
    def color(self, c: QColor) -> None:
        self._color = c
        self._update_icon()

    def _update_icon(self) -> None:
        self.setIcon(_color_icon(self._color, 20))
        self.setIconSize(self.size())

    def _pick_color(self) -> None:
        dlg = QColorDialog(self._color, self)
        dlg.setOption(QColorDialog.ColorDialogOption.ShowAlphaChannel, True)
        if dlg.exec():
            self._color = dlg.selectedColor()
            self._update_icon()
            self.color_changed.emit(self._color)


class _RecentColorsRow(QWidget):
    """Row of clickable recent color swatches."""

    color_picked = pyqtSignal(QColor)

    def __init__(self, colors: list[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(2)
        self._buttons: list[QPushButton] = []
        self._colors = colors
        self._rebuild()

    def _rebuild(self) -> None:
        # Clear existing
        for btn in self._buttons:
            self._layout.removeWidget(btn)
            btn.deleteLater()
        self._buttons.clear()

        for hex_color in self._colors[:8]:
            btn = QPushButton()
            btn.setFixedSize(20, 20)
            color = QColor(hex_color)
            btn.setIcon(_color_icon(color, 16))
            btn.setIconSize(btn.size())
            btn.setFlat(True)
            btn.clicked.connect(lambda checked, c=color: self.color_picked.emit(c))
            self._layout.addWidget(btn)
            self._buttons.append(btn)

        self._layout.addStretch()

    def update_colors(self, colors: list[str]) -> None:
        self._colors = colors
        self._rebuild()


class PropertiesPanel(QDockWidget):
    """Right-side dock widget for editing annotation properties."""

    properties_changed = pyqtSignal(dict)

    def __init__(self, config: AppConfig, parent: QWidget | None = None) -> None:
        super().__init__("Properties", parent)
        self._config = config
        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.setMinimumWidth(200)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(8)

        # --- Colors ---
        self._color_group = QGroupBox("Colors")
        color_group = self._color_group
        color_layout = QVBoxLayout(color_group)

        pen_row = QHBoxLayout()
        pen_row.addWidget(QLabel("Pen:"))
        self._pen_color_btn = _ColorButton(QColor(config.editor.default_pen_color))
        self._pen_color_btn.color_changed.connect(self._on_pen_color_changed)
        pen_row.addWidget(self._pen_color_btn)
        pen_row.addStretch()
        color_layout.addLayout(pen_row)

        fill_row = QHBoxLayout()
        fill_row.addWidget(QLabel("Fill:"))
        self._fill_color_btn = _ColorButton(QColor(config.editor.default_fill_color))
        self._fill_color_btn.color_changed.connect(self._on_fill_color_changed)
        fill_row.addWidget(self._fill_color_btn)
        fill_row.addStretch()
        color_layout.addLayout(fill_row)

        # Recent colors
        self._recent_row = _RecentColorsRow(config.editor.recent_colors)
        self._recent_row.color_picked.connect(self._on_recent_color_picked)
        color_layout.addWidget(QLabel("Recent:"))
        color_layout.addWidget(self._recent_row)

        layout.addWidget(color_group)

        # --- Line ---
        self._stroke_group = QGroupBox("Stroke")
        line_group = self._stroke_group
        line_layout = QVBoxLayout(line_group)

        width_row = QHBoxLayout()
        width_row.addWidget(QLabel("Width:"))
        self._width_spin = QSpinBox()
        self._width_spin.setRange(1, 50)
        self._width_spin.setValue(config.editor.default_pen_width)
        self._width_spin.valueChanged.connect(self._on_width_changed)
        width_row.addWidget(self._width_spin)
        line_layout.addLayout(width_row)

        opacity_row = QHBoxLayout()
        opacity_row.addWidget(QLabel("Opacity:"))
        self._opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self._opacity_slider.setRange(0, 100)
        self._opacity_slider.setValue(100)
        self._opacity_slider.valueChanged.connect(self._on_opacity_changed)
        opacity_row.addWidget(self._opacity_slider)
        self._opacity_label = QLabel("100%")
        self._opacity_label.setFixedWidth(36)
        opacity_row.addWidget(self._opacity_label)
        line_layout.addLayout(opacity_row)

        layout.addWidget(line_group)

        # --- Font (shown only for text tool) ---
        self._font_group = QGroupBox("Font")
        font_layout = QVBoxLayout(self._font_group)

        family_row = QHBoxLayout()
        family_row.addWidget(QLabel("Family:"))
        self._font_combo = QFontComboBox()
        self._font_combo.setCurrentFont(
            __import__("PyQt6.QtGui", fromlist=["QFont"]).QFont(config.editor.default_font)
        )
        self._font_combo.currentFontChanged.connect(self._on_font_changed)
        family_row.addWidget(self._font_combo)
        font_layout.addLayout(family_row)

        size_row = QHBoxLayout()
        size_row.addWidget(QLabel("Size:"))
        self._font_size_spin = QSpinBox()
        self._font_size_spin.setRange(6, 200)
        self._font_size_spin.setValue(config.editor.default_font_size)
        self._font_size_spin.valueChanged.connect(self._on_font_size_changed)
        size_row.addWidget(self._font_size_spin)
        font_layout.addLayout(size_row)

        layout.addWidget(self._font_group)
        self._font_group.setVisible(False)

        # --- Pixelation (shown only for blur tool) ---
        self._blur_group = QGroupBox("Pixelation")
        blur_layout = QVBoxLayout(self._blur_group)

        block_row = QHBoxLayout()
        block_row.addWidget(QLabel("Block size:"))
        self._block_size_spin = QSpinBox()
        self._block_size_spin.setRange(2, 50)
        self._block_size_spin.setValue(10)
        self._block_size_spin.setSuffix(" px")
        self._block_size_spin.setToolTip("Larger = more pixelated")
        self._block_size_spin.valueChanged.connect(self._on_block_size_changed)
        block_row.addWidget(self._block_size_spin)
        blur_layout.addLayout(block_row)

        layout.addWidget(self._blur_group)
        self._blur_group.setVisible(False)

        layout.addStretch()
        self.setWidget(container)

    # --- Public API ---

    def set_tool_name(self, name: str) -> None:
        """Show/hide tool-specific controls based on the active tool."""
        self._font_group.setVisible(name == "text")
        self._blur_group.setVisible(name == "blur")
        # Hide stroke/color controls for pixelate — it doesn't use them
        self._stroke_group.setVisible(name != "blur")
        self._color_group.setVisible(name != "blur")

    def set_pen_color(self, color: QColor) -> None:
        self._pen_color_btn.color = color

    def set_fill_color(self, color: QColor) -> None:
        self._fill_color_btn.color = color

    def set_pen_width(self, width: int) -> None:
        self._width_spin.setValue(width)

    def set_opacity(self, opacity: float) -> None:
        self._opacity_slider.setValue(int(opacity * 100))

    def current_properties(self) -> dict:
        """Return the current property values as a dict."""
        return {
            "pen_color": self._pen_color_btn.color,
            "fill_color": self._fill_color_btn.color,
            "pen_width": self._width_spin.value(),
            "item_opacity": self._opacity_slider.value() / 100.0,
            "font_family": self._font_combo.currentFont().family(),
            "font_size": self._font_size_spin.value(),
        }

    # --- Slots ---

    def _on_pen_color_changed(self, color: QColor) -> None:
        self._config.add_recent_color(color.name(QColor.NameFormat.HexArgb))
        self._recent_row.update_colors(self._config.editor.recent_colors)
        self.properties_changed.emit({"pen_color": color})

    def _on_fill_color_changed(self, color: QColor) -> None:
        self._config.add_recent_color(color.name(QColor.NameFormat.HexArgb))
        self._recent_row.update_colors(self._config.editor.recent_colors)
        self.properties_changed.emit({"fill_color": color})

    def _on_recent_color_picked(self, color: QColor) -> None:
        self._pen_color_btn.color = color
        self.properties_changed.emit({"pen_color": color})

    def _on_width_changed(self, value: int) -> None:
        self.properties_changed.emit({"pen_width": value})

    def _on_opacity_changed(self, value: int) -> None:
        self._opacity_label.setText(f"{value}%")
        self.properties_changed.emit({"item_opacity": value / 100.0})

    def _on_font_changed(self, font) -> None:
        self.properties_changed.emit({"font_family": font.family()})

    def _on_font_size_changed(self, value: int) -> None:
        self.properties_changed.emit({"font_size": value})

    def _on_block_size_changed(self, value: int) -> None:
        self.properties_changed.emit({"block_size": value})
