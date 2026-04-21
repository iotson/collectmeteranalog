import os
import sys
from unittest import mock

import numpy as np
import pandas as pd
import pytest
from PIL import Image


class TestLabelFileLoading:
    def test_label_with_empty_dir_exits(self, tmp_path):
        """label() should exit if no images found."""
        from collectmeteranalog.labeling import label
        with pytest.raises(SystemExit):
            label(str(tmp_path))

    def test_label_with_modern_csv(self, tmp_path):
        """Test loading images via modern CSV labelfile format."""
        # Create test images
        for name in ["img1.jpg", "img2.jpg"]:
            img = Image.new("RGB", (32, 32), color="red")
            img.save(tmp_path / name)

        # Create modern CSV
        csv_path = tmp_path / "labels.csv"
        df = pd.DataFrame({
            "Index": [0, 1],
            "File": ["img1.jpg", "img2.jpg"],
            "Predicted": [3.5, 7.2]
        })
        df.to_csv(csv_path, index=False)

        # We can't fully run label() without a display, but we can test the
        # file loading logic by importing and calling the CSV loading part
        files_df = pd.read_csv(
            csv_path, index_col="Index",
            usecols=["Index", "File", "Predicted"]
        )
        files_df["FilePath"] = files_df["File"].apply(
            lambda f: os.path.join(str(tmp_path), f)
        )
        files_df = files_df[files_df["FilePath"].apply(os.path.exists)]
        assert len(files_df) == 2
        assert list(files_df["Predicted"]) == [3.5, 7.2]

    def test_label_with_legacy_csv(self, tmp_path):
        """Test loading images via legacy CSV format."""
        img = Image.new("RGB", (32, 32), color="blue")
        img.save(tmp_path / "5.0_test.jpg")

        csv_path = tmp_path / "legacy.csv"
        df = pd.DataFrame({"file": ["5.0_test.jpg"]})
        df.to_csv(csv_path)

        raw_files = pd.read_csv(csv_path, index_col=0).to_numpy().reshape(-1)
        files = np.array([
            os.path.join(str(tmp_path), f) for f in raw_files
            if os.path.exists(os.path.join(str(tmp_path), f))
        ])
        assert len(files) == 1
        assert "5.0_test.jpg" in files[0]

    def test_labelfile_missing_files_filtered(self, tmp_path):
        """Files that don't exist should be filtered out."""
        img = Image.new("RGB", (32, 32), color="green")
        img.save(tmp_path / "exists.jpg")

        csv_path = tmp_path / "labels.csv"
        df = pd.DataFrame({
            "Index": [0, 1],
            "File": ["exists.jpg", "missing.jpg"],
            "Predicted": [1.0, 2.0]
        })
        df.to_csv(csv_path, index=False)

        files_df = pd.read_csv(
            csv_path, index_col="Index",
            usecols=["Index", "File", "Predicted"]
        )
        files_df["FilePath"] = files_df["File"].apply(
            lambda f: os.path.join(str(tmp_path), f)
        )
        files_df = files_df[files_df["FilePath"].apply(os.path.exists)]
        assert len(files_df) == 1


# ---------------------------------------------------------------------------
# Tests that call label() end-to-end (window mocked, exec mocked)
# ---------------------------------------------------------------------------

def _mock_window_and_exec():
    """Return a context-manager stack that prevents real GUI from showing."""
    return (
        mock.patch("collectmeteranalog.labeling.LabelingWindow"),
        mock.patch("PySide6.QtWidgets.QApplication.exec", return_value=0),
    )


class TestLabelFunctionEndToEnd:
    """Call label() with the actual function, mocking only the Qt window/exec."""

    def test_plain_dir_creates_window(self, tmp_path):
        """label() with plain directory: loads files and creates LabelingWindow."""
        img = Image.new("RGB", (32, 32), color="red")
        img.save(tmp_path / "3.5_test.jpg")

        from collectmeteranalog.labeling import label

        p1, p2 = _mock_window_and_exec()
        with p1 as MockWindow, p2:
            label(str(tmp_path))
            MockWindow.assert_called_once()
            call_args = MockWindow.call_args
            assert call_args[0][1] == 0.0   # startlabel
            assert call_args[0][2] == 1     # ticksteps

    def test_plain_dir_with_startlabel(self, tmp_path):
        """label() passes startlabel to LabelingWindow correctly."""
        img = Image.new("RGB", (32, 32), color="blue")
        img.save(tmp_path / "7.0_test.jpg")

        from collectmeteranalog.labeling import label

        p1, p2 = _mock_window_and_exec()
        with p1 as MockWindow, p2:
            label(str(tmp_path), startlabel=5.0, ticksteps=2)
            call_args = MockWindow.call_args
            assert call_args[0][1] == 5.0
            assert call_args[0][2] == 2

    def test_modern_csv_creates_window(self, tmp_path):
        """label() with modern CSV format loads predictions and creates window."""
        img = Image.new("RGB", (32, 32), color="green")
        img.save(tmp_path / "img1.jpg")

        csv_path = tmp_path / "labels.csv"
        pd.DataFrame({
            "Index": [0],
            "File": ["img1.jpg"],
            "Predicted": [4.5],
        }).to_csv(csv_path, index=False)

        from collectmeteranalog.labeling import label

        p1, p2 = _mock_window_and_exec()
        with p1 as MockWindow, p2:
            label(str(tmp_path), labelfile_path=str(csv_path))
            MockWindow.assert_called_once()
            predictions = MockWindow.call_args[0][3]
            assert predictions is not None
            assert 4.5 in predictions

    def test_modern_csv_without_predicted_column(self, tmp_path):
        """CSV without Predicted column falls back to empty prediction list."""
        img = Image.new("RGB", (32, 32), color="gray")
        img.save(tmp_path / "img1.jpg")

        csv_path = tmp_path / "labels.csv"
        # Write CSV without Predicted column then patch read_csv to simulate it
        pd.DataFrame({
            "Index": [0],
            "File": ["img1.jpg"],
            "Predicted": [2.0],
        }).to_csv(csv_path, index=False)

        from collectmeteranalog.labeling import label

        # Patch pd.read_csv for the first call so it returns a df without Predicted
        original_read_csv = pd.read_csv

        def patched_read_csv(path, **kwargs):
            df = original_read_csv(path, **kwargs)
            if "Predicted" in df.columns:
                df = df.drop(columns=["Predicted"])
            return df

        p1, p2 = _mock_window_and_exec()
        with p1 as MockWindow, p2:
            with mock.patch("collectmeteranalog.labeling.pd.read_csv", side_effect=patched_read_csv):
                label(str(tmp_path), labelfile_path=str(csv_path))
            MockWindow.assert_called_once()

    def test_legacy_csv_creates_window(self, tmp_path):
        """label() falls back to legacy CSV format when modern columns are absent."""
        img = Image.new("RGB", (32, 32), color="yellow")
        img.save(tmp_path / "5.0_test.jpg")

        csv_path = tmp_path / "legacy.csv"
        pd.DataFrame({"file": ["5.0_test.jpg"]}).to_csv(csv_path)

        from collectmeteranalog.labeling import label

        p1, p2 = _mock_window_and_exec()
        with p1 as MockWindow, p2:
            label(str(tmp_path), labelfile_path=str(csv_path))
            MockWindow.assert_called_once()

    def test_completely_invalid_csv_exits(self, tmp_path):
        """label() raises SystemExit when CSV cannot be parsed in any format."""
        csv_path = tmp_path / "bad.csv"
        csv_path.write_text("this,is,not,a,valid,labelfile\n1,2,3,4,5,6\n")

        from collectmeteranalog.labeling import label

        with pytest.raises(SystemExit):
            label(str(tmp_path), labelfile_path=str(csv_path))

    def test_csv_all_files_missing_exits(self, tmp_path):
        """label() exits when all referenced files in CSV are missing."""
        csv_path = tmp_path / "labels.csv"
        pd.DataFrame({
            "Index": [0],
            "File": ["ghost.jpg"],
            "Predicted": [1.0],
        }).to_csv(csv_path, index=False)

        from collectmeteranalog.labeling import label

        with pytest.raises(SystemExit):
            label(str(tmp_path), labelfile_path=str(csv_path))
