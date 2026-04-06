"""xdg-desktop-portal Screenshot integration via D-Bus."""

from __future__ import annotations

import uuid
from pathlib import Path
from urllib.parse import urlparse, unquote

from PyQt6.QtCore import QEventLoop, QTimer, QVariant
from PyQt6.QtDBus import (
    QDBusConnection,
    QDBusInterface,
    QDBusMessage,
    QDBusVariant,
)


_PORTAL_SERVICE = "org.freedesktop.portal.Desktop"
_PORTAL_PATH = "/org/freedesktop/portal/desktop"
_PORTAL_IFACE = "org.freedesktop.portal.Screenshot"
_REQUEST_IFACE = "org.freedesktop.portal.Request"

_TIMEOUT_MS = 10_000


def _unique_token() -> str:
    """Return a token safe for a D-Bus object path segment."""
    return "waysnip_" + uuid.uuid4().hex[:12]


def _sender_name() -> str:
    """Get the unique bus name mangled for object-path use.

    The portal builds the request path from the sender's unique name with
    dots replaced by underscores and the leading colon stripped.
    """
    bus = QDBusConnection.sessionBus()
    name = bus.baseService()  # e.g. ":1.234"
    return name.lstrip(":").replace(".", "_")


def _uri_to_path(uri: str) -> Path:
    """Convert a file:// URI to a local Path."""
    parsed = urlparse(uri)
    return Path(unquote(parsed.path))


def _call_screenshot(interactive: bool, show_cursor: bool = False) -> Path:
    """Perform a portal Screenshot call and wait for the async response.

    Parameters
    ----------
    interactive:
        If True the portal shows its own picker UI. If False a full-screen
        capture is taken immediately.
    show_cursor:
        Whether to include the mouse cursor in the capture (non-interactive
        mode only; the portal may ignore this in interactive mode).

    Returns
    -------
    Path to the temporary PNG written by the portal.

    Raises
    ------
    RuntimeError
        On timeout, cancellation, or D-Bus error.
    """
    bus = QDBusConnection.sessionBus()

    token = _unique_token()
    request_path = f"/org/freedesktop/portal/desktop/request/{_sender_name()}/{token}"

    # Prepare to listen for the Response signal *before* calling Screenshot so
    # we never miss a fast reply.
    loop = QEventLoop()
    result_uri: list[str] = []
    error_msg: list[str] = []

    def _on_response(msg: QDBusMessage) -> None:
        args = msg.arguments()
        if len(args) < 2:
            error_msg.append("Unexpected portal response (missing arguments)")
            loop.quit()
            return
        response_code = args[0]
        results = args[1]
        if response_code != 0:
            error_msg.append(
                f"Portal returned non-success response code {response_code}"
            )
            loop.quit()
            return
        uri = results.get("uri", "")
        if not uri:
            error_msg.append("Portal response missing 'uri' field")
            loop.quit()
            return
        result_uri.append(uri)
        loop.quit()

    connected = bus.connect(
        _PORTAL_SERVICE,
        request_path,
        _REQUEST_IFACE,
        "Response",
        _on_response,
    )
    if not connected:
        raise RuntimeError(
            f"Failed to connect to portal Response signal on {request_path}"
        )

    # Build the options dict.
    options: dict[str, QDBusVariant] = {
        "handle_token": QDBusVariant(QVariant(token)),
        "interactive": QDBusVariant(QVariant(interactive)),
    }
    if not interactive:
        options["modal"] = QDBusVariant(QVariant(False))

    iface = QDBusInterface(
        _PORTAL_SERVICE,
        _PORTAL_PATH,
        _PORTAL_IFACE,
        bus,
    )
    if not iface.isValid():
        raise RuntimeError(
            "Could not create D-Bus interface for xdg-desktop-portal. "
            "Is the portal service running?"
        )

    reply: QDBusMessage = iface.call("Screenshot", "", options)

    if reply.type() == QDBusMessage.MessageType.ErrorMessage:
        raise RuntimeError(f"Portal Screenshot call failed: {reply.errorMessage()}")

    # Wait for the Response signal (or timeout).
    QTimer.singleShot(_TIMEOUT_MS, loop.quit)
    loop.exec()

    # Disconnect our handler.
    bus.disconnect(
        _PORTAL_SERVICE,
        request_path,
        _REQUEST_IFACE,
        "Response",
        _on_response,
    )

    if error_msg:
        raise RuntimeError(error_msg[0])
    if not result_uri:
        raise RuntimeError("Portal screenshot timed out")

    return _uri_to_path(result_uri[0])


def capture_fullscreen(show_cursor: bool = False) -> Path:
    """Take a non-interactive full-screen screenshot via the portal.

    Parameters
    ----------
    show_cursor:
        Include the mouse cursor in the capture if the portal supports it.

    Returns
    -------
    Path to the temporary PNG file written by the portal.
    """
    return _call_screenshot(interactive=False, show_cursor=show_cursor)


def capture_interactive() -> Path:
    """Open the portal's interactive screenshot picker (GNOME's own UI).

    Returns
    -------
    Path to the temporary PNG file written by the portal.
    """
    return _call_screenshot(interactive=True)
