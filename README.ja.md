# MessageFlight

[中文](README.zh.md) | [English](README.md) | 日本語 | [한국어](README.ko.md) | [Bahasa Indonesia](README.id.md) | [ไทย](README.th.md) | [Tiếng Việt](README.vi.md) | [Bahasa Melayu](README.ms.md)

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8%2B-3776AB?style=flat&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/GUI-PyQt6-41CD52?style=flat" alt="PyQt6">
  <img src="https://img.shields.io/badge/Platform-Windows%2010%2F11-0078D6?style=flat&logo=windows&logoColor=white" alt="Windows">
  <a href="https://pypi.org/project/messageflight/"><img src="https://img.shields.io/pypi/v/messageflight?style=flat&logo=pypi&logoColor=white" alt="PyPI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow?style=flat" alt="License"></a>
  <a href="https://github.com/wx528/MessageFlight/actions/workflows/ci.yml"><img src="https://github.com/wx528/MessageFlight/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <br>
  <img src="https://img.shields.io/badge/Languages-zh%20%7C%20en%20%7C%20ja%20%7C%20ko%20%7C%20id%20%7C%20th%20%7C%20vi%20%7C%20ms-8A2BE2?style=flat" alt="Languages">
</p>

Windows の通知を小さな飛行機のように画面上へ飛ばします。

## スクリーンショット

| | | |
|:---:|:---:|:---:|
| ![ゲーム画面の上を飛ぶ飛行機](screenshots/screen_top_on_game01.png) | ![ゲーム画面の上を飛ぶ飛行機](screenshots/screen_top_on_game02.png) | ![デスクトップ上を飛ぶ飛行機](screenshots/screen_top_on_screen.png) |
| ![サイバー配色の飛行機](screenshots/screen_other_color.png) | | |

## 機能

- 実際の Windows 通知を飛行機アニメーションで表示
- トレイメニューで一時停止、デモ通知、通知オフ、設定、自動起動、終了を操作
- 軽量 UI 言語: 中国語、英語、日本語、韓国語、インドネシア語、タイ語、ベトナム語、マレー語
- 配色、飛行ルート、機体プリセットをカスタマイズ可能
- SAPI または MiniMax による任意の TTS 対応

## クイックスタート

Windows 10/11 と Python 3.8+ が必要です。

```bash
git clone https://github.com/wx528/MessageFlight.git
cd MessageFlight
python -m venv .venv
.venv\Scripts\activate
pip install .
python message_flight.py
```

`uv` を使う場合:

```bash
uv sync
uv run python message_flight.py
```

[MIT License](LICENSE)
