# HomeKit Camera GStreamer
English

## 特徴
- マルチストリーミング対応 (ソースがPipeWireやネットワークストリームなど同時読み取りに対応している必要がある)
- GStreamerが対応しているほぼすべてのソースに対応 (PipeWire、USB/Webカメラ、ネットワークストリーム、ファイル、画面収録など)
- Raspberry Pi Camera Module V2 (libcamera) にて動作確認済み
- H264エンコーダーの自動選択 (openh264enc, v4l2h264encなど)
- ストリーミング中の動的な解像度変更

## インストール
### Debian (Ubuntu, Raspberry Pi OS)
```bash
sudo apt install gir1.2-gst-plugins-base-1.0 gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-pipewire libgstreamer1.0-0 pipewire pipewire-libcamera libcamera-ipa wireplumber python3-gi python3-pip python3-gst-1.0
pip3 install git+https://github.com/j6yrfbckhh-collab/homekit-camera-gstreamer.git --break-system-packages
```
