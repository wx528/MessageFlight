# MessageFlight 双语 README Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 MessageFlight 写一份以中文为主的精简 README（覆盖项目名、截图、核心功能、快速开始），并新增英文版 README 作为外链。

**Architecture:** 两个 markdown 文件互链。`README.md`（中文）作为 GitHub 仓库默认入口；`README.en.md`（英文）作为外链提供。截图引用相对路径 `screenshots/`。

**Tech Stack:** Markdown（GitHub Flavored）

---

## File Structure

| 文件 | 状态 | 职责 |
|---|---|---|
| `README.md` | 覆盖现有 | 中文主入口：标题、截图、功能、快速开始、底部语言切换 + 许可证 |
| `README.en.md` | 新建 | 英文版，与中文 README 章节对应 |

---

## Task 1: 写中文 README（主入口）

**Files:**
- Modify: `README.md`（覆盖现有内容）

- [ ] **Step 1: 替换 README.md 内容为精简中文版**

用以下内容覆盖整个 `README.md`：

```markdown
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
```

- [ ] **Step 2: 验证 README.md 内容**

运行：
```powershell
Get-Content README.md
```

预期：文件含 `[English](README.en.md)` 链接、三个截图相对路径、`git clone https://github.com/wx528/MessageFlight.git`、底部 `[MIT License](LICENSE)`。

- [ ] **Step 3: 提交**

```bash
git add README.md
git commit -m "docs: rewrite README in Chinese (primary)"
```

---

## Task 2: 写英文 README（外链版）

**Files:**
- Create: `README.en.md`

- [ ] **Step 1: 新建 README.en.md**

写入以下内容：

```markdown
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

```bash
git clone https://github.com/wx528/MessageFlight.git
cd MessageFlight
pip install -r requirements.txt
python message_flight.py
```

[MIT License](LICENSE)
```

- [ ] **Step 2: 验证 README.en.md 内容**

运行：
```powershell
Get-Content README.en.md
```

预期：文件含 `[中文](README.md)` 链接、三个截图相对路径、`git clone https://github.com/wx528/MessageFlight.git`、底部 `[MIT License](LICENSE)`。

- [ ] **Step 3: 提交**

```bash
git add README.en.md
git commit -m "docs: add English README linked from Chinese primary"
```

---

## Task 3: 最终验证

**Files:** 仓库根目录

- [ ] **Step 1: 验证两个文件存在**

```powershell
Get-ChildItem -LiteralPath . -File -Filter README*.md
```

预期输出：
```
Name
----
README.en.md
README.md
```

- [ ] **Step 2: 验证截图文件存在**

```powershell
Get-ChildItem -LiteralPath screenshots -File
```

预期输出：
```
Name
----
screen_top_on_game01.png
screen_top_on_game02.png
screen_top_on_screen.png
```

- [ ] **Step 3: 交叉检查链接**

```powershell
Select-String -Path README.md -Pattern 'README.en.md'; Select-String -Path README.en.md -Pattern 'README.md'
```

预期：两个文件分别能搜到对方文件名。

- [ ] **Step 4: 提交（如有遗漏）**

若有未提交文件：
```bash
git status
git add <遗漏文件>
git commit -m "docs: complete bilingual README"
```

否则跳过。
