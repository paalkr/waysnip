"""System tray icon with context menu."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon

from waysnip.constants import APP_DISPLAY_NAME

if TYPE_CHECKING:
    from waysnip.app import WaySnipApp
    from waysnip.config import AppConfig


def _make_tray_icon() -> QIcon:
    """Load a bright symbolic icon suitable for the system tray."""
    from pathlib import Path
    icon_path = Path(__file__).parent / "resources" / "icons" / "waysnip-symbolic.svg"
    if icon_path.exists():
        return QIcon(str(icon_path))
    # Fallback to the full color icon
    icon_path = Path(__file__).parent / "resources" / "icons" / "waysnip.svg"
    if icon_path.exists():
        return QIcon(str(icon_path))
    return QIcon.fromTheme("accessories-screenshot")


class TrayIcon(QSystemTrayIcon):
    def __init__(self, app: WaySnipApp) -> None:
        super().__init__(_make_tray_icon(), parent=None)
        self._app = app
        self._config: AppConfig = app._config  # noqa: SLF001

        self.setToolTip(APP_DISPLAY_NAME)
        self._build_menu()
        self.activated.connect(self._on_activated)

    # ---- Menu construction -------------------------------------------------

    def _build_menu(self) -> None:
        menu = QMenu()

        menu.addAction("Region Capture", self._app.do_capture_region)
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
