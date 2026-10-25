import pytest
from gst_camera import GstCamera
from pyhap.accessory_driver import AccessoryDriver
from gi.repository import Gst, GstApp  # type: ignore


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

    pipeline = Gst.Pipeline.new()
    src = GstApp.AppSrc()
    pipeline.add(src)
    dec = pipeline.make_and_add("jpegdec")
    sink = GstApp.AppSink()
    pipeline.add(sink)
    Gst.Element.link_many(src, dec, sink)

    pipeline.set_state(Gst.State.PLAYING)
    src.push_buffer(Gst.Buffer.new_wrapped(snapshot))
    caps = sink.pull_sample().get_caps().get_structure(0)
    pipeline.set_state(Gst.State.NULL)

    assert caps["width"] == width
    assert caps["height"] == height
