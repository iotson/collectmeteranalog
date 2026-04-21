import os
import pytest
from PIL import Image

# Enable PySide6 in headless (offscreen) mode so GUI tests run without a display.
# This must be set before any Qt import happens.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture
def tmp_image_dir(tmp_path):
    """Create a temp directory with test images labeled in the expected format."""
    for val in [0.0, 3.5, 7.2]:
        img = Image.new("RGB", (64, 64), color="red")
        img.save(tmp_path / f"{val:.1f}_test_{val}.jpg")
    return tmp_path


@pytest.fixture
def single_image(tmp_path):
    """Create a single test image."""
    img = Image.new("RGB", (64, 64), color="blue")
    path = tmp_path / "5.0_meter.jpg"
    img.save(path)
    return path
