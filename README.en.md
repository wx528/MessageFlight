# MessageFlight ✈️

[中文](README.md)

Let Windows notifications fly across your screen like a little plane 🎈

## Screenshots

| | | |
|:---:|:---:|:---:|
| ![Plane flying above a game window](screenshots/screen_top_on_game01.png) | ![Plane flying above a game window](screenshots/screen_top_on_game02.png) | ![Plane flying across the desktop](screenshots/screen_top_on_screen.png) |

## Features

- 🛩️ **Animated plane**: flies from the left edge to the right with a gentle float effect
- 📢 **Real system notifications**: listens to the Windows notification center (via `winsdk`)
- 🎨 **Tray menu**: pause, autostart, and quit
- 🔍 **Permission status**: shows notification listener permission state
- 🧪 **Demo fallback**: falls back to built-in demo notifications when `winsdk` is unavailable

## Quick Start

Requires Windows 10/11 and Python 3.8+.

Using `pip`:

```bash
git clone https://github.com/wx528/MessageFlight.git
cd MessageFlight

python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt
python message_flight.py
```

Run `deactivate` to leave the virtual environment when you're done.

Using [`uv`](https://docs.astral.sh/uv/) (faster):

```bash
git clone https://github.com/wx528/MessageFlight.git
cd MessageFlight

uv venv
uv pip install -r requirements.txt
uv run python message_flight.py
```

[MIT License](LICENSE)
