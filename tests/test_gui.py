import math
import os

import numpy as np
import pytest
from PIL import Image

from collectmeteranalog.labeling import ziffer_data_files, load_image

# GUI tests require a display; skip if unavailable
pytestmark = pytest.mark.skipif(
    os.environ.get("DISPLAY") is None and os.environ.get("WAYLAND_DISPLAY") is None
    and not os.environ.get("QT_QPA_PLATFORM"),
    reason="No display available for GUI tests"
)


def _make_app():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class TestPolarOverlayView:
    def test_set_image(self, tmp_image_dir):
        _make_app()
        from collectmeteranalog.labeling import PolarOverlayView
        view = PolarOverlayView()
        img = Image.new("RGB", (100, 100), color="red")
        view.set_image(img)
        assert view._pixmap_item is not None

    def test_viewport_center_and_radius(self, tmp_image_dir):
        _make_app()
        from collectmeteranalog.labeling import PolarOverlayView
        view = PolarOverlayView()
        view.resize(400, 400)
        img = Image.new("RGB", (100, 100), color="blue")
        view.set_image(img)
        cx, cy, radius = view._get_viewport_center_and_radius()
        assert cx is not None
        assert cy is not None
        assert radius > 0

    def test_grid_toggle(self):
        _make_app()
        from collectmeteranalog.labeling import PolarOverlayView
        view = PolarOverlayView()
        assert view._grid_visible is True
        view.set_grid_visible(False)
        assert view._grid_visible is False
        view.set_grid_visible(True)
        assert view._grid_visible is True

    def test_update_overlay_stores_params(self):
        _make_app()
        from collectmeteranalog.labeling import PolarOverlayView
        view = PolarOverlayView()
        view.update_overlay(5.5, 2)
        assert view._filelabel == 5.5
        assert view._ticksteps == 2


class TestLabelingWindow:
    def test_window_creation(self, tmp_image_dir):
        _make_app()
        from collectmeteranalog.labeling import LabelingWindow
        files = ziffer_data_files(str(tmp_image_dir))
        window = LabelingWindow(files, 0.0, 1, None)
        assert window.filelabel >= 0.0
        assert window.i >= 0
        assert len(window.files) == 3
        window.close()

    def test_change_label(self, tmp_image_dir):
        _make_app()
        from collectmeteranalog.labeling import LabelingWindow
        files = ziffer_data_files(str(tmp_image_dir))
        window = LabelingWindow(files, 0.0, 1, None)
        initial = window.filelabel
        window._change_label(0.1)
        assert window.filelabel == round((initial + 0.1) % 10, 1)
        window.close()

    def test_change_label_wraps(self, tmp_image_dir):
        _make_app()
        from collectmeteranalog.labeling import LabelingWindow
        files = ziffer_data_files(str(tmp_image_dir))
        window = LabelingWindow(files, 0.0, 1, None)
        window.filelabel = 9.9
        window._change_label(0.1)
        assert window.filelabel == 0.0
        window.close()

    def test_set_filelabel(self, tmp_image_dir):
        _make_app()
        from collectmeteranalog.labeling import LabelingWindow
        files = ziffer_data_files(str(tmp_image_dir))
        window = LabelingWindow(files, 0.0, 1, None)
        window.set_filelabel(7.3)
        assert window.filelabel == 7.3
        window.close()

    def test_toggle_grid(self, tmp_image_dir):
        _make_app()
        from collectmeteranalog.labeling import LabelingWindow
        files = ziffer_data_files(str(tmp_image_dir))
        window = LabelingWindow(files, 0.0, 1, None)
        assert window.usegrid is True
        window._on_toggle_grid()
        assert window.usegrid is False
        window._on_toggle_grid()
        assert window.usegrid is True
        window.close()
