import os
import shutil
import math

import numpy as np
import pytest
from PIL import Image

from collectmeteranalog.labeling import ziffer_data_files, load_image


class TestZifferDataFiles:
    def test_finds_jpg_files(self, tmp_image_dir):
        files = ziffer_data_files(str(tmp_image_dir))
        assert len(files) == 3
        assert all(f.endswith(".jpg") for f in files)

    def test_ignores_non_jpg(self, tmp_image_dir):
        (tmp_image_dir / "readme.txt").write_text("not an image")
        (tmp_image_dir / "photo.png").write_bytes(b"\x89PNG")
        files = ziffer_data_files(str(tmp_image_dir))
        assert len(files) == 3

    def test_empty_dir(self, tmp_path):
        files = ziffer_data_files(str(tmp_path))
        assert files == []

    def test_finds_in_subdirectories(self, tmp_image_dir):
        sub = tmp_image_dir / "sub"
        sub.mkdir()
        img = Image.new("RGB", (32, 32), color="green")
        img.save(sub / "1.0_sub.jpg")
        files = ziffer_data_files(str(tmp_image_dir))
        assert len(files) == 4

    def test_sorted_by_basename(self, tmp_image_dir):
        files = ziffer_data_files(str(tmp_image_dir))
        basenames = [os.path.basename(f) for f in files]
        assert basenames == sorted(basenames)


class TestLoadImage:
    def test_loads_first_image(self, tmp_image_dir):
        files = ziffer_data_files(str(tmp_image_dir))
        img, category, filename, idx = load_image(files, 0)
        assert isinstance(img, Image.Image)
        assert category >= 0
        assert os.path.exists(filename)
        assert idx >= 0

    def test_parses_label_with_decimal(self, tmp_image_dir):
        files = ziffer_data_files(str(tmp_image_dir))
        # Find the file starting with "3.5_"
        idx = next(i for i, f in enumerate(files) if "3.5_" in os.path.basename(f))
        img, category, filename, result_idx = load_image(files, idx)
        assert category == 3.5

    def test_parses_label_single_digit(self, tmp_path):
        img = Image.new("RGB", (32, 32), color="white")
        img.save(tmp_path / "7_simple.jpg")
        files = ziffer_data_files(str(tmp_path))
        _, category, _, _ = load_image(files, 0)
        assert category == 7.0

    def test_startlabel_skips_lower(self, tmp_image_dir):
        files = ziffer_data_files(str(tmp_image_dir))
        img, category, filename, idx = load_image(files, 0, startlabel=5.0)
        assert category >= 5.0

    def test_unparseable_label_defaults_to_zero(self, tmp_path):
        img = Image.new("RGB", (32, 32), color="gray")
        img.save(tmp_path / "x_unknown.jpg")
        files = ziffer_data_files(str(tmp_path))
        _, category, _, _ = load_image(files, 0)
        assert category == 0
