from collections import defaultdict
from math import gcd
from pprint import pprint
from gi.repository import Gst  # type: ignore

Gst.init()
monitor = Gst.DeviceMonitor()
monitor.add_filter("Video/Source")
monitor.start()
devices = monitor.get_devices()
monitor.stop()


def convert(data):
    match data:
        case Gst.ValueList():
            data = tuple(data)
        case Gst.IntRange():
            tmp = data.range
            data = f"{min(tmp)} ~ {max(tmp)}"
    return data


for device in devices:
    print(device.get_display_name())
    if name := device.get_properties().get_value("device.api"):
        print(f"API: {name}")

    formats = set()
    resolutions = defaultdict(set)
    for cap in device.get_caps():
        width = cap.get_value("width")
        height = cap.get_value("height")
        match (width, height):
            case int(), int():
                g = gcd(width, height)
                group = (width // g, height // g)
            case _:
                width = convert(width)
                height = convert(height)
                group = "other"
        resolutions[group].add((width, height))
        match cap.get_name():
            case "video/x-raw":
                format = cap.get_value("format")
            case "image/jpeg":
                format = "MJPEG"
        formats.add(format)
    print(f"formats: {', '.join(formats)}")
    pprint(resolutions)
    print()
