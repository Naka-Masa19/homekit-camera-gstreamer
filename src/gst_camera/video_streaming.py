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
        self.stream_config = stream_config
        self.pre_encoder_format = pre_encoder_format
        self.encoder_properties = encoder_properties
        self.ignore_h264_level = ignore_h264_level
        self.pipeline = Gst.Pipeline.new()
        self.bus = self.pipeline.get_bus()

        self.src = source()
        match self.src.iterate_all_by_element_factory_name("pipewiresrc").next():
            case Gst.IteratorResult.OK, pipewiresrc:
                pipewiresrc.set_properties(client_name=f"HomeKit Stream ({stream_config['address']})")
        self.pipeline.add(self.src)

        self._init_encodebin()

        self.rtppay = self.pipeline.make_and_add("rtph264pay")
        self.rtppay.set_properties(
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

        Gst.Element.link_many(self.src, self.enc, self.rtppay, srtp, sink)

    def _init_encodebin(self):
        self.enc: Gst.Bin = self.pipeline.make_and_add("encodebin")

        enc_format = Gst.Caps.new_empty_simple("video/x-h264")
        enc_format.set_value("profile", _ENCODE_PROFILE[self.stream_config["v_profile_id"]])
        if not self.ignore_h264_level:
            enc_format.set_value("level", _ENCODE_LEVEL[self.stream_config["v_level"]])
        enc_format.set_value("bitrate", self.stream_config["v_max_bitrate"])

        enc_restriction = Gst.Caps.new_empty_simple("video/x-raw")
        enc_restriction.set_value("width", self.stream_config["width"])
        enc_restriction.set_value("height", self.stream_config["height"])
        enc_restriction.set_value("framerate", Gst.Fraction(self.stream_config["fps"]))
        if self.pre_encoder_format is not None:
            enc_restriction.set_value("format", self.pre_encoder_format)

        self.profile = GstPbutils.EncodingVideoProfile.new(enc_format, None, enc_restriction, 0)
        self.profile.set_element_properties(self.encoder_properties)

        self.enc.set_properties(profile=self.profile)

        logger.info(f"Encodebin input caps: {enc_restriction.to_string()}")
        logger.info(f"H264 profile: {enc_format.to_string()}")

    def start_stream(self):
        self.pipeline.set_state(Gst.State.PLAYING)
        success = self.pipeline.get_state(Gst.SECOND * 10)[0] != Gst.StateChangeReturn.FAILURE

        if logger.isEnabledFor(logging.INFO):
            bin_list = list()
            itr = self.enc.iterate_recurse()
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
        self.src.unlink(self.enc)
        self.enc.unlink(self.rtppay)

        self.enc.set_state(Gst.State.NULL)
        self.pipeline.remove(self.enc)

        self._init_encodebin()

        Gst.Element.link_many(self.src, self.enc, self.rtppay)

        self.enc.sync_state_with_parent()
        return Gst.PadProbeReturn.REMOVE

    def reconfigure_stream(self, stream_config):
        self.stream_config.update(stream_config)
        self.src.get_static_pad("src").add_probe(Gst.PadProbeType.BLOCK_DOWNSTREAM, self._reinit_encodebin)
        while self.bus.pop():
            pass
        return True

    def stop_stream(self):
        self.pipeline.set_state(Gst.State.NULL)
