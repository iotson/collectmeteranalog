import sys
from unittest import mock

import pytest


class TestCLI:
    def test_no_args_shows_help(self):
        from collectmeteranalog.__main__ import main
        with mock.patch("sys.argv", ["prog"]):
            with pytest.raises(SystemExit) as exc:
                main()
            assert exc.value.code == 1

    def test_version_flag(self, capsys):
        from collectmeteranalog.__main__ import main
        with mock.patch("sys.argv", ["prog", "--version"]):
            with pytest.raises(SystemExit) as exc:
                main()
            assert exc.value.code == 0
        assert "1.2.0" in capsys.readouterr().out

    def test_labeling_missing_path(self):
        from collectmeteranalog.__main__ import main
        with mock.patch("sys.argv", ["prog", "--labeling", "/nonexistent/path"]):
            with pytest.raises(SystemExit):
                main()

    def test_ticksteps_clamped_low(self):
        """ticksteps < 1 should be clamped to 1."""
        from collectmeteranalog.__main__ import main
        with mock.patch("sys.argv", ["prog", "--labeling", "/tmp", "--ticksteps", "0"]):
            with mock.patch("collectmeteranalog.__main__.load_interpreter"):
                with mock.patch("collectmeteranalog.__main__.label") as mock_label:
                    main()
                    assert mock_label.call_args[1]["ticksteps"] == 1

    def test_ticksteps_clamped_high(self):
        """ticksteps > 5 should be clamped to 1."""
        from collectmeteranalog.__main__ import main
        with mock.patch("sys.argv", ["prog", "--labeling", "/tmp", "--ticksteps", "10"]):
            with mock.patch("collectmeteranalog.__main__.load_interpreter"):
                with mock.patch("collectmeteranalog.__main__.label") as mock_label:
                    main()
                    assert mock_label.call_args[1]["ticksteps"] == 1

    def test_labeling_calls_label(self, tmp_path):
        from collectmeteranalog.__main__ import main
        with mock.patch("sys.argv", ["prog", "--labeling", str(tmp_path)]):
            with mock.patch("collectmeteranalog.__main__.load_interpreter"):
                with mock.patch("collectmeteranalog.__main__.label") as mock_label:
                    main()
                    mock_label.assert_called_once()
                    assert mock_label.call_args[0][0] == str(tmp_path)

    def test_labeling_with_labelfile(self, tmp_path):
        from collectmeteranalog.__main__ import main
        lf = str(tmp_path / "labels.csv")
        with mock.patch("sys.argv", ["prog", "--labeling", str(tmp_path), "--labelfile", lf]):
            with mock.patch("collectmeteranalog.__main__.load_interpreter"):
                with mock.patch("collectmeteranalog.__main__.label") as mock_label:
                    main()
                    args = mock_label.call_args
                    assert args[0][0] == str(tmp_path)
                    assert args[0][2] == lf

    def test_collect_calls_collect(self):
        from collectmeteranalog.__main__ import main
        with mock.patch("sys.argv", ["prog", "--collect", "192.168.1.1"]):
            with mock.patch("collectmeteranalog.__main__.load_interpreter"):
                with mock.patch("collectmeteranalog.__main__.collect") as mock_collect:
                    main()
                    mock_collect.assert_called_once()

    def test_no_collect_no_labeling_exits(self):
        """Neither --collect nor --labeling should print error and exit."""
        from collectmeteranalog.__main__ import main
        with mock.patch("sys.argv", ["prog", "--model", "off"]):
            with mock.patch("collectmeteranalog.__main__.load_interpreter"):
                with pytest.raises(SystemExit) as exc:
                    main()
                assert exc.value.code == 1
