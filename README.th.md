# MessageFlight

[中文](README.zh.md) | [English](README.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Bahasa Indonesia](README.id.md) | ไทย | [Tiếng Việt](README.vi.md) | [Bahasa Melayu](README.ms.md)

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

ทำให้การแจ้งเตือนของ Windows บินผ่านหน้าจอเหมือนเครื่องบินลำเล็ก

## ภาพหน้าจอ

| | | |
|:---:|:---:|:---:|
| ![เครื่องบินบินเหนือหน้าต่างเกม](screenshots/screen_top_on_game01.png) | ![เครื่องบินบินเหนือหน้าต่างเกม](screenshots/screen_top_on_game02.png) | ![เครื่องบินบินผ่านเดสก์ท็อป](screenshots/screen_top_on_screen.png) |
| ![เครื่องบินในพรีเซ็ตสีไซเบอร์](screenshots/screen_other_color.png) | | |

## คุณสมบัติ

- แสดงการแจ้งเตือน Windows จริงด้วยแอนิเมชันเครื่องบิน
- เมนูถาดระบบสำหรับหยุดชั่วคราว เดโม ห้ามรบกวน ตั้งค่า เริ่มอัตโนมัติ และออก
- รองรับภาษา UI แบบเบา: zh, en, ja, ko, id, th, vi และ ms
- ปรับแต่งสี เส้นทางบิน และพรีเซ็ตยานบินได้
- รองรับ TTS แบบเลือกใช้ผ่าน SAPI หรือ MiniMax

## เริ่มต้นอย่างรวดเร็ว

ต้องใช้ Windows 10/11 และ Python 3.11+

```bash
git clone https://github.com/wx528/MessageFlight.git
cd MessageFlight
python -m venv .venv
.venv\Scripts\activate
pip install .
python message_flight.py
```

ใช้ `uv`:

```bash
uv sync
uv run python message_flight.py
```

[MIT License](LICENSE)
