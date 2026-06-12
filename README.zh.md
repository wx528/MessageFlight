# MessageFlight

中文 | [English](README.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Bahasa Indonesia](README.id.md) | [ไทย](README.th.md) | [Tiếng Việt](README.vi.md) | [Bahasa Melayu](README.ms.md)

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

让 Windows 通知像小飞机一样飞过你的屏幕。

## 截图

| | | |
|:---:|:---:|:---:|
| ![小飞机在游戏窗口上方飞过](screenshots/screen_top_on_game01.png) | ![小飞机在游戏窗口上方飞过](screenshots/screen_top_on_game02.png) | ![小飞机飞过桌面](screenshots/screen_top_on_screen.png) |
| ![小飞机配色：未来赛博](screenshots/screen_other_color.png) | | |

## 功能特性

- 为真实 Windows 通知显示小飞机飞行动画
- 托盘菜单支持暂停、演示通知、免打扰、设置、开机自启和退出
- 轻量多语言界面：中文、英语、日语、韩语、印尼语、泰语、越南语、马来语
- 支持自定义配色、飞行路径和飞行器预设
- 可选 TTS：SAPI 或 MiniMax
- 可选的语音命令：本地唤醒词 + 云端 STT

## 快速开始

要求 Windows 10/11 + Python 3.11+。

```bash
git clone https://github.com/wx528/MessageFlight.git
cd MessageFlight
python -m venv .venv
.venv\Scripts\activate
pip install .
python message_flight.py
```

使用 `uv`：

```bash
uv sync
uv run python message_flight.py
```

## 注意事项

- 首次启用语音命令时，openwakeword 会自动下载约 30MB 的预训练模型，需要联网。

[MIT License](LICENSE)
