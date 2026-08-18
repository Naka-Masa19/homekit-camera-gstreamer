# Adapted from HAP-python's camera_main.py and modified for this project.
# Original: https://github.com/ikalchev/HAP-python/blob/dev/camera_main.py
# Licensed under the Apache License, Version 2.0. See ../THIRD_PARTY_LICENSES.md.
"""Example of using Media Foundation (mfvideosrc) or Direct3D11 screen
capture (d3d11screencapturesrc) as a video source on Windows."""

import logging

logging.basicConfig(level=logging.INFO)

import signal
from pyhap.accessory_driver import AccessoryDriver
from pyhap import camera, util
from gst_camera import GstCamera
from gi.repository import Gst  # type:ignore

if factory := Gst.ElementFactory.find("amfh264enc"):
    factory.set_rank(Gst.Rank.NONE)

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


# camera source
source = "mfvideosrc"

# raw video source
# source = "mfvideosrc ! video/x-raw, width=1920, height=1080, framerate=30/1"

# screen capture source
# source = "d3d11screencapturesrc"

camera = GstCamera(source, options, driver, "Camera")
driver.add_accessory(camera)

# We want KeyboardInterrupts and SIGTERM (terminate) to be handled by the driver itself,
# so that it can gracefully stop the accessory, server and advertising.
signal.signal(signal.SIGTERM, driver.signal_handler)
# Start it!
driver.start()
