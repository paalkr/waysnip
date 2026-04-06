"""System tray icon with context menu."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon

from waysnip.constants import APP_DISPLAY_NAME

if TYPE_CHECKING:
    from waysnip.app import WaySnipApp
    from waysnip.config import AppConfig


def _make_icon() -> QIcon:
    """Create a simple camera-ish icon as a placeholder."""
    size = 64
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Body
    p.setBrush(QColor("#0078d7"))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(6, 16, 52, 38, 6, 6)

    # Lens
    p.setBrush(QColor("#e0e0e0"))
    p.drawEllipse(20, 22, 24, 24)
    p.setBrush(QColor("#2b2b2b"))
    p.drawEllipse(26, 28, 12, 12)

    # Flash bump
    p.setBrush(QColor("#0078d7"))
    p.drawRoundedRect(22, 10, 20, 10, 3, 3)

    p.end()
    return QIcon(pm)


class TrayIcon(QSystemTrayIcon):
    def __init__(self, app: WaySnipApp) -> None:
        super().__init__(_make_icon(), parent=None)
        self._app = app
        self._config: AppConfig = app._config  # noqa: SLF001

        self.setToolTip(APP_DISPLAY_NAME)
        self._build_menu()
        self.activated.connect(self._on_activated)

    # ---- Menu construction -------------------------------------------------

    def _build_menu(self) -> None:
        menu = QMenu()

        menu.addAction("Region Capture", self._app.do_capture_region)
        menu.addAction("Window Capture", self._app.do_capture_window)
        menu.addAction("Fullscreen Capture", self._app.do_capture_fullscreen)
        menu.addSeparator()
        menu.addAction("Gallery", self._app.do_open_gallery)
        menu.addAction("Settings", self._app.do_open_settings)
        menu.addSeparator()

        quit_action = QAction("Quit", menu)
        quit_action.triggered.connect(self._quit)
        menu.addAction(quit_action)

        self.setContextMenu(menu)

    # ---- Signals -----------------------------------------------------------

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason != QSystemTrayIcon.ActivationReason.Trigger:
            return

        action_map = {
            "region": self._app.do_capture_region,
            "window": self._app.do_capture_window,
            "fullscreen": self._app.do_capture_fullscreen,
            "gallery": self._app.do_open_gallery,
        }
        action = action_map.get(self._config.tray.left_click_action, self._app.do_capture_region)
        action()

    # ---- Public ------------------------------------------------------------

    def reload_config(self, config: AppConfig) -> None:
        self._config = config

    # ---- Private -----------------------------------------------------------

    @staticmethod
    def _quit() -> None:
        from PyQt6.QtWidgets import QApplication

        QApplication.quit()
