# HomeKit Camera GStreamer
English

## 特徴
- マルチストリーミング対応 (PipeWireやネットワークストリームなどソースが同時読み取りに対応している必要がある)
- GStreamerが対応しているほぼすべてのソースに対応 (PipeWire、USB/Webカメラ、ネットワークストリーム、ファイル、画面収録など)
- Raspberry Pi Camera Module V2 (libcamera) にて動作確認済み
- H264エンコーダーの自動選択 (openh264enc, v4l2h264encなど)
- ストリーミング中の動的な解像度変更

## インストール
### Debian (Ubuntu, Raspberry Pi OS)
```bash
sudo apt install gstreamer1.0-plugins-good gstreamer1.0-plugins-bad libgstreamer1.0-0 gir1.2-gst-plugins-base-1.0 python3-gst-1.0 python3-gi python3-pip
pip3 install git+https://github.com/j6yrfbckhh-collab/homekit-camera-gstreamer.git --break-system-packages
```
## カメラを使う例

### PipeWire
```bash
sudo apt install pipewire wireplumber gstreamer1.0-pipewire
```
### Libcamera
```bash
sudo apt install pipewire-libcamera libcamera-ipa
```
<!--pipewire-libcameraはDebian trixie以降ではlibspa-0.2-libcameraへの以降用パッケージとなっている。-->
