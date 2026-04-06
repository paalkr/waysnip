"""Tests for waysnip save/load functionality.

These tests define the contract for save.py. They will fail until the
capture agent delivers the implementation.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# save.py does not exist yet — skip the entire module if import fails.
try:
    from waysnip.save import (
        save_screenshot,
        load_annotations,
        flatten_image,
        save_flattened_copy,
    )

    HAS_SAVE_MODULE = True
except ImportError:
    HAS_SAVE_MODULE = False

pytestmark = pytest.mark.skipif(
    not HAS_SAVE_MODULE, reason="waysnip.save not yet implemented"
)


class TestSaveScreenshot:
    def test_creates_file(self, tmp_path, sample_pixmap):
        path = save_screenshot(sample_pixmap, directory=tmp_path)
        assert path.exists()
        assert path.suffix == ".png"

    def test_filename_pattern(self, tmp_path, sample_pixmap):
        path = save_screenshot(sample_pixmap, directory=tmp_path)
        # Should match Screenshot_YYYY-MM-DD_HH-MM-SS.png pattern
        assert path.name.startswith("Screenshot_")

    def test_embeds_metadata(self, tmp_path, sample_pixmap):
        annotations = [{"type": "rectangle", "x": 10, "y": 20}]
        path = save_screenshot(
            sample_pixmap, directory=tmp_path, annotations=annotations
        )
        loaded = load_annotations(path)
        assert loaded is not None
        assert len(loaded) == 1
        assert loaded[0]["type"] == "rectangle"


class TestLoadAnnotations:
    def test_returns_none_for_plain_png(self, tmp_path, sample_pixmap):
        path = tmp_path / "plain.png"
        sample_pixmap.save(str(path), "PNG")
        result = load_annotations(path)
        assert result is None

    def test_round_trip(self, tmp_path, sample_pixmap):
        annotations = [
            {"type": "arrow", "x": 0, "y": 0, "pen_width": 3},
            {"type": "text", "x": 50, "y": 50, "content": "hello"},
        ]
        path = save_screenshot(
            sample_pixmap, directory=tmp_path, annotations=annotations
        )
        loaded = load_annotations(path)
        assert loaded == annotations


class TestFlatten:
    def test_flatten_strips_metadata(self, tmp_path, sample_pixmap):
        annotations = [{"type": "rectangle", "x": 0, "y": 0}]
        path = save_screenshot(
            sample_pixmap, directory=tmp_path, annotations=annotations
        )
        flattened = flatten_image(path)
        assert flattened is not None
        # Save flattened and check no annotations
        flat_path = tmp_path / "flat.png"
        flattened.save(str(flat_path), "PNG")
        assert load_annotations(flat_path) is None

    def test_save_flattened_copy(self, tmp_path, sample_pixmap):
        annotations = [{"type": "rectangle", "x": 0, "y": 0}]
        path = save_screenshot(
            sample_pixmap, directory=tmp_path, annotations=annotations
        )
        flat_path = save_flattened_copy(path)
        assert flat_path.exists()
        assert "_flat" in flat_path.stem
