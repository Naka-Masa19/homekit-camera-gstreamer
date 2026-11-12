from collections import defaultdict
from math import gcd
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
    other_resolutions = set()
    for cap in device.get_caps():
        width = cap.get_value("width")
        height = cap.get_value("height")
        match (width, height):
            case int(), int():
                g = gcd(width, height)
                resolutions[(width // g, height // g)].add((width, height))
            case _:
                width = convert(width)
                height = convert(height)
                other_resolutions.add((width, height))
        match cap.get_name():
            case "video/x-raw":
                format = cap.get_value("format")
            case "image/jpeg":
                format = "MJPEG"
        formats.add(format)
    print(f"formats: {', '.join(formats)}")
    for key in resolutions.keys():
        print(f"{key[0]}:{key[1]}: {', '.join([f'{i[0]}x{i[1]}' for i in resolutions[key]])}")
    print("others:", other_resolutions)
    width, height = max([rr for r in resolutions.values() for rr in r], key=lambda x: x[0] * x[1], default=(None, None))
    if width and height:
        g = gcd(width, height)
        print(f"この入力の最も視野が広いアスペクト比はおそらく{width // g}:{height // g}({width}x{height})です。")
    print()

print("\033[1A\033[2K", end="")
