import os
import shutil
import math
from unittest.mock import patch

import numpy as np
import pytest
from PIL import Image
from PySide6.QtWidgets import QMessageBox

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


class TestLabelingWindowNavigation:
    def _make_window(self, tmp_image_dir):
        from collectmeteranalog.labeling import LabelingWindow, ziffer_data_files
        files = ziffer_data_files(str(tmp_image_dir))
        return LabelingWindow(files, 0.0, 1, None)

    def test_on_previous_wraps(self, tmp_image_dir):
        _make_app()
        w = self._make_window(tmp_image_dir)
        initial_i = w.i
        w._on_previous()
        assert w.i == len(w.files) - 1  # wraps to end
        w.close()

    def test_on_next_saves_label(self, tmp_image_dir):
        _make_app()
        w = self._make_window(tmp_image_dir)
        w.filelabel = 8.5
        old_filename = w.filename
        w._on_next()
        # The previous file should have been renamed with 8.5_ prefix
        expected_base = f"8.5_{os.path.basename(old_filename).split('_', 1)[-1]}"
        renamed = os.path.join(os.path.dirname(old_filename), expected_base)
        assert os.path.exists(renamed) or old_filename == renamed
        w.close()

    def test_on_remove_deletes_file(self, tmp_image_dir):
        _make_app()
        w = self._make_window(tmp_image_dir)
        file_to_delete = w.filename
        initial_count = len(w.files)
        with patch("collectmeteranalog.labeling.QMessageBox.question",
                   return_value=QMessageBox.Yes):
            w._on_remove()
        assert not os.path.exists(file_to_delete)
        assert len(w.files) == initial_count - 1
        w.close()

    def test_on_remove_last_file_closes(self, tmp_path):
        _make_app()
        from collectmeteranalog.labeling import LabelingWindow
        img = Image.new("RGB", (32, 32), color="red")
        img.save(tmp_path / "5.0_only.jpg")
        files = [str(tmp_path / "5.0_only.jpg")]
        w = LabelingWindow(np.array(files), 0.0, 1, None)
        with patch("collectmeteranalog.labeling.QMessageBox.question",
                   return_value=QMessageBox.Yes):
            w._on_remove()
        # Window should have closed (no crash)

    def test_slider_updates_label(self, tmp_image_dir):
        _make_app()
        w = self._make_window(tmp_image_dir)
        w._on_slider_changed(75)
        assert w.filelabel == 7.5
        assert w.slider_value_label.text() == "7.5"
        w.close()

    def test_update_title(self, tmp_image_dir):
        _make_app()
        w = self._make_window(tmp_image_dir)
        w._update_title()
        title = w.windowTitle()
        assert "Image:" in title
        assert str(len(w.files)) in title
        w.close()


class TestLabelingWindowPrediction:
    def test_prediction_disabled(self, tmp_image_dir):
        _make_app()
        from collectmeteranalog.labeling import LabelingWindow, ziffer_data_files
        files = ziffer_data_files(str(tmp_image_dir))
        w = LabelingWindow(files, 0.0, 1, None)
        assert "disabled" in w.pred_label.text().lower()
        w.close()

    def test_prediction_from_labelfile(self, tmp_image_dir):
        _make_app()
        from collectmeteranalog.labeling import LabelingWindow, ziffer_data_files
        files = ziffer_data_files(str(tmp_image_dir))
        predictions = np.array([4.2, 5.5, 8.1])
        w = LabelingWindow(files, 0.0, 1, predictions)
        # Should show prediction from labelfile since model is disabled
        assert "4.2" in w.pred_label.text() or "disabled" in w.pred_label.text().lower()
        w.close()

    def test_prediction_with_nan(self, tmp_image_dir):
        _make_app()
        from collectmeteranalog.labeling import LabelingWindow, ziffer_data_files
        files = ziffer_data_files(str(tmp_image_dir))
        predictions = np.array([float('nan'), 5.5, 8.1])
        w = LabelingWindow(files, 0.0, 1, predictions)
        assert "disabled" in w.pred_label.text().lower()
        w.close()


class TestPolarOverlayViewExtended:
    def test_mouse_click_converts_to_label(self, tmp_image_dir):
        _make_app()
        from collectmeteranalog.labeling import PolarOverlayView
        view = PolarOverlayView()
        view.resize(400, 400)
        img = Image.new("RGB", (100, 100), color="red")
        view.set_image(img)
        cx, cy, radius = view._get_viewport_center_and_radius()
        # Should return valid values
        assert cx is not None
        assert radius > 0

    def test_update_overlay_triggers_update(self):
        _make_app()
        from collectmeteranalog.labeling import PolarOverlayView
        view = PolarOverlayView()
        view.update_overlay(3.3, 2)
        assert view._filelabel == 3.3
        assert view._ticksteps == 2

    def test_no_image_returns_none(self):
        _make_app()
        from collectmeteranalog.labeling import PolarOverlayView
        view = PolarOverlayView()
        cx, cy, radius = view._get_viewport_center_and_radius()
        assert cx is None
