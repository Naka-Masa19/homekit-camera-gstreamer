# HomeKit Camera GStreamer
English

## 特徴
- マルチストリーミング対応
- GStreamerが対応しているほぼすべてのソースに対応 (USB/Webカメラ、PipeWire、ネットワークストリーム、ファイル、画面収録など)
- Raspberry Pi Camera Module V2 (libcamera) にて動作確認済み
- ハードウェアエンコーダーの自動選択
- ストリーミング中の動的な解像度変更

## インストール
### Debian (Ubuntu, Raspberry Pi OS)
```bash
sudo apt install gir1.2-gst-plugins-base-1.0 gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-pipewire libgstreamer1.0-0 pipewire pipewire-libcamera libcamera-ipa wireplumber python3-gi python3-pip python3-gst-1.0
pip3 install git+https://github.com/j6yrfbckhh-collab/homekit-camera-gstreamer.git --break-system-packages
```
