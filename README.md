# HomeKit Camera GStreamer
[English](README-en.md)

[![Lint](https://github.com/j6yrfbckhh-collab/homekit-camera-gstreamer/actions/workflows/lint.yml/badge.svg)](https://github.com/j6yrfbckhh-collab/homekit-camera-gstreamer/actions/workflows/lint.yml)

## 特徴
- マルチストリーミング対応
    - 複数のデバイスへ同時にストリーミングできます。
    - PipeWireやネットワークストリームなど、複数クライアントから同時に利用できる入力ソースが必要です。
- GStreamerが対応しているほぼすべてのソースに対応
    - PipeWire
    - USB/Webカメラ
    - Raspberry Pi Camera Module
    - ネットワークストリーム
    - ファイル
    - etc.
- H.264エンコーダーの自動選択 (encodebin)
    - `openh264enc`
    - `v4l2h264enc`
    - etc.
- ストリーミング中の動的な解像度変更
    - HomeKitからの要求に応じて、ストリーミング中でも解像度を変更できます。

## 動作確認済み環境
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
> Raspberry Pi Camera Moduleなどlibcameraを使用するカメラの場合は追加で以下のパッケージが必要です。
> ```bash
> sudo apt install libspa-0.2-libcamera libcamera-ipa
> ```
> `libspa-0.2-libcamera` が利用できない環境では、以下を試してください。
> ```bash
> sudo apt install pipewire-libcamera libcamera-ipa
> ```
### デフォルトカメラの設定
``` bash
wpctl status
wpctl set-default [カメラのID]
```
> [カメラのID]はwpctl statusのSourcesの結果に合わせて書き換えて下さい。

### 実行
使用するカメラのアスペクト比に合わせてサンプルを選択してください。

[16:9カメラ向けサンプルコード](examples/pipewire-16:9.py)
- 一般的なカメラ、Raspberry Pi Camera Module 3など

[4:3カメラ向けサンプルコード](examples/pipewire-4:3.py)
- Raspberry Pi Camera Module 1 / 2など
