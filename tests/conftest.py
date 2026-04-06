"""Shared fixtures for WaySnip tests."""

from __future__ import annotations

import sys

import pytest

# Ensure QApplication exists before any Qt widget/pixmap usage.
# pytest-qt provides qapp fixture, but we also need one for non-qt tests
# that still touch QColor etc.
from PyQt6.QtWidgets import QApplication

_qapp_instance: QApplication | None = None


@pytest.fixture(scope="session")
def qapp_cls():
    """Session-scoped QApplication (only one allowed per process)."""
    global _qapp_instance
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv[:1])
        _qapp_instance = app
    return app


@pytest.fixture()
def qapp(qapp_cls):
    """Per-test alias so tests can request it simply."""
    return qapp_cls


@pytest.fixture()
def tmp_config_dir(tmp_path, monkeypatch):
    """Provide a temporary directory for config files and patch constants."""
    config_dir = tmp_path / ".config" / "waysnip"
    config_dir.mkdir(parents=True)
    config_file = config_dir / "config.toml"

    monkeypatch.setattr("waysnip.constants.CONFIG_DIR", config_dir)
    monkeypatch.setattr("waysnip.constants.CONFIG_FILE", config_file)
    # Also patch the references imported into config.py
    monkeypatch.setattr("waysnip.config.CONFIG_DIR", config_dir)
    monkeypatch.setattr("waysnip.config.CONFIG_FILE", config_file)

    return config_dir


@pytest.fixture()
def sample_config():
    """Return an AppConfig with default values."""
    from waysnip.config import AppConfig

    return AppConfig()


@pytest.fixture()
def sample_pixmap(qapp):
    """Return a small 100x100 solid-color QPixmap for testing."""
    from PyQt6.QtGui import QPixmap, QColor

    pm = QPixmap(100, 100)
    pm.fill(QColor(64, 128, 255))
    return pm
