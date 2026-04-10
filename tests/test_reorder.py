"""Tests for annotation layer ordering (z-value management)."""

from __future__ import annotations

import pytest
from PyQt6.QtGui import QPixmap, QColor

from waysnip.editor.scene import AnnotationScene
from waysnip.editor.tools.base import BaseAnnotationItem
from waysnip.editor.tools.blur import BlurItem
from waysnip.editor.tools.rectangle import RectangleItem
from waysnip.editor.tools.ellipse import EllipseItem
from waysnip.editor.tools.arrow import ArrowItem
from waysnip.editor.commands import ReorderItemCommand


@pytest.fixture()
def scene(qapp):
    """Scene with a small background pixmap."""
    s = AnnotationScene()
    pm = QPixmap(200, 200)
    pm.fill(QColor(128, 128, 128))
    s.set_background_pixmap(pm)
    return s


class TestAutoZAssignment:
    def test_new_items_get_incrementing_z(self, scene):
        r1 = RectangleItem()
        r2 = RectangleItem()
        r3 = RectangleItem()
        scene.addItem(r1)
        scene.addItem(r2)
        scene.addItem(r3)
        assert r1.zValue() < r2.zValue() < r3.zValue()

    def test_blur_stays_at_minus_500(self, scene):
        b = BlurItem()
        scene.addItem(b)
        assert b.zValue() == -500

    def test_blur_below_regular_items(self, scene):
        r = RectangleItem()
        b = BlurItem()
        scene.addItem(r)
        scene.addItem(b)
        assert b.zValue() < r.zValue()

    def test_blur_below_even_when_added_after(self, scene):
        r = RectangleItem()
        scene.addItem(r)
        b = BlurItem()
        scene.addItem(b)
        assert b.zValue() < r.zValue()


class TestBringToFront:
    def test_brings_item_to_top(self, scene):
        r1 = RectangleItem()
        r2 = EllipseItem()
        r3 = ArrowItem()
        scene.addItem(r1)
        scene.addItem(r2)
        scene.addItem(r3)
        new_z = scene.bring_to_front(r1)
        assert new_z is not None
        r1.setZValue(new_z)
        assert r1.zValue() > r3.zValue()

    def test_already_on_top_returns_none(self, scene):
        r1 = RectangleItem()
        r2 = RectangleItem()
        scene.addItem(r1)
        scene.addItem(r2)
        assert scene.bring_to_front(r2) is None


class TestSendToBack:
    def test_sends_item_to_bottom(self, scene):
        r1 = RectangleItem()
        r2 = EllipseItem()
        r3 = ArrowItem()
        scene.addItem(r1)
        scene.addItem(r2)
        scene.addItem(r3)
        new_z = scene.send_to_back(r3)
        assert new_z is not None
        r3.setZValue(new_z)
        assert r3.zValue() < r1.zValue()
        assert r3.zValue() > -500  # Still above blur layer

    def test_already_at_back_returns_none(self, scene):
        r1 = RectangleItem()
        r2 = RectangleItem()
        scene.addItem(r1)
        scene.addItem(r2)
        assert scene.send_to_back(r1) is None


class TestMoveUp:
    def test_swaps_with_item_above(self, scene):
        r1 = RectangleItem()
        r2 = RectangleItem()
        scene.addItem(r1)
        scene.addItem(r2)
        result = scene.move_up(r1)
        assert result is not None
        new_z, other, other_new_z = result
        assert other is r2
        r1.setZValue(new_z)
        r2.setZValue(other_new_z)
        assert r1.zValue() > r2.zValue()

    def test_already_on_top_returns_none(self, scene):
        r1 = RectangleItem()
        r2 = RectangleItem()
        scene.addItem(r1)
        scene.addItem(r2)
        assert scene.move_up(r2) is None


class TestMoveDown:
    def test_swaps_with_item_below(self, scene):
        r1 = RectangleItem()
        r2 = RectangleItem()
        scene.addItem(r1)
        scene.addItem(r2)
        result = scene.move_down(r2)
        assert result is not None
        new_z, other, other_new_z = result
        assert other is r1
        r2.setZValue(new_z)
        r1.setZValue(other_new_z)
        assert r2.zValue() < r1.zValue()

    def test_already_at_back_returns_none(self, scene):
        r1 = RectangleItem()
        r2 = RectangleItem()
        scene.addItem(r1)
        scene.addItem(r2)
        assert scene.move_down(r1) is None


class TestReorderItemCommand:
    def test_undo_redo_single_item(self, scene):
        r1 = RectangleItem()
        r2 = RectangleItem()
        scene.addItem(r1)
        scene.addItem(r2)
        old_z = r1.zValue()
        new_z = scene.bring_to_front(r1)
        cmd = ReorderItemCommand(scene, r1, old_z, new_z)
        cmd.redo()
        assert r1.zValue() == new_z
        cmd.undo()
        assert r1.zValue() == old_z

    def test_undo_redo_swap(self, scene):
        r1 = RectangleItem()
        r2 = RectangleItem()
        scene.addItem(r1)
        scene.addItem(r2)
        result = scene.move_up(r1)
        new_z, other, other_new_z = result
        cmd = ReorderItemCommand(
            scene, r1, r1.zValue(), new_z,
            other_item=other, other_old_z=other.zValue(), other_new_z=other_new_z,
        )
        old_r1_z = r1.zValue()
        old_r2_z = r2.zValue()
        cmd.redo()
        assert r1.zValue() > r2.zValue()
        cmd.undo()
        assert r1.zValue() == old_r1_z
        assert r2.zValue() == old_r2_z


class TestZOrderSerialization:
    def test_z_order_round_trips(self, scene):
        r = RectangleItem()
        scene.addItem(r)
        r.setZValue(42.0)
        data = r.serialize()
        assert data["z_order"] == 42.0

        r2 = BaseAnnotationItem.deserialize(data)
        assert r2 is not None
        assert r2.zValue() == 42.0

    def test_blur_ignores_saved_z_order(self, scene):
        b = BlurItem()
        scene.addItem(b)
        data = b.serialize()
        data["z_order"] = 999  # tamper with saved value
        b2 = BaseAnnotationItem.deserialize(data)
        assert b2.zValue() == -500
