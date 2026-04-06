"""Tests for waysnip save/load functionality."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from waysnip.save import (
    save_screenshot,
    load_annotations,
    flatten_image,
    save_flattened_copy,
)
from waysnip.config import AppConfig
from waysnip.constants import META_KEY_ANNOTATIONS


@pytest.fixture
def save_config(tmp_path):
    """Create an AppConfig pointing to a temp directory."""
    config = AppConfig()
    config.save.directory = str(tmp_path)
    config.save.pattern = "Screenshot_%Y-%m-%d_%H-%M-%S.png"
    config.save.mode = "annotated"
    return config


class TestSaveScreenshot:
    def test_creates_file(self, tmp_path, sample_pixmap, save_config):
        path = save_screenshot(sample_pixmap, [], None, save_config)
        assert path.exists()
        assert path.suffix == ".png"

    def test_filename_pattern(self, tmp_path, sample_pixmap, save_config):
        path = save_screenshot(sample_pixmap, [], None, save_config)
        assert path.name.startswith("Screenshot_")

    def test_embeds_metadata(self, tmp_path, sample_pixmap, save_config):
        annotations = [{"type": "rectangle", "x": 10, "y": 20}]
        path = save_screenshot(sample_pixmap, annotations, sample_pixmap, save_config)
        _orig, loaded = load_annotations(path)
        assert len(loaded) == 1
        assert loaded[0]["type"] == "rectangle"


class TestLoadAnnotations:
    def test_returns_empty_for_plain_png(self, tmp_path, sample_pixmap):
        path = tmp_path / "plain.png"
        sample_pixmap.save(str(path), "PNG")
        original, annotations = load_annotations(path)
        assert original is None
        assert annotations == []

    def test_round_trip(self, tmp_path, sample_pixmap, save_config):
        annotations = [
            {"type": "arrow", "x": 0, "y": 0, "pen_width": 3},
            {"type": "text", "x": 50, "y": 50, "content": "hello"},
        ]
        path = save_screenshot(sample_pixmap, annotations, sample_pixmap, save_config)
        _orig, loaded = load_annotations(path)
        assert loaded == annotations


class TestFlatten:
    def test_flatten_strips_metadata(self, tmp_path, sample_pixmap, save_config):
        annotations = [{"type": "rectangle", "x": 0, "y": 0}]
        path = save_screenshot(sample_pixmap, annotations, sample_pixmap, save_config)
        flatten_image(path)
        _orig, loaded = load_annotations(path)
        assert loaded == []

    def test_save_flattened_copy(self, tmp_path, sample_pixmap, save_config):
        annotations = [{"type": "rectangle", "x": 0, "y": 0}]
        path = save_screenshot(sample_pixmap, annotations, sample_pixmap, save_config)
        flat_path = save_flattened_copy(path)
        assert flat_path.exists()
        assert "_flat" in flat_path.stem
