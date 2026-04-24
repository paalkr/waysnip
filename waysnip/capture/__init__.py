"""Capture pipeline — fullscreen capture, region selection, and clipboard."""

from __future__ import annotations

from waysnip.capture.clipboard import ClipboardManager
from waysnip.capture.portal import capture_fullscreen
from waysnip.capture.region_selector import RegionSelector

__all__ = [
    "ClipboardManager",
    "RegionSelector",
    "capture_fullscreen",
]
