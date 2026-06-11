# MessageFlight

[中文](README.zh.md) | [English](README.md) | [日本語](README.ja.md) | 한국어 | [Bahasa Indonesia](README.id.md) | [ไทย](README.th.md) | [Tiếng Việt](README.vi.md) | [Bahasa Melayu](README.ms.md)

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

Windows 알림이 작은 비행기처럼 화면을 날아가게 합니다.

## 스크린샷

| | | |
|:---:|:---:|:---:|
| ![게임 화면 위를 나는 비행기](screenshots/screen_top_on_game01.png) | ![게임 화면 위를 나는 비행기](screenshots/screen_top_on_game02.png) | ![데스크톱 위를 나는 비행기](screenshots/screen_top_on_screen.png) |
| ![사이버 색상 프리셋의 비행기](screenshots/screen_other_color.png) | | |

## 기능

- 실제 Windows 알림을 비행기 애니메이션으로 표시
- 트레이 메뉴에서 일시정지, 데모 알림, 방해 금지, 설정, 자동 시작, 종료 제어
- 가벼운 UI 언어 지원: 중국어, 영어, 일본어, 한국어, 인도네시아어, 태국어, 베트남어, 말레이어
- 색상, 비행 경로, 비행체 프리셋 사용자 지정
- SAPI 또는 MiniMax 기반 선택적 TTS 지원

## 빠른 시작

Windows 10/11 및 Python 3.8+가 필요합니다.

```bash
git clone https://github.com/wx528/MessageFlight.git
cd MessageFlight
python -m venv .venv
.venv\Scripts\activate
pip install .
python message_flight.py
```

`uv` 사용:

```bash
uv sync
uv run python message_flight.py
```

[MIT License](LICENSE)
