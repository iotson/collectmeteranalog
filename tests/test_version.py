from collectmeteranalog.__version__ import __version__


def test_version_format():
    parts = __version__.split(".")
    assert len(parts) == 3
    assert all(p.isdigit() for p in parts)


def test_version_is_current():
    assert __version__ == "1.2.0"
