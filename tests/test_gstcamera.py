import pytest
from gst_camera import GstCamera
from pyhap.accessory_driver import AccessoryDriver
from gi import require_version

require_version("GdkPixbuf", "2.0")

from gi.repository import Gio, GdkPixbuf  # type: ignore  # noqa: E402


@pytest.fixture
def acc():
    options = {
        "video": {"codec": {"profiles": [], "levels": []}, "resolutions": []},
        "audio": {"codecs": []},
        "address": "192.168.1.1",
    }

    return GstCamera("videotestsrc", options, AccessoryDriver(), "Camera")


@pytest.mark.parametrize("width, height", [(1920, 1080), (640, 480)])
def test_snapshot(acc: GstCamera, width: int, height: int):
    snapshot = acc.get_snapshot({"image-width": width, "image-height": height})

    assert isinstance(snapshot, bytes)

    pixbuf = GdkPixbuf.Pixbuf.new_from_stream(Gio.MemoryInputStream.new_from_data(snapshot))

    assert pixbuf.get_width() == width
    assert pixbuf.get_height() == height
