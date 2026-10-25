from gst_camera.video_streaming import VideoStreaming
from gi.repository import Gst  # type:ignore
from time import sleep
from secrets import token_bytes
from base64 import b64encode
import logging

logging.basicConfig(level=logging.INFO)


def test_videostreaming():
    config = {
        "v_profile_id": b"\x01",
        "v_level": b"\x02",
        "width": 1280,
        "height": 720,
        "fps": 30,
        "v_ssrc": 11580679,
        "v_payload_type": b"c",
        "v_max_bitrate": 299,
        "v_rtcp_interval": 0.5,
        "v_max_mtu": b"b\x05",
        "a_codec": b"\x03",
        "a_comfort_noise": b"\x00",
        "a_channel": 1,
        "a_bitrate": False,
        "a_sample_rate": 24,
        "a_packet_time": 20,
        "a_ssrc": 7837805,
        "a_payload_type": b"n",
        "a_max_bitrate": 24,
        "a_rtcp_interval": 5.0,
        "a_comfort_payload_type": b"\r",
        "stream_idx": 0,
        "address": "172.0.0.1",
        "v_port": 59017,
        "v_srtp_key": b64encode(token_bytes(30)),
        "a_port": 57210,
        "a_srtp_key": b64encode(token_bytes(30)),
    }
    streaming = VideoStreaming(
        lambda: Gst.parse_bin_from_description("videotestsrc", True), config, None, Gst.Structure.new_empty("a"), False
    )
    assert streaming.start_stream()
    sleep(5)
    assert streaming.reconfigure_stream(config)
    sleep(5)
    streaming.stop_stream()
