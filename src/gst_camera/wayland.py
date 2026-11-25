from gi import require_versions

require_versions({"Xdp": "1.0"})

from gi.repository import Xdp, GLib, Gst  # type: ignore  # noqa: E402


class ScreenCapture:
    def __init__(self):
        self.portal = Xdp.Portal()

        self.portal.create_screencast_session(
            Xdp.OutputType.MONITOR,
            Xdp.ScreencastFlags.NONE,
            Xdp.CursorMode.EMBEDDED,
            Xdp.PersistMode.TRANSIENT,
            None,
            None,
            self.on_session_created,
        )

        self._loop = GLib.MainLoop()
        self._loop.run()

    def on_session_created(self, portal: Xdp.Portal, result):
        self.session = portal.create_screencast_session_finish(result)
        self.session.start(None, None, self.on_session_started)

    def on_session_started(self, session: Xdp.Session, result):
        session.start_finish(result)
        stream = session.get_streams()[0]
        self.width, self.height = stream[1]["size"]
        self.path = stream[0]
        self._loop.quit()

    def __call__(self, *args, **kwds):
        bin = Gst.Bin.new()
        pipewire = bin.make_and_add("pipewiresrc")
        pipewire.set_properties(fd=self.session.open_pipewire_remote(), path=self.path)

        capsfilter = bin.make_and_add("capsfilter")
        caps = Gst.Caps.new_empty_simple("video/x-raw")
        caps.set_value("width", self.width)
        caps.set_value("height", self.height)
        # caps.set_value("framerate", Gst.Fraction(60))
        capsfilter.set_property("caps", caps)

        identity = bin.make_and_add("identity")

        Gst.Element.link_many(pipewire, capsfilter, identity)

        ghost_pad = Gst.GhostPad.new("src", identity.get_static_pad("src"))
        ghost_pad.set_active(True)
        bin.add_pad(ghost_pad)

        return bin
