"""Save, load, and flatten screenshots with embedded annotation metadata."""

from __future__ import annotations

import base64
import json
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QBuffer, QIODevice
from PyQt6.QtGui import QImage, QPixmap

from waysnip.config import AppConfig
from waysnip.constants import META_KEY_ANNOTATIONS, META_KEY_ORIGINAL


def _pixmap_to_png_bytes(pixmap: QPixmap) -> bytes:
    """Encode a QPixmap as PNG bytes."""
    buf = QBuffer()
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    pixmap.save(buf, "PNG")
    return bytes(buf.data())


def _pixmap_to_base64(pixmap: QPixmap) -> str:
    """Encode a QPixmap as a base64 string of its PNG representation."""
    return base64.b64encode(_pixmap_to_png_bytes(pixmap)).decode("ascii")


def _pixmap_from_base64(data: str) -> QPixmap:
    """Decode a base64-encoded PNG back into a QPixmap."""
    raw = base64.b64decode(data)
    pm = QPixmap()
    pm.loadFromData(raw, "PNG")
    return pm


def save_screenshot(
    pixmap: QPixmap,
    annotations: list[dict],
    original_pixmap: QPixmap | None,
    config: AppConfig,
) -> Path:
    """Save a screenshot to disk with optional annotation metadata.

    Parameters
    ----------
    pixmap:
        The (possibly annotated/flattened) image to save.
    annotations:
        Annotation data dicts to embed in PNG metadata.
    original_pixmap:
        The un-annotated capture, embedded so the file can be re-edited later.
    config:
        Application config (provides save directory, filename pattern, mode).

    Returns
    -------
    Path to the saved file.
    """
    now = datetime.now()
    filename = now.strftime(config.save.pattern)

    save_dir = config.get_save_directory()
    dest = save_dir / filename

    # If the pattern contains sub-directories (e.g. "%Y-%m/Screenshot_..."),
    # make sure they exist.
    dest.parent.mkdir(parents=True, exist_ok=True)

    mode = config.save.mode

    if mode == "editable" and original_pixmap is not None:
        # Save the original (clean) pixels — annotations only in metadata.
        image = original_pixmap.toImage()
    else:
        # "annotated" (default) — save the flattened annotated image as pixels.
        image = pixmap.toImage()

    # Embed annotation JSON.
    if annotations:
        image.setText(META_KEY_ANNOTATIONS, json.dumps(annotations))

    # Embed original pixmap for later re-editing (in "annotated" mode, the
    # pixels are the flattened render, so we need the original separately).
    if mode == "annotated" and original_pixmap is not None:
        image.setText(META_KEY_ORIGINAL, _pixmap_to_base64(original_pixmap))

    image.save(str(dest), "PNG")
    return dest


def load_annotations(path: Path) -> tuple[QPixmap | None, list[dict]]:
    """Load annotation metadata from a WaySnip PNG.

    Returns
    -------
    A tuple of (original_pixmap_or_None, annotation_dicts).
    """
    image = QImage(str(path))
    if image.isNull():
        raise FileNotFoundError(f"Cannot load image: {path}")

    original: QPixmap | None = None
    annotations: list[dict] = []

    orig_b64 = image.text(META_KEY_ORIGINAL)
    if orig_b64:
        original = _pixmap_from_base64(orig_b64)

    ann_json = image.text(META_KEY_ANNOTATIONS)
    if ann_json:
        annotations = json.loads(ann_json)

    return original, annotations


def flatten_image(path: Path) -> None:
    """Strip all WaySnip metadata from a PNG file, re-saving in place."""
    image = QImage(str(path))
    if image.isNull():
        raise FileNotFoundError(f"Cannot load image: {path}")

    # QImage doesn't have a removeText — create a fresh image and copy pixels.
    clean = QImage(image.size(), image.format())
    clean.fill(0)
    from PyQt6.QtGui import QPainter

    painter = QPainter(clean)
    painter.drawImage(0, 0, image)
    painter.end()

    clean.save(str(path), "PNG")


def save_flattened_copy(path: Path) -> Path:
    """Save a metadata-free copy of the image as ``{stem}_flat.png``.

    Returns the path to the new file.
    """
    image = QImage(str(path))
    if image.isNull():
        raise FileNotFoundError(f"Cannot load image: {path}")

    flat_path = path.with_stem(path.stem + "_flat")

    clean = QImage(image.size(), image.format())
    clean.fill(0)
    from PyQt6.QtGui import QPainter

    painter = QPainter(clean)
    painter.drawImage(0, 0, image)
    painter.end()

    clean.save(str(flat_path), "PNG")
    return flat_path
