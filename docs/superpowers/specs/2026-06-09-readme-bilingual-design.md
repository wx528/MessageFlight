# MessageFlight 双语 README 设计

## 目标

为 MessageFlight 项目写一份精简、双语的 README，结构覆盖项目名、截图、核心特性、一键安装运行。

## 背景

- 项目语言：Python 3.8+，使用 PyQt6 + winsdk
- 平台：仅 Windows 10/11
- 主入口：`message_flight.py`
- 截图目录：`screenshots/`（3 张图：`screen_top_on_game01.png`、`screen_top_on_game02.png`、`screen_top_on_screen.png`）
- 仓库路径：`https://github.com/wx528/MessageFlight`
- 许可证：MIT
- 已有旧 README.md 存在问题：图片引用已删除的文件 `506bc42a66d12fe62c4fd180010fef32.jpg`、GitHub 路径为占位符 `yourusername`、未引用新截图

## 设计

### 文件结构

| 文件 | 语言 | 说明 |
|---|---|---|
| `README.md` | 英文 | GitHub 默认展示的入口 |
| `README.zh-CN.md` | 中文 | 中文用户版本，结构与英文版对称 |

两个文件互链：英文文件顶部放中文链接徽章（`[中文](README.zh-CN.md)`），中文文件顶部放英文链接徽章（`[English](README.md)`）。

### `README.md` 结构

1. **标题区**
   - `# MessageFlight ✈️`
   - 副标题：一句话英文描述（飞机拖着通知横幅飞过屏幕）

2. **Screenshots 区块**
   - 标题 `## Screenshots`
   - 三张图横向并排：`screen_top_on_game01.png`、`screen_top_on_game02.png`、`screen_top_on_screen.png`
   - 用 HTML `<table>` 或 GitHub 友好的 `![alt](path)` 列表，宽度受限场景下退化为单列

3. **Features 区块**
   - 标题 `## Features`
   - 4-5 条 bullet，核心特性：
     - Animated plane flying across screen
     - Listens to real Windows notifications (via winsdk)
     - Tray icon with pause / autostart / quit menu
     - Notification permission status display
     - Falls back to demo notifications if winsdk unavailable

4. **Quick Start 区块**
   - 标题 `## Quick Start`
   - 三个代码块：
     ```bash
     git clone https://github.com/wx528/MessageFlight.git
     cd MessageFlight
     pip install -r requirements.txt
     python message_flight.py
     ```

5. **底部**
   - 语言切换徽章：`[English](README.md) | [中文](README.zh-CN.md)`
   - 许可证徽章 / 链接：`[MIT License](LICENSE)`

### `README.zh-CN.md` 结构

与 `README.md` 一一对应，仅做中文本地化：
1. 标题区
2. 截图区块（同一目录的三张图）
3. 功能特性区块
4. 快速开始区块（含相同的 `git clone` URL，路径保留 `MessageFlight`）
5. 底部语言切换 + 许可证

### 截图引用

所有截图引用使用相对路径 `screenshots/<filename>.png`，例如：

```markdown
![Plane flying over a game window](screenshots/screen_top_on_game01.png)
```

三张图用 `&nbsp;` 空格或简单换行排版，GitHub 渲染下并排显示。

## 旧文件处理

- 覆盖现有 `README.md`（旧内容已含失效图链与占位符）
- 新建 `README.zh-CN.md`

## 验证

1. 仓库根目录存在 `README.md` 和 `README.zh-CN.md`
2. 三个截图路径都指向 `screenshots/` 下的实际文件
3. `git clone` 链接指向 `https://github.com/wx528/MessageFlight.git`
4. 两个文件互相指向对方
5. 许可证链接 `LICENSE` 有效
