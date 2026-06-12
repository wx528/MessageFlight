# MessageFlight

[中文](README.zh.md) | [English](README.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Bahasa Indonesia](README.id.md) | [ไทย](README.th.md) | Tiếng Việt | [Bahasa Melayu](README.ms.md)

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

Đưa thông báo Windows bay qua màn hình như một chiếc máy bay nhỏ.

## Ảnh chụp màn hình

| | | |
|:---:|:---:|:---:|
| ![Máy bay bay phía trên cửa sổ game](screenshots/screen_top_on_game01.png) | ![Máy bay bay phía trên cửa sổ game](screenshots/screen_top_on_game02.png) | ![Máy bay bay qua màn hình desktop](screenshots/screen_top_on_screen.png) |
| ![Máy bay với preset màu cyber](screenshots/screen_other_color.png) | | |

## Tính năng

- Hiển thị thông báo Windows thật bằng hoạt ảnh máy bay
- Menu khay hệ thống để tạm dừng, gửi demo, không làm phiền, cài đặt, tự khởi động và thoát
- UI đa ngôn ngữ nhẹ: zh, en, ja, ko, id, th, vi và ms
- Tùy chỉnh màu sắc, đường bay và preset phương tiện
- Hỗ trợ TTS tùy chọn qua SAPI hoặc MiniMax

## Bắt đầu nhanh

Yêu cầu Windows 10/11 và Python 3.11+.

```bash
git clone https://github.com/wx528/MessageFlight.git
cd MessageFlight
python -m venv .venv
.venv\Scripts\activate
pip install .
python message_flight.py
```

Dùng `uv`:

```bash
uv sync
uv run python message_flight.py
```

[MIT License](LICENSE)
