# MessageFlight ✈️

[English](README.en.md)

让 Windows 通知像小飞机一样飞过你的屏幕 🎈

## 截图

| | | |
|:---:|:---:|:---:|
| ![小飞机在游戏窗口上方飞过](screenshots/screen_top_on_game01.png) | ![小飞机在游戏窗口上方飞过](screenshots/screen_top_on_game02.png) | ![小飞机飞过桌面](screenshots/screen_top_on_screen.png) |

## 功能特性

- 🛩️ **小飞机动画**：从屏幕左侧飞到右侧，附带浮动效果
- 📢 **真实系统通知**：监听 Windows 通知中心（基于 `winsdk`）
- 🎨 **托盘菜单**：支持暂停 / 开机自启 / 退出
- 🔍 **权限提示**：显示通知监听权限状态
- 🧪 **演示回退**：未安装 `winsdk` 时回退为内置演示通知

## 快速开始

```bash
git clone https://github.com/wx528/MessageFlight.git
cd MessageFlight
pip install -r requirements.txt
python message_flight.py
```

[MIT License](LICENSE)
