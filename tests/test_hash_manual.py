"""Tests for hash_manual.py (standalone script with module-level execution)."""
import importlib
import sys

import pytest
from PIL import Image


class TestHashManualModule:

    def test_module_runs_without_error(self, tmp_path, monkeypatch):
        """
        The module executes top-level code on import.
        With an empty source dir the hash file is created but empty.
        """
        monkeypatch.chdir(tmp_path)
        (tmp_path / "data").mkdir()

        # Remove cached module so the top-level code runs fresh
        sys.modules.pop("collectmeteranalog.hash_manual", None)

        import collectmeteranalog.hash_manual  # noqa: F401

        hash_file = tmp_path / "data" / "HistoricHashData.txt"
        assert hash_file.exists()
        # Empty source dir → empty hash file
        assert hash_file.read_text(encoding="utf-8") == ""

    def test_calculate_hash_empty_list(self, tmp_path, monkeypatch):
        """calculate_hash on an empty list returns an empty list."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "data").mkdir()

        sys.modules.pop("collectmeteranalog.hash_manual", None)
        import collectmeteranalog.hash_manual as hm

        result = hm.calculate_hash([], "test_meter")
        assert result == []

    def test_calculate_hash_with_image(self, tmp_path, monkeypatch):
        """calculate_hash returns one entry per valid image."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "data").mkdir()

        img_path = tmp_path / "test.jpg"
        Image.new("RGB", (64, 64), color="red").save(img_path)

        sys.modules.pop("collectmeteranalog.hash_manual", None)
        import collectmeteranalog.hash_manual as hm

        result = hm.calculate_hash([str(img_path)], "test_meter")
        assert len(result) == 1
        assert result[0][1] == str(img_path)
        assert result[0][2] == "test_meter"

    def test_calculate_hash_skips_corrupt_file(self, tmp_path, monkeypatch):
        """calculate_hash silently skips files that cannot be opened."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "data").mkdir()

        bad = tmp_path / "corrupt.jpg"
        bad.write_bytes(b"not an image")

        sys.modules.pop("collectmeteranalog.hash_manual", None)
        import collectmeteranalog.hash_manual as hm

        result = hm.calculate_hash([str(bad)], "test_meter")
        assert result == []
