"""Tests for the logical → pixel mapping in the region selector.

Covers the display-scaling bug where the full-layout screenshot is larger
than the logical virtual desktop (grim renders at the highest output scale;
gnome-screenshot captures physical pixels).
"""

from __future__ import annotations

from PyQt6.QtCore import QPoint, QRect, QSize
from PyQt6.QtGui import QColor, QPixmap

from waysnip.capture.region_selector import (
    RegionSelector,
    compute_screenshot_mapping,
    logical_to_pixel_rect,
)


class TestComputeScreenshotMapping:
    def test_scale_one(self):
        scale, origin = compute_screenshot_mapping(
            QSize(1920, 1080), QRect(0, 0, 1920, 1080)
        )
        assert scale == 1.0
        assert origin == QPoint(0, 0)

    def test_integer_scale(self):
        # Single 4K output at 200%: logical 1920x1080, image 3840x2160.
        scale, origin = compute_screenshot_mapping(
            QSize(3840, 2160), QRect(0, 0, 1920, 1080)
        )
        assert scale == 2.0

    def test_mixed_scale_grim_layout(self):
        # Sondre-style setup: scale-1 1920x1080 next to a scale-2 monitor
        # (logical 1280x720).  Layout = 3200x1080 logical; grim renders at
        # max scale 2 → image 6400x2160.
        virtual = QRect(0, 0, 1920, 1080).united(QRect(1920, 0, 1280, 720))
        scale, origin = compute_screenshot_mapping(QSize(6400, 2160), virtual)
        assert scale == 2.0
        assert origin == QPoint(0, 0)

    def test_fractional_scale(self):
        # 2560x1440 output at 125%: logical 2048x1152, image 2560x1440.
        scale, _ = compute_screenshot_mapping(
            QSize(2560, 1440), QRect(0, 0, 2048, 1152)
        )
        assert scale == 1.25

    def test_negative_layout_origin(self):
        # Monitor positioned left of the primary → virtual origin < 0.
        virtual = QRect(-1920, 0, 1920, 1080).united(QRect(0, 0, 1920, 1080))
        scale, origin = compute_screenshot_mapping(QSize(3840, 1080), virtual)
        assert scale == 1.0
        assert origin == QPoint(-1920, 0)

    def test_degenerate_inputs_fall_back_to_identity(self):
        assert compute_screenshot_mapping(QSize(0, 0), QRect(0, 0, 1920, 1080)) == (
            1.0,
            QPoint(0, 0),
        )
        assert compute_screenshot_mapping(QSize(1920, 1080), QRect()) == (
            1.0,
            QPoint(0, 0),
        )


class TestLogicalToPixelRect:
    def test_identity(self):
        src = logical_to_pixel_rect(QRect(10, 20, 30, 40), 1.0, QPoint(0, 0))
        assert src.getRect() == (10, 20, 30, 40)

    def test_scale_two(self):
        src = logical_to_pixel_rect(QRect(10, 20, 30, 40), 2.0, QPoint(0, 0))
        assert src.getRect() == (20, 40, 60, 80)

    def test_origin_shift(self):
        src = logical_to_pixel_rect(QRect(-1920, 0, 100, 100), 1.0, QPoint(-1920, 0))
        assert src.getRect() == (0, 0, 100, 100)

    def test_fractional(self):
        src = logical_to_pixel_rect(QRect(100, 100, 200, 200), 1.25, QPoint(0, 0))
        assert src.getRect() == (125, 125, 250, 250)

    def test_second_monitor_in_mixed_layout(self):
        # The scale-2 monitor at logical x=1920 starts at pixel x=3840 in
        # a grim composite rendered at scale 2.
        src = logical_to_pixel_rect(QRect(1920, 0, 1280, 720), 2.0, QPoint(0, 0))
        assert src.getRect() == (3840, 0, 2560, 1440)


class TestPressDoesNotClobberMapping:
    """Regression: the selection anchor (_origin, set on mouse press) must not
    collide with the screenshot mapping origin (_img_origin). A collision made
    the frozen image jump by the click offset the moment a drag started."""

    def test_press_leaves_img_origin_untouched(self, qapp):
        pm = QPixmap(800, 600)
        pm.fill(QColor("gray"))
        sel = RegionSelector(pm)
        before = QPoint(sel._img_origin)

        overlay = sel._overlays[0] if sel._overlays else None
        sel.handle_mouse_press(QPoint(300, 250), overlay)

        # The selection anchor moved to the click...
        assert sel._origin == QPoint(300, 250)
        # ...but the screenshot mapping origin is unchanged.
        assert sel._img_origin == before

    def test_img_origin_and_origin_are_distinct_attributes(self, qapp):
        pm = QPixmap(800, 600)
        pm.fill(QColor("gray"))
        sel = RegionSelector(pm)
        assert hasattr(sel, "_img_origin")
        assert hasattr(sel, "_origin")


def _quadrant_pixmap(w: int, h: int) -> QPixmap:
    """Pixmap with four solid-colour quadrants for crop verification."""
    pm = QPixmap(w, h)
    from PyQt6.QtGui import QPainter

    p = QPainter(pm)
    p.fillRect(0, 0, w // 2, h // 2, QColor("red"))
    p.fillRect(w // 2, 0, w - w // 2, h // 2, QColor("lime"))
    p.fillRect(0, h // 2, w // 2, h - h // 2, QColor("blue"))
    p.fillRect(w // 2, h // 2, w - w // 2, h - h // 2, QColor("yellow"))
    p.end()
    return pm


class TestConfirmSelectionCrop:
    def _selector(self, qapp, pixmap: QPixmap, scale: float, origin=QPoint(0, 0)):
        selector = RegionSelector(pixmap)
        # The offscreen test platform has a single synthetic screen, so the
        # auto-computed mapping is meaningless here — inject the scenario.
        selector._scale = scale
        selector._img_origin = origin
        return selector

    def test_crop_at_scale_two_returns_physical_pixels(self, qapp):
        pm = _quadrant_pixmap(400, 400)  # "physical" image of a 200x200 logical desktop
        selector = self._selector(qapp, pm, scale=2.0)
        selector._selection = QRect(0, 0, 100, 100)  # logical top-left quadrant

        captured: list[QPixmap] = []
        selector.region_selected.connect(captured.append)
        selector._confirm_selection()

        assert len(captured) == 1
        out = captured[0]
        assert out.size() == QSize(200, 200)
        img = out.toImage()
        assert img.pixelColor(100, 100) == QColor("red")

    def test_crop_second_quadrant_content(self, qapp):
        pm = _quadrant_pixmap(400, 400)
        selector = self._selector(qapp, pm, scale=2.0)
        selector._selection = QRect(100, 100, 100, 100)  # logical bottom-right

        captured: list[QPixmap] = []
        selector.region_selected.connect(captured.append)
        selector._confirm_selection()

        img = captured[0].toImage()
        assert captured[0].size() == QSize(200, 200)
        assert img.pixelColor(100, 100) == QColor("yellow")

    def test_crop_clamps_to_image_bounds(self, qapp):
        pm = _quadrant_pixmap(400, 400)
        selector = self._selector(qapp, pm, scale=2.0)
        # Selection extends past the right/bottom edge of the desktop.
        selector._selection = QRect(150, 150, 100, 100)

        captured: list[QPixmap] = []
        selector.region_selected.connect(captured.append)
        selector._confirm_selection()

        assert captured[0].size() == QSize(100, 100)

    def test_crop_identity_scale_unchanged_behavior(self, qapp):
        pm = _quadrant_pixmap(200, 200)
        selector = self._selector(qapp, pm, scale=1.0)
        selector._selection = QRect(0, 0, 100, 100)

        captured: list[QPixmap] = []
        selector.region_selected.connect(captured.append)
        selector._confirm_selection()

        assert captured[0].size() == QSize(100, 100)
        assert captured[0].toImage().pixelColor(50, 50) == QColor("red")

    def test_crop_fully_outside_image_emits_nothing(self, qapp):
        pm = _quadrant_pixmap(200, 200)
        selector = self._selector(qapp, pm, scale=1.0)
        selector._selection = QRect(500, 500, 50, 50)

        captured: list[QPixmap] = []
        selector.region_selected.connect(captured.append)
        selector._confirm_selection()

        assert captured == []
