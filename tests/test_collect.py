from collectmeteranalog.collect import yesterday, ziffer_data_files


class TestYesterday:
    def test_returns_string(self):
        result = yesterday()
        assert isinstance(result, str)
        assert len(result) == 8  # YYYYMMDD

    def test_days_before(self):
        day1 = yesterday(1)
        day3 = yesterday(3)
        assert day1 != day3
        assert int(day1) > int(day3)

    def test_zero_days_is_today(self):
        from datetime import date
        today = date.today().strftime("%Y%m%d")
        assert yesterday(0) == today


class TestCollectZifferDataFiles:
    def test_finds_jpg_files(self, tmp_image_dir):
        files = ziffer_data_files(str(tmp_image_dir))
        assert len(files) == 3

    def test_empty_dir(self, tmp_path):
        files = ziffer_data_files(str(tmp_path))
        assert files == []
