# HomeKit Camera GStreamer
[English]()

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
## 構成例 (PipeWire経由のカメラ)

### PipeWireのインストール
```bash
sudo apt install pipewire wireplumber gstreamer1.0-pipewire
```
> Libcamera (Raspberry Pi Camera Moduleなど) の場合は追加で以下のパッケージが必要です。
> ```bash
> sudo apt install pipewire-libcamera libcamera-ipa
> ```
> >pipewire-libcameraはDebian trixie以降ではlibspa-0.2-libcameraへの以降用パッケージとなっている。
### デフォルトカメラの設定
``` bash
wpctl status
wpctl set-default [カメラのID]
```
> [カメラのID]はwpctl statusのSourcesの結果に合わせて書き換えて下さい

### 実行
[mjpegカメラ向けサンプルコード](https://github.com/j6yrfbckhh-collab/homekit-camera-gstreamer/blob/main/examples/mpeg-camera.py)
