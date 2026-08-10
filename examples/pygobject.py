"""Example of using an MJPEG camera through PipeWire with PyGObject."""

import logging

logging.basicConfig(level=logging.INFO)

import signal
from pyhap.accessory_driver import AccessoryDriver
from pyhap import camera, util
from gst_camera import GstCamera

from gi import require_version

require_version("Gst", "1.0")
from gi.repository import Gst  # type:ignore

# Specify the audio and video configuration that your device can support
# The HAP client will choose from these when negotiating a session.
options = {
    "video": {
        "codec": {
            "profiles": [
                camera.VIDEO_CODEC_PARAM_PROFILE_ID_TYPES["BASELINE"],
                camera.VIDEO_CODEC_PARAM_PROFILE_ID_TYPES["MAIN"],
                # camera.VIDEO_CODEC_PARAM_PROFILE_ID_TYPES["HIGH"]
            ],
            "levels": [
                camera.VIDEO_CODEC_PARAM_LEVEL_TYPES["TYPE3_1"],
                camera.VIDEO_CODEC_PARAM_LEVEL_TYPES["TYPE3_2"],
                camera.VIDEO_CODEC_PARAM_LEVEL_TYPES["TYPE4_0"],
            ],
        },
        "resolutions": [
            # Width, Height, framerate
            [1920, 1080, 30],  # FHD
            [1280, 720, 30],  # HD
            [960, 540, 30],  # qHD
            [640, 360, 30],  # 360p
            [480, 270, 30],  # 270p
            [320, 180, 30],  # 180p
            [320, 240, 15],  # Required for Apple Watch
        ],
    },
    "audio": {
        "codecs": [],
    },
    "srtp": True,
    "stream_count": 5,
    # hard code the address if auto-detection does not work as desired: e.g. "192.168.1.226"
    "address": util.get_local_address(),
}

# Start the accessory on port 51826
driver = AccessoryDriver(port=51826)

class Source(Gst.Bin):
    """pipewiresrc use-bufferpool=false ! image/jpeg, width=1920, height=1080, framerate=30/1 ! jpegdec"""
    def __init__(self):
        super().__init__()

        src = self.make_and_add("pipewiresrc")
        src.set_properties(use_bufferpool=False)

        capsfilter = self.make_and_add("capsfilter")
        caps = Gst.Caps.new_empty_simple("image/jpeg")
        caps.set_value("width", 1920)
        caps.set_value("height", 1080)
        caps.set_value("framerate", Gst.Fraction(30))
        capsfilter.set_property("caps", caps)

        jpegdec = self.make_and_add("jpegdec")

        Gst.Element.link_many(src, capsfilter, jpegdec)

        ghost_pad = Gst.GhostPad.new("src", jpegdec.get_static_pad("src"))
        ghost_pad.set_active(True)
        self.add_pad(ghost_pad)

acc = GstCamera(Source, options, driver, "Camera")
driver.add_accessory(acc)

# We want KeyboardInterrupts and SIGTERM (terminate) to be handled by the driver itself,
# so that it can gracefully stop the accessory, server and advertising.
signal.signal(signal.SIGTERM, driver.signal_handler)
# Start it!
driver.start()
