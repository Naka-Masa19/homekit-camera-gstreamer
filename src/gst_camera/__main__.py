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
            data = f"[{','.join(str(d) for d in list(data))}]"
        case Gst.IntRange():
            tmp = data.range
            data = f"[{min(tmp)}~{max(tmp)}]"
    return data


for device in devices:
    print(device.get_display_name())
    if name := device.get_properties().get_value("device.api"):
        print(f"API: {name}")

    formats = {"raw-format": set(), "drm-format": set(), "encoded": set()}
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
                if format == "DMA_DRM":
                    formats["drm-format"].add(cap.get_value("drm-format"))
                else:
                    formats["raw-format"].add(format)
            case e:
                formats["encoded"].add(e)
    for key, value in formats.items():
        if value:
            print(f"{key}: {', '.join(sorted(value))}")

    print("resolutions:")
    # print(max(len(f"{key[0]}:{key[1]}") for key in resolutions.keys()))
    for key in sorted(resolutions.keys()):
        print(f"    {key[0]}:{key[1]}: {', '.join([f'{i[0]}x{i[1]}' for i in sorted(resolutions[key], reverse=True)])}")
    if other_resolutions:
        print(f"    others: {', '.join(f'{other[0]}x{other[1]}' for other in other_resolutions)}")

    width, height = max([j for i in resolutions.values() for j in i], key=lambda x: x[0] * x[1], default=(None, None))
    if width and height:
        g = gcd(width, height)
        print(f"The widest aspect ratio for this input is probably {width // g}:{height // g} ({width}x{height}).")
    print()

print("\033[1A\033[2K", end="")
