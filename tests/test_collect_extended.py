import os
import shutil

import pytest
from PIL import Image

from collectmeteranalog.collect import (
    yesterday, ziffer_data_files, save_hash_file, load_hash_file,
    move_to_label
)


class TestSaveAndLoadHashFile:
    def test_roundtrip(self, tmp_path):
        import imagehash
        img = Image.new("RGB", (32, 20), color="red")
        h = imagehash.average_hash(img)
        data = [[h, "test.jpg", "meter1", "2026-04-21"]]

        hashfile = str(tmp_path / "hashes.txt")
        save_hash_file(data, hashfile)
        assert os.path.exists(hashfile)

        loaded = load_hash_file(hashfile)
        assert len(loaded) == 1
        assert loaded[0][1] == "test.jpg"
        assert loaded[0][2] == "meter1"
        assert loaded[0][3] == "2026-04-21"

    def test_load_nonexistent_file(self, tmp_path):
        result = load_hash_file(str(tmp_path / "nonexistent.txt"))
        assert result == []

    def test_save_empty_list(self, tmp_path):
        hashfile = str(tmp_path / "empty.txt")
        save_hash_file([], hashfile)
        assert os.path.exists(hashfile)
        loaded = load_hash_file(hashfile)
        assert loaded == []


class TestMoveToLabel:
    def test_move_files(self, tmp_path):
        # Setup source files
        src = tmp_path / "raw"
        src.mkdir()
        for i in range(3):
            img = Image.new("RGB", (32, 32), color="blue")
            img.save(src / f"{i}.0_test{i}.jpg")

        files = [str(f) for f in sorted(src.glob("*.jpg"))]
        label_dir = tmp_path / "data" / "labeled"

        # Monkey-patch the target_label_path
        import collectmeteranalog.collect as collect_mod
        orig = collect_mod.target_label_path
        collect_mod.target_label_path = str(label_dir.relative_to(tmp_path))

        try:
            move_to_label(str(tmp_path), True, files)  # keepolddata=True (copy)
            assert label_dir.exists()
            assert len(list(label_dir.glob("*.jpg"))) == 3
            # Source files should still exist (copy mode)
            assert all(os.path.exists(f) for f in files)
        finally:
            collect_mod.target_label_path = orig


class TestZifferDataFilesCollect:
    def test_finds_nested_files(self, tmp_path):
        sub1 = tmp_path / "a" / "b"
        sub1.mkdir(parents=True)
        sub2 = tmp_path / "c"
        sub2.mkdir()
        Image.new("RGB", (10, 10)).save(sub1 / "1.0_img.jpg")
        Image.new("RGB", (10, 10)).save(sub2 / "2.0_img.jpg")
        Image.new("RGB", (10, 10)).save(tmp_path / "3.0_img.jpg")
        files = ziffer_data_files(str(tmp_path))
        assert len(files) == 3
