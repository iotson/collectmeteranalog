"""Additional tests for collect.py to improve coverage."""
import os
from io import BytesIO
from unittest import mock
from urllib.error import HTTPError, URLError

import pytest
from PIL import Image

import collectmeteranalog.collect as collect_mod


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _make_jpg(path, color=(128, 64, 32)):
    img = Image.new("RGB", (32, 20), color=color)
    img.save(path, format="JPEG")


# ---------------------------------------------------------------------------
# TestReadImages
# ---------------------------------------------------------------------------

class TestReadImages:
    """Tests for the readimages() function (network layer)."""

    def _all_paths_except_hour00(self, tmp_path, servername="192.168.1.1"):
        """Pre-create all hourly dirs except 00 so only one HTTP request fires."""
        today = collect_mod.yesterday(0)
        for i in range(1, 24):
            hour = f"{i:02d}"
            d = tmp_path / servername / today / hour
            d.mkdir(parents=True, exist_ok=True)

    def test_url_error_causes_exit(self, tmp_path):
        """URLError (server unreachable) must call sys.exit(1)."""
        from collectmeteranalog.collect import readimages

        self._all_paths_except_hour00(tmp_path)

        with mock.patch(
            "urllib.request.urlopen", side_effect=URLError("unreachable")
        ):
            with pytest.raises(SystemExit) as exc:
                readimages("192.168.1.1", str(tmp_path), daysback=1)
            assert exc.value.code == 1

    def test_http_error_continues(self, tmp_path):
        """HTTPError (e.g. 404) must be swallowed – no exit."""
        from collectmeteranalog.collect import readimages

        self._all_paths_except_hour00(tmp_path)

        http_err = HTTPError(url="", code=404, msg="Not Found", hdrs={}, fp=None)
        with mock.patch("urllib.request.urlopen", side_effect=http_err):
            # Should not raise
            readimages("192.168.1.1", str(tmp_path), daysback=1)

    def test_existing_path_is_skipped(self, tmp_path):
        """Pre-existing hourly directories must be skipped (no urlopen call)."""
        from collectmeteranalog.collect import readimages

        # Create ALL 24 dirs so every hour is skipped
        today = collect_mod.yesterday(0)
        for i in range(24):
            hour = f"{i:02d}"
            d = tmp_path / "192.168.1.1" / today / hour
            d.mkdir(parents=True, exist_ok=True)

        with mock.patch("urllib.request.urlopen") as mock_url:
            readimages("192.168.1.1", str(tmp_path), daysback=1)
            mock_url.assert_not_called()

    def test_download_jpeg_content_type(self, tmp_path):
        """image/jpeg content-type → saved directly via iter_content."""
        from collectmeteranalog.collect import readimages

        self._all_paths_except_hour00(tmp_path)

        buf = BytesIO()
        Image.new("RGB", (10, 10)).save(buf, format="JPEG")
        jpeg_bytes = buf.getvalue()

        html = b'<a href="/analog/20260421/00/img_abc.jpg">img.jpg</a>'
        mock_fp = mock.MagicMock()
        mock_fp.read.return_value = html

        mock_response = mock.MagicMock()
        mock_response.headers = {"Content-Type": "image/jpeg"}
        mock_response.iter_content.return_value = [jpeg_bytes]
        mock_response.__enter__ = mock.MagicMock(return_value=mock_response)
        mock_response.__exit__ = mock.MagicMock(return_value=False)

        with mock.patch("urllib.request.urlopen", return_value=mock_fp):
            with mock.patch("requests.get", return_value=mock_response):
                readimages("192.168.1.1", str(tmp_path), daysback=1)

    def test_download_non_jpeg_re_encodes(self, tmp_path):
        """Non-JPEG content-type → image re-encoded to JPEG."""
        from collectmeteranalog.collect import readimages

        self._all_paths_except_hour00(tmp_path)

        buf = BytesIO()
        Image.new("RGB", (10, 10)).save(buf, format="PNG")
        buf.seek(0)

        html = b'<a href="/analog/20260421/00/img_abc.jpg">img.jpg</a>'
        mock_fp = mock.MagicMock()
        mock_fp.read.return_value = html

        mock_response = mock.MagicMock()
        mock_response.headers = {"Content-Type": "image/png"}
        mock_response.raw = buf
        mock_response.__enter__ = mock.MagicMock(return_value=mock_response)
        mock_response.__exit__ = mock.MagicMock(return_value=False)

        with mock.patch("urllib.request.urlopen", return_value=mock_fp):
            with mock.patch("requests.get", return_value=mock_response):
                with mock.patch("PIL.Image.open", return_value=Image.new("RGB", (10, 10))):
                    readimages("192.168.1.1", str(tmp_path), daysback=1)

    def test_non_jpg_url_is_skipped(self, tmp_path):
        """URLs not ending in .jpg/.jpeg must be ignored."""
        from collectmeteranalog.collect import readimages

        self._all_paths_except_hour00(tmp_path)

        html = b'<a href="/analog/20260421/00/readme.txt">readme.txt</a>'
        mock_fp = mock.MagicMock()
        mock_fp.read.return_value = html

        with mock.patch("urllib.request.urlopen", return_value=mock_fp):
            with mock.patch("requests.get") as mock_get:
                readimages("192.168.1.1", str(tmp_path), daysback=1)
                mock_get.assert_not_called()

    def test_request_exception_breaks_retry(self, tmp_path):
        """RequestException during download breaks the retry loop gracefully."""
        from collectmeteranalog.collect import readimages
        import requests

        self._all_paths_except_hour00(tmp_path)

        html = b'<a href="/analog/20260421/00/img_abc.jpg">img.jpg</a>'
        mock_fp = mock.MagicMock()
        mock_fp.read.return_value = html

        mock_response = mock.MagicMock()
        mock_response.headers = {"Content-Type": "image/jpeg"}
        mock_response.__enter__ = mock.MagicMock(
            side_effect=requests.exceptions.RequestException("network error")
        )
        mock_response.__exit__ = mock.MagicMock(return_value=False)

        with mock.patch("urllib.request.urlopen", return_value=mock_fp):
            with mock.patch("requests.get", return_value=mock_response):
                readimages("192.168.1.1", str(tmp_path), daysback=1)  # must not raise

    def test_servername_without_prefix(self, tmp_path):
        """Servername without http:// prefix gets it prepended."""
        from collectmeteranalog.collect import readimages

        # All paths exist → no actual HTTP call needed
        today = collect_mod.yesterday(0)
        for i in range(24):
            d = tmp_path / "meter.local" / today / f"{i:02d}"
            d.mkdir(parents=True, exist_ok=True)

        with mock.patch("urllib.request.urlopen") as mock_url:
            readimages("meter.local", str(tmp_path), daysback=1)
            mock_url.assert_not_called()

    def test_servername_with_prefix(self, tmp_path):
        """Servername already containing http:// is used as-is."""
        from collectmeteranalog.collect import readimages

        today = collect_mod.yesterday(0)
        for i in range(24):
            d = tmp_path / "http://meter.local" / today / f"{i:02d}"
            d.mkdir(parents=True, exist_ok=True)

        with mock.patch("urllib.request.urlopen") as mock_url:
            readimages("http://meter.local", str(tmp_path), daysback=1)
            mock_url.assert_not_called()


# ---------------------------------------------------------------------------
# TestRemoveSimilarImages
# ---------------------------------------------------------------------------

class TestRemoveSimilarImages:

    def test_empty_input_creates_hash_file(self, tmp_path):
        """No images → empty hash file is written."""
        (tmp_path / "data").mkdir()
        collect_mod.remove_similar_images(str(tmp_path), [], "meter1")
        assert (tmp_path / "data" / "HistoricHashData.txt").exists()

    def test_unique_images_are_kept(self, tmp_path):
        """Images that differ enough are NOT removed (similarbits=0 → never duplicate)."""
        import numpy as np

        (tmp_path / "data").mkdir()
        p1 = tmp_path / "a.jpg"
        p2 = tmp_path / "b.jpg"
        # Use gradient images so hashes are meaningful
        arr1 = np.arange(32 * 20, dtype=np.uint8).reshape(20, 32)
        arr2 = (255 - arr1).astype(np.uint8)
        Image.fromarray(arr1, mode="L").convert("RGB").save(p1)
        Image.fromarray(arr2, mode="L").convert("RGB").save(p2)

        # similarbits=0 → abs(diff) < 0 is never true, nothing removed
        collect_mod.remove_similar_images(str(tmp_path), [str(p1), str(p2)], "m", similarbits=0)
        assert p1.exists()
        assert p2.exists()

    def test_duplicate_images_are_removed(self, tmp_path):
        """Identical images → one gets removed."""
        (tmp_path / "data").mkdir()
        p1 = tmp_path / "img1.jpg"
        p2 = tmp_path / "img2.jpg"
        img = Image.new("RGB", (32, 20), color=(100, 150, 200))
        img.save(p1)
        img.save(p2)

        collect_mod.remove_similar_images(
            str(tmp_path), [str(p1), str(p2)], "m", similarbits=10
        )
        remaining = sum(1 for p in (p1, p2) if p.exists())
        assert remaining == 1

    def test_saveduplicates_moves_files(self, tmp_path):
        """saveduplicates=True must move duplicates, not delete them."""
        (tmp_path / "data").mkdir()
        p1 = tmp_path / "img1.jpg"
        p2 = tmp_path / "img2.jpg"
        img = Image.new("RGB", (32, 20), color=(100, 150, 200))
        img.save(p1)
        img.save(p2)

        collect_mod.remove_similar_images(
            str(tmp_path), [str(p1), str(p2)], "m", similarbits=10, saveduplicates=True
        )
        dup_dir = tmp_path / "data" / "raw_images" / "duplicates"
        assert dup_dir.exists()
        moved = list(dup_dir.glob("*.jpg"))
        assert len(moved) >= 1

    def test_with_existing_historic_hash_data(self, tmp_path):
        """Existing hash file is loaded and new unique images are added."""
        import imagehash
        import numpy as np

        data_dir = tmp_path / "data"
        data_dir.mkdir()
        hash_file = data_dir / "HistoricHashData.txt"

        # Create a gradient image and compute its hash to write as historic entry
        arr = np.arange(32 * 20, dtype=np.uint8).reshape(20, 32)
        old_img = Image.fromarray(arr, mode="L")
        old_hash = imagehash.average_hash(old_img)
        from datetime import date, timedelta
        recent_date = (date.today() - timedelta(days=10)).strftime("%Y-%m-%d")
        hash_file.write_text(
            f"{recent_date}\toldmeter\told.jpg\t{old_hash}\n", encoding="utf-8"
        )

        # New image with inverted gradient → hash differs significantly
        arr2 = (255 - arr).astype(np.uint8)
        p = tmp_path / "new.jpg"
        Image.fromarray(arr2, mode="L").convert("RGB").save(p)

        collect_mod.remove_similar_images(str(tmp_path), [str(p)], "m", similarbits=1)

        # Hash file should now contain 2 entries (old + new)
        lines = hash_file.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 2


# ---------------------------------------------------------------------------
# TestMoveToLabelMoveMode
# ---------------------------------------------------------------------------

class TestMoveToLabelMoveMode:

    def test_move_removes_source_dir(self, tmp_path):
        """keepolddata=False must move files and delete raw_images dir."""
        raw_dir = tmp_path / "data" / "raw_images"
        raw_dir.mkdir(parents=True)
        files = []
        for i in range(3):
            p = raw_dir / f"{i}.jpg"
            _make_jpg(p)
            files.append(str(p))

        orig_raw = collect_mod.target_raw_path
        orig_label = collect_mod.target_label_path
        collect_mod.target_raw_path = "data/raw_images"
        collect_mod.target_label_path = "data/labeled"

        try:
            collect_mod.move_to_label(str(tmp_path), False, files)  # keepolddata=False
            label_dir = tmp_path / "data" / "labeled"
            assert label_dir.exists()
            assert len(list(label_dir.glob("*.jpg"))) == 3
            assert not raw_dir.exists()
        finally:
            collect_mod.target_raw_path = orig_raw
            collect_mod.target_label_path = orig_label

    def test_copy_keeps_source(self, tmp_path):
        """keepolddata=True must copy files and keep the source."""
        raw_dir = tmp_path / "data" / "raw_images"
        raw_dir.mkdir(parents=True)
        files = []
        for i in range(2):
            p = raw_dir / f"{i}.jpg"
            _make_jpg(p)
            files.append(str(p))

        orig_label = collect_mod.target_label_path
        collect_mod.target_label_path = "data/labeled"

        try:
            collect_mod.move_to_label(str(tmp_path), True, files)  # keepolddata=True
            assert all(os.path.exists(f) for f in files)
        finally:
            collect_mod.target_label_path = orig_label


# ---------------------------------------------------------------------------
# TestCollectFunction
# ---------------------------------------------------------------------------

class TestCollectFunction:

    def _patch_all(self):
        """Context manager stack that mocks all I/O-heavy helpers."""
        return (
            mock.patch("collectmeteranalog.collect.readimages"),
            mock.patch("collectmeteranalog.collect.remove_similar_images"),
            mock.patch("collectmeteranalog.collect.move_to_label"),
            mock.patch("collectmeteranalog.collect.label"),
            mock.patch("collectmeteranalog.collect.ziffer_data_files", return_value=[]),
        )

    def test_no_download_skips_readimages(self, tmp_path):
        from collectmeteranalog.collect import collect

        p1, p2, p3, p4, p5 = self._patch_all()
        with p1 as mock_read, p2, p3, p4, p5:
            collect("meter1", str(tmp_path), 3, download=False)
            mock_read.assert_not_called()

    def test_with_download_calls_readimages(self, tmp_path):
        from collectmeteranalog.collect import collect

        p1, p2, p3, p4, p5 = self._patch_all()
        with p1 as mock_read, p2, p3, p4, p5:
            collect("meter1", str(tmp_path), 3, download=True)
            mock_read.assert_called_once()

    def test_collect_calls_label(self, tmp_path):
        from collectmeteranalog.collect import collect

        p1, p2, p3, p4, p5 = self._patch_all()
        with p1, p2, p3, p4 as mock_label, p5:
            collect("meter1", str(tmp_path), 3, download=False, startlabel=1.5, ticksteps=2)
            mock_label.assert_called_once()
            call_kwargs = mock_label.call_args
            assert call_kwargs[1].get("ticksteps") == 2
