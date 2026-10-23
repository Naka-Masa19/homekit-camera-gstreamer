from gi import require_versions

require_versions({"Gst": "1.0", "GstApp": "1.0", "GstPbutils": "1.0"})

from .core import GstCamera

__all__ = ["GstCamera"]
