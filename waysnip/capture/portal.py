"""Full-screen capture backend.

Dispatches to `gnome-screenshot`, the `org.freedesktop.portal.Screenshot`
D-Bus portal, or `grim` based on the active desktop environment (read from
`XDG_CURRENT_DESKTOP`), with fall-through to the next backend if the
preferred one fails for any reason.

The portal backend exists because GNOME 49 removed `gnome-screenshot` from
Mutter's private screenshot API allow-list — on GNOME 49+ (Ubuntu 26.04)
`gnome-screenshot -f` fails with AccessDenied while the portal keeps working.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.parse import unquote, urlparse

_GNOME_TOKENS = frozenset({"gnome", "gnome-classic", "gnome-flashback", "unity"})
_WLROOTS_TOKENS = frozenset({"sway", "hyprland", "wlroots", "wayfire", "river", "miracle-wm"})

# How long to wait for the portal Response signal.  Generous because some
# portal implementations show a permission dialog the user has to answer.
_PORTAL_TIMEOUT_MS = 60_000


def _desktop_tokens() -> set[str]:
    raw = os.environ.get("XDG_CURRENT_DESKTOP", "")
    return {tok.strip().lower() for tok in raw.split(":") if tok.strip()}


def _backend_order() -> list[str]:
    tokens = _desktop_tokens()
    if tokens & _WLROOTS_TOKENS:
        return ["grim", "portal", "gnome-screenshot"]
    if tokens & _GNOME_TOKENS:
        return ["gnome-screenshot", "portal", "grim"]
    return ["gnome-screenshot", "portal", "grim"]


def _capture_via_gnome_screenshot(path: Path, show_cursor: bool) -> bool:
    cmd = ["gnome-screenshot", "-f", str(path)]
    if show_cursor:
        cmd.append("--include-pointer")
    return _run_capture(cmd, path, "gnome-screenshot")


def _capture_via_grim(path: Path, show_cursor: bool) -> bool:
    cmd = ["grim"]
    if show_cursor:
        cmd.append("-c")
    cmd.append(str(path))
    return _run_capture(cmd, path, "grim")


def _run_capture(cmd: list[str], path: Path, name: str) -> bool:
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=10)
    except FileNotFoundError:
        print(f"{name} not installed")
        return False
    except subprocess.TimeoutExpired:
        print(f"{name} timed out")
        return False
    if result.returncode != 0:
        print(f"{name} failed: {result.stderr.decode(errors='replace').strip()}")
        return False
    if not path.exists() or path.stat().st_size == 0:
        print(f"{name} produced no output")
        return False
    return True


def _portal_screenshot_request(interactive: bool) -> tuple[int | None, str]:
    """Fire one org.freedesktop.portal.Screenshot request and wait for Response.

    Event-driven via QtDBus: subscribe to the Request's Response signal,
    fire the Screenshot call, then spin a local QEventLoop with a hard
    timeout.  Never blocks Qt event processing and cannot hang forever
    (unlike the old dbus-monitor subprocess approach).

    Returns (response_code, uri).  response_code is None on transport
    failure or timeout; 0 means success, 1 user-cancelled, 2 denied.
    """
    try:
        from PyQt6.QtCore import QCoreApplication, QEventLoop, QObject, QTimer, pyqtSlot
        from PyQt6.QtDBus import QDBusConnection, QDBusInterface, QDBusMessage
    except ImportError as exc:
        print(f"portal: QtDBus unavailable ({exc})")
        return None, ""

    if QCoreApplication.instance() is None:
        print("portal: no Qt application running")
        return None, ""

    bus = QDBusConnection.sessionBus()
    if not bus.isConnected():
        print("portal: session bus not connected")
        return None, ""

    # Predict the Request object path so we can subscribe before calling
    # (avoids racing the Response signal).
    token = f"waysnip_{os.getpid()}_{time.monotonic_ns()}"
    sender = bus.baseService().lstrip(":").replace(".", "_")
    request_path = f"/org/freedesktop/portal/desktop/request/{sender}/{token}"

    result: dict = {}
    loop = QEventLoop()

    class _Listener(QObject):
        @pyqtSlot(QDBusMessage)
        def handle(self, msg) -> None:  # noqa: ANN001
            args = msg.arguments()
            result["response"] = args[0] if args else 1
            result["results"] = args[1] if len(args) > 1 else {}
            loop.quit()

    listener = _Listener()

    def _subscribe(p: str) -> bool:
        return bus.connect(
            "org.freedesktop.portal.Desktop",
            p,
            "org.freedesktop.portal.Request",
            "Response",
            listener.handle,
        )

    def _unsubscribe(p: str) -> None:
        bus.disconnect(
            "org.freedesktop.portal.Desktop",
            p,
            "org.freedesktop.portal.Request",
            "Response",
            listener.handle,
        )

    if not _subscribe(request_path):
        print("portal: could not subscribe to Response signal")
        return None, ""

    iface = QDBusInterface(
        "org.freedesktop.portal.Desktop",
        "/org/freedesktop/portal/desktop",
        "org.freedesktop.portal.Screenshot",
        bus,
    )
    reply = iface.call(
        "Screenshot", "", {"handle_token": token, "interactive": interactive}
    )
    if reply.type() == QDBusMessage.MessageType.ErrorMessage:
        print(f"portal: {reply.errorName()}: {reply.errorMessage()}")
        _unsubscribe(request_path)
        return None, ""

    # Older portals may return a handle that differs from the predicted
    # path — re-subscribe on the actual one.
    args = reply.arguments()
    handle = args[0] if args else None
    actual_path = handle.path() if hasattr(handle, "path") else str(handle or "")
    if actual_path and actual_path != request_path:
        _unsubscribe(request_path)
        if not _subscribe(actual_path):
            print("portal: could not subscribe to Response signal (actual path)")
            return None, ""
        request_path = actual_path

    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(loop.quit)
    timer.start(_PORTAL_TIMEOUT_MS)
    loop.exec()
    timer.stop()
    _unsubscribe(request_path)

    if "response" not in result:
        print("portal: timed out waiting for Response")
        return None, ""

    uri = ""
    results = result.get("results") or {}
    if isinstance(results, dict):
        uri = str(results.get("uri", ""))
    return result["response"], uri


def _capture_via_portal(path: Path, show_cursor: bool) -> bool:  # noqa: ARG001
    """Capture via the org.freedesktop.portal.Screenshot D-Bus portal.

    Tries a silent (non-interactive) request first — that works when the
    permission store has a grant for the app (``waysnip setup`` adds one).
    On denial, retries interactively, which shows the desktop's permission
    dialog.  The portal has no show_cursor option; the parameter is ignored.
    """
    response, uri = _portal_screenshot_request(interactive=False)
    if response is None:
        return False
    if response == 1:
        print("portal: cancelled by user")
        return False
    if response != 0:
        print("portal: silent capture denied, retrying with permission dialog")
        response, uri = _portal_screenshot_request(interactive=True)
        if response != 0:
            print(f"portal: request denied or cancelled (response={response})")
            return False

    if not uri.startswith("file://"):
        print(f"portal: unusable screenshot uri {uri!r}")
        return False

    src = Path(unquote(urlparse(uri).path))
    if not src.exists() or src.stat().st_size == 0:
        print(f"portal: screenshot file missing or empty: {src}")
        return False

    # Move into our temp path so the portal's copy (often dropped in the
    # user's screenshots dir) doesn't linger.
    shutil.move(str(src), str(path))
    return True


_BACKENDS = {
    "gnome-screenshot": _capture_via_gnome_screenshot,
    "portal": _capture_via_portal,
    "grim": _capture_via_grim,
}


def capture_fullscreen(show_cursor: bool = False) -> Path | None:
    """Take a full-screen screenshot silently.

    Returns the path to a temporary PNG, or None if every backend failed.
    """
    tmp = tempfile.NamedTemporaryFile(suffix=".png", prefix="waysnip_", delete=False)
    tmp.close()
    path = Path(tmp.name)

    for backend in _backend_order():
        if _BACKENDS[backend](path, show_cursor):
            return path

    path.unlink(missing_ok=True)
    return None
