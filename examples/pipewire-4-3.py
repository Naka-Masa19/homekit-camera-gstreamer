# Adapted from HAP-python's camera_main.py and modified for this project.
# Original: https://github.com/ikalchev/HAP-python/blob/dev/camera_main.py
# Licensed under the Apache License, Version 2.0. See ../THIRD_PARTY_LICENSES.md.
"""Example of using a 4:3 camera through PipeWire."""

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
            [1600, 1200, 30],  # UXGA
            [1280, 960, 30],
            [1024, 768, 30],  # XGA
            [800, 600, 30],  # SVGA
            [640, 480, 30],  # VGA
            [320, 240, 30],  # QVGA
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


# Pipewire camera source
source = "pipewiresrc use-bufferpool=false"

# raw video source
# source = "pipewiresrc use-bufferpool=false ! video/x-raw, format=YUY2, width=1600, height=1200, framerate=30/1"

# MJPEG camera source
# source = "pipewiresrc use-bufferpool=false ! image/jpeg, width=1600, height=1200, framerate=30/1 ! jpegdec"

acc = GstCamera(source, options, driver, "Camera")
driver.add_accessory(acc)

# We want KeyboardInterrupts and SIGTERM (terminate) to be handled by the driver itself,
# so that it can gracefully stop the accessory, server and advertising.
signal.signal(signal.SIGTERM, driver.signal_handler)
# Start it!
driver.start()
