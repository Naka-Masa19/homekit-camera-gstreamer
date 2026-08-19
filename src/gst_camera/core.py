from base64 import b64decode
from collections.abc import Callable
from pyhap import camera
from os import environ
import logging
import asyncio
from gi import require_versions

require_versions({"Gst": "1.0", "GstApp": "1.0", "GstPbutils": "1.0"})
from gi.repository import Gst, GstApp, GstPbutils  # type:ignore

Gst.init()

logger = logging.getLogger(__name__)
logger.info(f"Initialized {Gst.version_string()}")

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

if "GST_DEBUG" not in environ:
    Gst.debug_set_default_threshold(
        {
            logging.CRITICAL: Gst.DebugLevel.NONE,
            logging.ERROR: Gst.DebugLevel.ERROR,
            logging.WARNING: Gst.DebugLevel.WARNING,
            logging.INFO: Gst.DebugLevel.FIXME,
            logging.DEBUG: Gst.DebugLevel.INFO,
        }[logger.getEffectiveLevel()]
    )

if not hasattr(asyncio, "SafeChildWatcher"):

    class _DummyChildWatcher:
        def __init__(self):
            logger.warning("Class asyncio.SafeChildWatcher was removed in Python 3.14.")

        def __getattr__(self, name):
            return lambda *a, **ka: logger.warning(f"Called asyncio.SafeChildWatcher.{name}, ignored.")

    asyncio.SafeChildWatcher = _DummyChildWatcher
    asyncio.set_child_watcher = lambda w: logger.warning("Method asyncio.set_child_watcher was removed in Python 3.14, ignored.")


class StreamingSession:
    def __init__(
        self,
        source: Callable[[], Gst.Bin],
        stream_config: dict,
        pre_encoder_format: str | None,
        encoder_properties: Gst.Structure,
    ):
        self.stream_config = stream_config
        self.pre_encoder_format = pre_encoder_format
        self.encoder_properties = encoder_properties
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


class GstCamera(camera.Camera):
    StreamingSessionClass = StreamingSession

    def __init__(self, source: str | Callable[[], Gst.Bin], options, *args, **kwargs):
        super().__init__(options, *args, **kwargs)
        self.set_info_service(firmware_revision=Gst.version_string())
        self._is_source_exclusive = options.get("stream_count", 1) == 1
        self._snapshot_pipeline_wait_state = Gst.State.NULL if self._is_source_exclusive else Gst.State.READY
        self.src = (lambda: Gst.parse_bin_from_description(f"{source} ! identity", True)) if isinstance(source, str) else source
        self.ignore_reconfig = False
        self.pre_encoder_format = None
        self.snapshot_warmup_frames = 0
        self.encoder_properties = Gst.Structure.new_empty("encoder_properties")
        self.snapshot_pipeline = Gst.Pipeline.new()
        self.snapshot_bus = self.snapshot_pipeline.get_bus()

        if not (callable(self.src) and isinstance(snapshot_src := self.src(), Gst.Bin)):
            raise TypeError("source must be str or callable")
        self.snapshot_pipeline.add(snapshot_src)
        match snapshot_src.iterate_all_by_element_factory_name("pipewiresrc").next():
            case Gst.IteratorResult.OK, pipewiresrc:
                pipewiresrc.set_properties(client_name="HomeKit Snapshot")

        snapshot_convertscale = self.snapshot_pipeline.make_and_add("videoconvertscale")
        self.snapshot_caps = self.snapshot_pipeline.make_and_add("capsfilter")
        snapshot_jpegenc = self.snapshot_pipeline.make_and_add("jpegenc")

        self.snapshot_sink = GstApp.AppSink()
        self.snapshot_pipeline.add(self.snapshot_sink)
        self.snapshot_sink.set_max_buffers(1)
        self.snapshot_sink.set_drop(True)

        Gst.Element.link_many(snapshot_src, snapshot_convertscale, self.snapshot_caps, snapshot_jpegenc, self.snapshot_sink)

        self.snapshot_pipeline.set_state(self._snapshot_pipeline_wait_state)

    @property
    def pre_encoder_format(self):
        return self._pre_encoder_format

    @pre_encoder_format.setter
    def pre_encoder_format(self, arg: str | None):
        if not isinstance(arg, str | None):
            raise TypeError("pre_encoder_format must be str or None")
        self._pre_encoder_format = arg

    @property
    def encoder_properties(self):
        return self._encoder_properties

    @encoder_properties.setter
    def encoder_properties(self, arg: dict | Gst.Structure | None):
        match arg:
            case dict():
                self._encoder_properties.remove_all_fields()
                for key, value in arg.items():
                    self._encoder_properties.set_value(key, value)
            case Gst.Structure():
                self._encoder_properties = arg
            case None:
                self._encoder_properties.remove_all_fields()
            case _:
                raise TypeError("encoder_properties must be dict, Gst.Structure or None")

    @property
    def snapshot_warmup_frames(self):
        return self._snapshot_warmup_frames

    @snapshot_warmup_frames.setter
    def snapshot_warmup_frames(self, arg: int):
        if not isinstance(arg, int):
            raise TypeError("snapshot_warmup_frames must be int")
        self._snapshot_warmup_frames = arg

    async def stop(self):  # stop accessary
        self.snapshot_pipeline.set_state(Gst.State.NULL)
        return await super().stop()

    async def start_stream(self, session_info, stream_config):
        logger.info(f"[{session_info['id']}] Starting stream")
        session_info["streaming_instance"] = self.StreamingSessionClass(
            self.src, stream_config, self.pre_encoder_format, self.encoder_properties
        )
        return await asyncio.to_thread(session_info["streaming_instance"].start_stream)

    async def reconfigure_stream(self, session_info, stream_config):
        if self.ignore_reconfig:
            logger.info(f"[{session_info['id']}] Ignoreing reconfig stream")
            return True
        logger.info(f"[{session_info['id']}] Reconfiguring stream")
        return session_info["streaming_instance"].reconfigure_stream(stream_config)

    async def stop_stream(self, session_info):
        logger.info(f"[{session_info['id']}] Stopping stream")
        session_info["streaming_instance"].stop_stream()

    def get_snapshot(self, info):
        while self.snapshot_bus.pop():
            pass
        caps = Gst.Caps.new_empty_simple("video/x-raw")
        caps.set_value("width", info["image-width"])
        caps.set_value("height", info["image-height"])
        self.snapshot_caps.set_properties(caps=caps)
        if self._is_source_exclusive and len(self.sessions) == 1:
            sample = None
        else:
            self.snapshot_pipeline.set_state(Gst.State.PLAYING)
            for _ in range(self.snapshot_warmup_frames + 1):
                sample = self.snapshot_sink.try_pull_sample(Gst.SECOND * 5)
            self.snapshot_pipeline.set_state(self._snapshot_pipeline_wait_state)
        return buf.extract_dup(0, buf.get_size()) if sample and (buf := sample.get_buffer()) else super().get_snapshot(info)
