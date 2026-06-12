# MessageFlight

[中文](README.zh.md) | English | [日本語](README.ja.md) | [한국어](README.ko.md) | [Bahasa Indonesia](README.id.md) | [ไทย](README.th.md) | [Tiếng Việt](README.vi.md) | [Bahasa Melayu](README.ms.md)

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/GUI-PyQt6-41CD52?style=flat" alt="PyQt6">
  <img src="https://img.shields.io/badge/Platform-Windows%2010%2F11-0078D6?style=flat&logo=windows&logoColor=white" alt="Windows">
  <a href="https://pypi.org/project/messageflight/"><img src="https://img.shields.io/pypi/v/messageflight?style=flat&logo=pypi&logoColor=white" alt="PyPI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow?style=flat" alt="License"></a>
  <a href="https://github.com/wx528/MessageFlight/actions/workflows/ci.yml"><img src="https://github.com/wx528/MessageFlight/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <br>
  <img src="https://img.shields.io/badge/Languages-zh%20%7C%20en%20%7C%20ja%20%7C%20ko%20%7C%20id%20%7C%20th%20%7C%20vi%20%7C%20ms-8A2BE2?style=flat" alt="Languages">
</p>

Let Windows notifications fly across your screen like a little plane.

## Screenshots

| | | |
|:---:|:---:|:---:|
| ![Plane flying above a game window](screenshots/screen_top_on_game01.png) | ![Plane flying above a game window](screenshots/screen_top_on_game02.png) | ![Plane flying across the desktop](screenshots/screen_top_on_screen.png) |
| ![Plane in cyber preset](screenshots/screen_other_color.png) | | |

## Features

- Animated plane overlay for real Windows notifications
- System tray controls for pause, demo notification, do-not-disturb, settings, autostart, and quit
- Lightweight UI languages: Chinese, English, Japanese, Korean, Indonesian, Thai, Vietnamese, and Malay
- Custom colors, flight paths, and vehicle presets
- Optional TTS support through SAPI or MiniMax
- Optional voice commands via local wake word + cloud STT

## Quick Start

Requires Windows 10/11 and Python 3.11+.

```bash
git clone https://github.com/wx528/MessageFlight.git
cd MessageFlight
python -m venv .venv
.venv\Scripts\activate
pip install .
python message_flight.py
```

Using `uv`:

```bash
uv sync
uv run python message_flight.py
```

[MIT License](LICENSE)
