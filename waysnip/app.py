"""Application singleton — single-instance IPC, orchestration, lifecycle."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from PyQt6.QtCore import QByteArray
from PyQt6.QtGui import QPixmap
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtWidgets import QApplication

from waysnip.config import AppConfig
from waysnip.constants import APP_DISPLAY_NAME, SOCKET_NAME_TEMPLATE

# ---------------------------------------------------------------------------
# Optional imports for modules built by other agents.  Stubs are used when
# the real modules are not yet available.
# ---------------------------------------------------------------------------
from waysnip.capture.portal import capture_fullscreen, capture_interactive
from waysnip.capture.region_selector import RegionSelector
from waysnip.capture.clipboard import ClipboardManager
from waysnip.editor.editor_window import EditorWindow
from waysnip.save import save_screenshot


def _socket_name() -> str:
    return SOCKET_NAME_TEMPLATE.format(uid=os.getuid())


def _try_send_to_running_instance(command: str) -> bool:
    """Attempt to send *command* to an already-running WaySnip instance.

    Returns True if the message was sent (meaning we should exit), False if no
    running instance was found.
    """
    sock = QLocalSocket()
    sock.connectToServer(_socket_name())
    if not sock.waitForConnected(500):
        return False

    payload = json.dumps({"command": command}).encode()
    sock.write(QByteArray(payload))
    sock.waitForBytesWritten(1000)
    sock.disconnectFromServer()
    return True


class WaySnipApp:
    """Top-level application object that owns the Qt event loop."""

    def __init__(self, command: str) -> None:
        self._app = QApplication.instance() or QApplication(sys.argv)
        self._app.setApplicationName(APP_DISPLAY_NAME)
        self._app.setQuitOnLastWindowClosed(False)

        self._config = AppConfig.load()
        self._server: QLocalServer | None = None
        self._tray = None
        self._gallery_window = None
        self._settings_dialog = None
        self._pending_command = command

        self._load_stylesheet()

    # ---- Lifecycle ---------------------------------------------------------

    def start(self) -> int:
        """Set up the local server, tray icon, and execute the initial command."""
        self._start_server()

        if self._config.tray.enabled:
            from waysnip.tray import TrayIcon

            self._tray = TrayIcon(self)
            self._tray.show()

        # Keep app alive until we explicitly allow quitting.
        # Without tray, the app should quit when the last editor/gallery
        # window closes — but NOT when the region selector closes.
        self._app.setQuitOnLastWindowClosed(False)

        self._dispatch(self._pending_command)

        return self._app.exec()

    # ---- IPC Server --------------------------------------------------------

    def _start_server(self) -> None:
        self._server = QLocalServer(self._app)
        # Remove stale socket if present.
        QLocalServer.removeServer(_socket_name())
        if not self._server.listen(_socket_name()):
            print(f"Warning: could not start IPC server: {self._server.errorString()}")
            return
        self._server.newConnection.connect(self._on_new_connection)

    def _on_new_connection(self) -> None:
        conn = self._server.nextPendingConnection()
        if conn is None:
            return
        conn.waitForReadyRead(1000)
        data = conn.readAll().data()
        conn.close()
        try:
            msg = json.loads(data.decode())
            self._dispatch(msg.get("command", "region"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass

    # ---- Command dispatch --------------------------------------------------

    def _dispatch(self, command: str) -> None:
        if command == "tray":
            # Just stay in tray, no action
            return
        actions = {
            "region": self.do_capture_region,
            "window": self.do_capture_window,
            "fullscreen": self.do_capture_fullscreen,
            "gallery": self.do_open_gallery,
            "config": self.do_open_settings,
        }
        action = actions.get(command, self.do_capture_region)
        action()

    # ---- Capture orchestration ---------------------------------------------

    def do_capture_region(self) -> None:
        show_cursor = self._config.capture.show_cursor
        path = capture_fullscreen(show_cursor=show_cursor)
        if path is None:
            return
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            return

        def _on_region_selected(cropped):
            if cropped is None or cropped.isNull():
                return
            self._copy_to_clipboard(cropped)
            self._post_capture(cropped)

        def _on_cancelled():
            if not self._config.tray.enabled:
                self._app.quit()

        self._region_selector = RegionSelector(pixmap)
        self._region_selector.region_selected.connect(_on_region_selected)
        self._region_selector.cancelled.connect(_on_cancelled)
        self._region_selector.show()

    def do_capture_window(self) -> None:
        path = capture_interactive()
        if path is None:
            return
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            return
        self._copy_to_clipboard(pixmap)
        self._post_capture(pixmap)

    def do_capture_fullscreen(self) -> None:
        show_cursor = self._config.capture.show_cursor
        path = capture_fullscreen(show_cursor=show_cursor)
        if path is None:
            return
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            return
        self._copy_to_clipboard(pixmap)
        self._post_capture(pixmap)

    # ---- Gallery / Settings ------------------------------------------------

    def do_open_gallery(self) -> None:
        from waysnip.gallery.gallery_window import GalleryWindow

        if self._gallery_window is None:
            self._gallery_window = GalleryWindow(self._config)
        self._gallery_window.show()
        self._gallery_window.raise_()
        self._gallery_window.activateWindow()

    def do_open_settings(self) -> None:
        from waysnip.settings_dialog import SettingsDialog

        if self._settings_dialog is None or not self._settings_dialog.isVisible():
            self._settings_dialog = SettingsDialog(self._config)
            self._settings_dialog.config_saved.connect(self._on_config_saved)
        self._settings_dialog.show()
        self._settings_dialog.raise_()
        self._settings_dialog.activateWindow()

    # ---- Helpers -----------------------------------------------------------

    def _post_capture(self, pixmap) -> None:
        """Open editor or save, depending on config."""
        action = self._config.capture.after_capture
        if action == "editor":
            self._open_editor(pixmap)
        elif action == "save":
            self._save_pixmap(pixmap)
        elif action == "clipboard+save":
            self._save_pixmap(pixmap)
        # "clipboard" — already copied above, nothing more to do.

    def _open_editor(self, pixmap) -> None:
        win = EditorWindow(pixmap, self._config)
        # Keep a reference so the window isn't garbage collected
        if not hasattr(self, "_editor_windows"):
            self._editor_windows = []
        self._editor_windows.append(win)
        def _on_editor_destroyed():
            if win in self._editor_windows:
                self._editor_windows.remove(win)
            # If no tray and no more windows, quit
            if not self._config.tray.enabled and not self._editor_windows:
                self._app.quit()

        win.destroyed.connect(_on_editor_destroyed)
        win.show()
        win.raise_()
        win.activateWindow()

    def _save_pixmap(self, pixmap, annotations=None, original_pixmap=None) -> None:
        path = save_screenshot(pixmap, annotations or [], original_pixmap, self._config)
        return path

    @staticmethod
    def _copy_to_clipboard(pixmap) -> None:
        ClipboardManager.copy_image_from_pixmap(pixmap)

    def _on_config_saved(self) -> None:
        self._config = AppConfig.load()
        if self._tray is not None:
            self._tray.reload_config(self._config)
        # Propagate to open editor windows
        if hasattr(self, "_editor_windows"):
            for win in self._editor_windows:
                if hasattr(win, "_config"):
                    win._config = self._config
        # Propagate to gallery
        if self._gallery_window is not None:
            self._gallery_window._config = self._config

    def _load_stylesheet(self) -> None:
        qss_path = Path(__file__).parent / "resources" / "style.qss"
        if qss_path.exists():
            self._app.setStyleSheet(qss_path.read_text())



# ---------------------------------------------------------------------------
# Public entry point called from cli.py
# ---------------------------------------------------------------------------

def run(command: str) -> None:
    """Start WaySnip or talk to an existing instance."""
    # We need a QApplication for QLocalSocket even when just sending IPC.
    _temp_app = QApplication.instance() or QApplication(sys.argv)

    if _try_send_to_running_instance(command):
        sys.exit(0)

    app = WaySnipApp(command)
    sys.exit(app.start())
