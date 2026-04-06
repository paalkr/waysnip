"""Application-wide constants and defaults."""

from pathlib import Path

APP_NAME = "waysnip"
APP_VERSION = "0.2.1"
APP_DISPLAY_NAME = "WaySnip"

# Paths
CONFIG_DIR = Path.home() / ".config" / APP_NAME
CONFIG_FILE = CONFIG_DIR / "config.toml"
DEFAULT_SAVE_DIR = Path.home() / "Pictures" / "Screenshots"

# IPC
SOCKET_NAME_TEMPLATE = "waysnip-{uid}"

# Save format
DEFAULT_FILENAME_PATTERN = "Screenshot_%Y-%m-%d_%H-%M-%S.png"

# Editor defaults
DEFAULT_PEN_COLOR = "#ff0000"
DEFAULT_PEN_WIDTH = 3
DEFAULT_FILL_COLOR = "#00000000"  # transparent
DEFAULT_FONT_FAMILY = "Sans"
DEFAULT_FONT_SIZE = 16

# Magnifier
DEFAULT_MAGNIFIER_ZOOM = 5
DEFAULT_MAGNIFIER_SIZE = 150

# Resize handles
HANDLE_SIZE = 8
HANDLE_HALF = HANDLE_SIZE / 2

# PNG metadata keys
META_KEY_ANNOTATIONS = "waysnip-annotations"
META_KEY_ORIGINAL = "waysnip-original"

# Tool shortcut keys
TOOL_SHORTCUTS = {
    "select": "V",
    "rectangle": "R",
    "ellipse": "E",
    "arrow": "A",
    "line": "L",
    "text": "T",
    "numbered_marker": "N",
    "freehand": "P",
    "highlight": "H",
    "blur": "B",
    "crop": "C",
}
