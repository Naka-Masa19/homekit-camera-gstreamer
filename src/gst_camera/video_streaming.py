from base64 import b64decode
from collections.abc import Callable
from gi.repository import Gst, GstPbutils  # type:ignore
import logging
from pyhap import camera

logger = logging.getLogger(__name__)

_ENCODE_PROFILE = {
    camera.VIDEO_CODEC_PARAM_PROFILE_ID_TYPES["BASELINE"]: "baseline",
    camera.VIDEO_CODEC_PARAM_PROFILE_ID_TYPES["MAIN"]: "main",
    camera.VIDEO_CODEC_PARAM_PROFILE_ID_TYPES["HIGH"]: "high",
}

_ENCODE_LEVEL = {
    camera.VIDEO_CODEC_PARAM_LEVEL_TYPES["TYPE3_1"]: "3.1",
    camera.VIDEO_CODEC_PARAM_LEVEL_TYPES["TYPE3_2"]: "3.2",
    camera.VIDEO_CODEC_PARAM_LEVEL_TYPES["TYPE4_0"]: "4",
}


class VideoStreaming:
    def __init__(
        self,
        source: Callable[[], Gst.Bin],
        stream_config: dict,
        pre_encoder_format: str | None,
        encoder_properties: Gst.Structure,
        ignore_h264_level: bool,
    ):
        self.pipeline = Gst.Pipeline.new()
        self._bus = self.pipeline.get_bus()
        self._stream_config = stream_config
        self._pre_encoder_format = pre_encoder_format
        self._encoder_properties = encoder_properties
        self._ignore_h264_level = ignore_h264_level

        self._src = source()
        self._src_pad = self._src.get_static_pad("src")
        match self._src.iterate_all_by_element_factory_name("pipewiresrc").next():
            case Gst.IteratorResult.OK, pipewiresrc:
                pipewiresrc.set_properties(client_name=f"HomeKit Stream ({stream_config['address']})")
        self.pipeline.add(self._src)

        self._init_encodebin()

        self._rtppay = self.pipeline.make_and_add("rtph264pay")
        self._rtppay.set_properties(
            config_interval=-1,
            ssrc=stream_config["v_ssrc"],
            mtu=int.from_bytes(stream_config["v_max_mtu"], "little"),
            pt=int.from_bytes(stream_config["v_payload_type"], "little"),
        )

        srtp = self.pipeline.make_and_add("srtpenc")
        srtp.set_properties(
            rtp_cipher="aes-128-icm", rtp_auth="hmac-sha1-80", key=Gst.Buffer.new_wrapped(b64decode(stream_config["v_srtp_key"]))
        )

        sink = self.pipeline.make_and_add("udpsink")
        sink.set_properties(sync=False, host=stream_config["address"], port=stream_config["v_port"])

        Gst.Element.link_many(self._src, self._enc, self._rtppay, srtp, sink)

    def _init_encodebin(self):
        self._enc: Gst.Bin = self.pipeline.make_and_add("encodebin")

        format = Gst.Caps.new_empty_simple("video/x-h264")
        format.set_value("profile", _ENCODE_PROFILE[self._stream_config["v_profile_id"]])
        format.set_value("bitrate", self._stream_config["v_max_bitrate"])
        if not self._ignore_h264_level:
            format.set_value("level", _ENCODE_LEVEL[self._stream_config["v_level"]])

        restriction = Gst.Caps.new_empty_simple("video/x-raw")
        restriction.set_value("width", self._stream_config["width"])
        restriction.set_value("height", self._stream_config["height"])
        restriction.set_value("framerate", Gst.Fraction(self._stream_config["fps"]))
        if self._pre_encoder_format is not None:
            restriction.set_value("format", self._pre_encoder_format)

        profile = GstPbutils.EncodingVideoProfile.new(format, None, restriction, 0)
        profile.set_element_properties(self._encoder_properties)

        self._enc.set_properties(profile=profile)

        logger.info(f"Encodebin input caps: {restriction.to_string()}")
        logger.info(f"H264 profile: {format.to_string()}")

    def start_stream(self):
        self.pipeline.set_state(Gst.State.PLAYING)
        success = self.pipeline.get_state(Gst.SECOND * 10)[0] != Gst.StateChangeReturn.FAILURE

        if logger.isEnabledFor(logging.INFO):
            bin_list = list()
            itr = self._enc.iterate_recurse()
            while True:
                match itr.next():
                    case Gst.IteratorResult.OK, element:
                        bin_list.append(element.get_name())
                    case Gst.IteratorResult.RESYNC, _:
                        bin_list.clear()
                        itr.resync()
                    case _:
                        break
            logger.info(f"Encodebin chain: {' -> '.join(bin_list)}")

        if not success:
            self.stop_stream()
        return success

    def _reinit_encodebin(self, pad: Gst.Pad, info: Gst.PadProbeInfo):
        self._src.unlink(self._enc)
        self._enc.unlink(self._rtppay)

        self._enc.set_state(Gst.State.NULL)
        self.pipeline.remove(self._enc)

        self._init_encodebin()

        Gst.Element.link_many(self._src, self._enc, self._rtppay)

        self._enc.sync_state_with_parent()
        return Gst.PadProbeReturn.REMOVE

    def reconfigure_stream(self, stream_config):
        self._stream_config.update(stream_config)
        self._src_pad.add_probe(Gst.PadProbeType.BLOCK_DOWNSTREAM, self._reinit_encodebin)
        while self._bus.pop():
            pass
        return True

    def stop_stream(self):
        self.pipeline.set_state(Gst.State.NULL)
