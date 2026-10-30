from collections.abc import Callable
from pyhap import camera
from os import environ
import logging
import asyncio
from gi.repository import Gst, GstApp  # type:ignore
from .video_streaming import VideoStreaming

logger = logging.getLogger(__name__)
logger.info("Initializing GStreamer")
Gst.init(None)
logger.info(f"Initialized {Gst.version_string()}")

if not Gst.version()[1] >= 22:
    raise RuntimeError(f"{__package__} requires GStreamer 1.22.0 or later, but {Gst.version_string()} is installed.")

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


class GstCamera(camera.Camera):
    StreamingSessionClass = VideoStreaming

    def __init__(self, source: str | Callable[[], Gst.Bin], options, *args, **kwargs):
        super().__init__(options, *args, **kwargs)
        self.set_info_service(firmware_revision=Gst.version_string())
        self._is_source_exclusive = options.get("stream_count", 1) == 1
        self._snapshot_pipeline_wait_state = Gst.State.NULL if self._is_source_exclusive else Gst.State.READY
        self.src = (lambda: Gst.parse_bin_from_description(f"{source} ! identity", True)) if isinstance(source, str) else source
        self.ignore_reconfig = False
        self.ignore_h264_level = False
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
            self.src, stream_config, self.pre_encoder_format, self.encoder_properties, self.ignore_h264_level
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
