import pytest
from gst_camera import GstCamera
from pyhap.accessory_driver import AccessoryDriver


@pytest.fixture
def acc():
    options = {
        "video": {"codec": {"profiles": [], "levels": []}, "resolutions": []},
        "audio": {"codecs": []},
        "address": "192.168.1.1",
    }

    return GstCamera("videotestsrc", options, AccessoryDriver(), "Camera")


def test_snapshot(acc):
    snapshot = acc.get_snapshot({"image-width": 1920, "image-height": 1080})
    assert isinstance(snapshot, bytes)
