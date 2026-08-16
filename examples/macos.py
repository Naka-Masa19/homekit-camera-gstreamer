"""Example of using an AVFoundation video source on macOS."""

import logging

logging.basicConfig(level=logging.INFO)

import signal
from pyhap.accessory_driver import AccessoryDriver
from pyhap import camera, util
from gst_camera import GstCamera

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
            # [1920, 1080, 30],  # FHD
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


# camera source
source = "avfvideosrc"

# raw video source
# source = "avfvideosrc ! video/x-raw, width=1280, height=720, framerate=30/1"

# screen capture source
# source = "avfvideosrc capture-screen=true"

camera = GstCamera(source, options, driver, "Camera")

# Required for stable realtime streaming with VideoToolbo
camera.encoder_properties["allow-frame-reordering"] = False

driver.add_accessory(camera)

# We want KeyboardInterrupts and SIGTERM (terminate) to be handled by the driver itself,
# so that it can gracefully stop the accessory, server and advertising.
signal.signal(signal.SIGTERM, driver.signal_handler)
# Start it!
driver.start()
