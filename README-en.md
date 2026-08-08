# HomeKit Camera GStreamer
[日本語](README.md)

## Features
- Supports multiple simultaneous streams
  - Streams can be served to multiple devices at the same time.
  - An input source that supports simultaneous use by multiple clients is required, such as PipeWire or a network stream.
- Supports nearly every source supported by GStreamer
  - PipeWire
  - USB/webcams
  - Raspberry Pi Camera Modules
  - Network streams
  - Files
  - etc.
- Automatic H.264 encoder selection (`encodebin`)
  - `openh264enc`
  - `v4l2h264enc`
  - etc.
- Dynamic resolution changes while streaming
  - The resolution can be changed during streaming in response to requests from HomeKit.

## Tested Environments
- Raspberry Pi
  - Model: Raspberry Pi 3 Model B Plus
  - OS: Ubuntu Server 26.04 LTS
  - Kernel: 7.0.0-1015-raspi
  - Source: PipeWire
  - Camera: Raspberry Pi Camera Module 2 (IMX219)
  - Python: 3.14.4
  - GStreamer: 1.28.2
  - Encoder: `v4l2h264enc`
- PC
  - OS: Fedora Linux 44 (Workstation Edition)
  - Source: PipeWire
  - Python: 3.14.6
  - GStreamer: 1.28.6
  - Encoder: `openh264enc`

## Installation
### Debian (Ubuntu, Raspberry Pi OS)
```bash
sudo apt install gstreamer1.0-plugins-good gstreamer1.0-plugins-bad libgstreamer1.0-0 gir1.2-gst-plugins-base-1.0 python3-gst-1.0 python3-gi python3-pip
pip3 install git+https://github.com/j6yrfbckhh-collab/homekit-camera-gstreamer.git --break-system-packages
```

## Configuration Example (Camera via PipeWire)

### Install PipeWire
```bash
sudo apt install pipewire wireplumber gstreamer1.0-pipewire
```

> Cameras that use libcamera, such as Raspberry Pi Camera Modules, also require the following packages:
>
> ```bash
> sudo apt install libspa-0.2-libcamera libcamera-ipa
> ```
>
> If `libspa-0.2-libcamera` is not available in your environment, try the following instead:
>
> ```bash
> sudo apt install pipewire-libcamera libcamera-ipa
> ```

### Set the Default Camera
```bash
wpctl status
wpctl set-default [camera ID]
```

> Replace `[camera ID]` with the ID shown under `Sources` in the output of `wpctl status`.

### Run
Choose the sample that matches the aspect ratio of the camera you want to use.

[Sample code for 16:9 cameras](examples/pipewire-16:9.py)

- General-purpose cameras and Raspberry Pi Camera Module 3, among others

[Sample code for 4:3 cameras](examples/pipewire-4:3.py)

- Raspberry Pi Camera Module 1 / 2, among others
