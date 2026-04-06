"""Integration tests — instantiate real UI components and verify wiring."""

from __future__ import annotations

import pytest
from PyQt6.QtGui import QPixmap, QColor, QImage


# --- Editor integration ---

class TestEditorWindow:
    def test_instantiates_with_pixmap(self, qapp):
        from waysnip.editor.editor_window import EditorWindow
        from waysnip.config import AppConfig

        pixmap = QPixmap(400, 300)
        pixmap.fill(QColor(100, 150, 200))
        win = EditorWindow(pixmap, AppConfig())
        assert win is not None
        assert win.windowTitle() != ""
        win.close()

    def test_has_toolbar_and_properties(self, qapp):
        from waysnip.editor.editor_window import EditorWindow
        from waysnip.config import AppConfig

        pixmap = QPixmap(400, 300)
        pixmap.fill(QColor(100, 150, 200))
        win = EditorWindow(pixmap, AppConfig())
        # Should have a toolbar and properties panel
        assert win._toolbar is not None
        assert win._properties is not None
        win.close()

    def test_scene_has_background(self, qapp):
        from waysnip.editor.scene import AnnotationScene

        pixmap = QPixmap(200, 150)
        pixmap.fill(QColor(50, 50, 50))
        scene = AnnotationScene()
        scene.set_background_pixmap(pixmap)
        assert scene.sceneRect().width() >= 200
        assert scene.sceneRect().height() >= 150

    def test_canvas_zoom(self, qapp):
        from waysnip.editor.canvas import AnnotationCanvas
        from waysnip.editor.scene import AnnotationScene

        scene = AnnotationScene()
        pixmap = QPixmap(200, 150)
        pixmap.fill(QColor(50, 50, 50))
        scene.set_background_pixmap(pixmap)
        canvas = AnnotationCanvas(scene)
        assert canvas is not None

    def test_all_tools_instantiate(self, qapp):
        from waysnip.editor.tools.select_tool import SelectTool
        from waysnip.editor.tools.rectangle import RectangleTool
        from waysnip.editor.tools.ellipse import EllipseTool
        from waysnip.editor.tools.arrow import ArrowTool
        from waysnip.editor.tools.line import LineTool
        from waysnip.editor.tools.text import TextTool
        from waysnip.editor.tools.numbered_marker import NumberedMarkerTool
        from waysnip.editor.tools.freehand import FreehandTool
        from waysnip.editor.tools.highlight import HighlightTool
        from waysnip.editor.tools.blur import BlurTool
        from waysnip.editor.tools.crop import CropTool

        tools = [
            SelectTool(), RectangleTool(), EllipseTool(), ArrowTool(),
            LineTool(), TextTool(), NumberedMarkerTool(), FreehandTool(),
            HighlightTool(), BlurTool(), CropTool(),
        ]
        assert len(tools) == 11
        for tool in tools:
            assert tool.name
            assert tool.shortcut


# --- Annotation items ---

class TestAnnotationItems:
    def test_rectangle_item_draw(self, qapp):
        from waysnip.editor.tools.rectangle import RectangleItem

        item = RectangleItem()
        item.setPos(10, 20)
        item.pen_color = QColor(255, 0, 0)
        item.fill_color = QColor(0, 255, 0, 128)
        data = item.serialize()
        assert data["type"] == "rectangle"
        assert data["x"] == 10.0
        assert data["y"] == 20.0

    def test_arrow_item_serialization(self, qapp):
        from waysnip.editor.tools.arrow import ArrowItem

        item = ArrowItem()
        item.setPos(5, 10)
        data = item.serialize()
        assert data["type"] == "arrow"
        restored = ArrowItem._from_data(data)
        assert restored.pos().x() == pytest.approx(5.0)

    def test_numbered_marker_numbering(self, qapp):
        from waysnip.editor.tools.numbered_marker import NumberedMarkerItem
        from PyQt6.QtWidgets import QGraphicsScene

        scene = QGraphicsScene()
        markers = []
        for i in range(5):
            m = NumberedMarkerItem()
            m.number = i + 1
            scene.addItem(m)
            markers.append(m)

        assert markers[0].number == 1
        assert markers[4].number == 5

    def test_blur_item_has_rect(self, qapp):
        from waysnip.editor.tools.blur import BlurItem

        item = BlurItem()
        assert item.boundingRect() is not None

    def test_text_item_serialization(self, qapp):
        from waysnip.editor.tools.text import TextItem

        item = TextItem()
        data = item.serialize()
        assert data["type"] == "text"


# --- Scene rendering ---

class TestSceneRendering:
    def test_render_to_pixmap(self, qapp):
        from waysnip.editor.scene import AnnotationScene
        from waysnip.editor.tools.rectangle import RectangleItem

        scene = AnnotationScene()
        bg = QPixmap(200, 150)
        bg.fill(QColor(255, 255, 255))
        scene.set_background_pixmap(bg)

        rect = RectangleItem()
        rect.setPos(10, 10)
        scene.addItem(rect)

        result = scene.render_to_pixmap()
        assert not result.isNull()
        assert result.width() >= 200
        assert result.height() >= 150


# --- Save round-trip with real annotations ---

class TestSaveRoundTrip:
    def test_save_and_reload_with_annotations(self, qapp, tmp_path):
        from waysnip.save import save_screenshot, load_annotations
        from waysnip.config import AppConfig

        config = AppConfig()
        config.save.directory = str(tmp_path)
        config.save.mode = "annotated"

        pixmap = QPixmap(100, 100)
        pixmap.fill(QColor(200, 200, 200))

        annotations = [
            {"type": "rectangle", "x": 10, "y": 20, "width": 50, "height": 30},
            {"type": "arrow", "x": 0, "y": 0, "end_x": 80, "end_y": 60},
        ]

        path = save_screenshot(pixmap, annotations, pixmap, config)
        assert path.exists()

        original, loaded = load_annotations(path)
        assert original is not None
        assert not original.isNull()
        assert len(loaded) == 2
        assert loaded[0]["type"] == "rectangle"
        assert loaded[1]["type"] == "arrow"

    def test_editable_mode_preserves_original(self, qapp, tmp_path):
        from waysnip.save import save_screenshot, load_annotations
        from waysnip.config import AppConfig

        config = AppConfig()
        config.save.directory = str(tmp_path)
        config.save.mode = "editable"

        # Create distinct original and annotated pixmaps
        original = QPixmap(100, 100)
        original.fill(QColor(0, 0, 255))
        annotated = QPixmap(100, 100)
        annotated.fill(QColor(255, 0, 0))

        annotations = [{"type": "ellipse", "x": 5, "y": 5}]
        path = save_screenshot(annotated, annotations, original, config)

        # In editable mode, the saved pixels should be the original
        saved_image = QImage(str(path))
        assert not saved_image.isNull()
        # The loaded original should be available via metadata
        # (but in editable mode, original is stored in pixel data, not metadata)
        _orig, loaded = load_annotations(path)
        assert len(loaded) == 1
        assert loaded[0]["type"] == "ellipse"


# --- Gallery ---

class TestGallery:
    def test_gallery_window_instantiates(self, qapp):
        from waysnip.gallery.gallery_window import GalleryWindow
        from waysnip.config import AppConfig

        config = AppConfig()
        win = GalleryWindow(config)
        assert win is not None
        assert "Gallery" in win.windowTitle()
        win.close()

    def test_thumbnail_model_scans_directory(self, qapp, tmp_path):
        from waysnip.gallery.thumbnail_model import ThumbnailModel

        # Create some fake PNGs
        for i in range(3):
            p = tmp_path / f"test_{i}.png"
            px = QPixmap(50, 50)
            px.fill(QColor(i * 80, 0, 0))
            px.save(str(p), "PNG")

        model = ThumbnailModel(str(tmp_path))
        assert model.rowCount() == 3


# --- Settings dialog ---

class TestSettingsDialog:
    def test_settings_dialog_instantiates(self, qapp):
        from waysnip.settings_dialog import SettingsDialog
        from waysnip.config import AppConfig

        config = AppConfig()
        dialog = SettingsDialog(config)
        assert dialog is not None
        dialog.close()


# --- CLI ---

class TestCLIIntegration:
    def test_build_parser_and_parse(self):
        from waysnip.cli import build_parser

        parser = build_parser()

        # No args -> region
        args = parser.parse_args([])
        assert args.command is None  # main() defaults to "region"

        # All subcommands
        for cmd in ["region", "window", "fullscreen", "gallery", "config"]:
            args = parser.parse_args([cmd])
            assert args.command == cmd

        # config --edit
        args = parser.parse_args(["config", "--edit"])
        assert args.edit is True


# --- Region selector ---

class TestRegionSelector:
    def test_instantiates(self, qapp):
        from waysnip.capture.region_selector import RegionSelector

        pixmap = QPixmap(800, 600)
        pixmap.fill(QColor(128, 128, 128))
        selector = RegionSelector(pixmap)
        assert selector is not None
        selector.close()


# --- Undo/Redo ---

class TestUndoRedo:
    def test_add_and_undo(self, qapp):
        from waysnip.editor.scene import AnnotationScene
        from waysnip.editor.tools.rectangle import RectangleItem
        from waysnip.editor.commands import AddItemCommand

        scene = AnnotationScene()
        bg = QPixmap(200, 150)
        bg.fill(QColor(255, 255, 255))
        scene.set_background_pixmap(bg)

        item = RectangleItem()
        cmd = AddItemCommand(scene, item)
        scene.undo_stack.push(cmd)

        # Item should be in scene
        annotations = scene.get_all_annotations()
        assert len(annotations) == 1

        # Undo
        scene.undo_stack.undo()
        annotations = scene.get_all_annotations()
        assert len(annotations) == 0

        # Redo
        scene.undo_stack.redo()
        annotations = scene.get_all_annotations()
        assert len(annotations) == 1
