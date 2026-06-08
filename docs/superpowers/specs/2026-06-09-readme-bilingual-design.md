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
| `README.md` | 中文（主） | GitHub 默认展示的入口 |
| `README.en.md` | 英文（链接） | 英文版本，作为外链提供 |

主入口是中文 README。英文版本通过中文 README 顶部徽章链接访问。

### `README.md`（中文主）结构

1. **标题区**
   - `# MessageFlight ✈️`
   - 副标题：一句话中文描述（让 Windows 通知像小飞机一样飞过屏幕）

2. **语言徽章**
   - 顶部右侧：`[English](README.en.md)`
   - 用徽章图或简洁链接都可

3. **截图区块**
   - 标题 `## 截图`
   - 三张图横向并排：`screen_top_on_game01.png`、`screen_top_on_game02.png`、`screen_top_on_screen.png`

4. **功能特性区块**
   - 标题 `## 功能特性`
   - 4-5 条 bullet：
     - 小飞机从屏幕左侧飞到右侧，附带浮动动画
     - 监听 Windows 通知中心，捕获真实系统通知
     - 系统托盘菜单支持暂停 / 开机自启 / 退出
     - 通知权限状态显示与引导
     - 未安装 `winsdk` 时回退为内置演示通知

5. **快速开始区块**
   - 标题 `## 快速开始`
   - 代码块：
     ```bash
     git clone https://github.com/wx528/MessageFlight.git
     cd MessageFlight
     pip install -r requirements.txt
     python message_flight.py
     ```

6. **底部**
   - 语言切换：`[English](README.en.md)`
   - 许可证：`[MIT License](LICENSE)`

### `README.en.md`（英文版）结构

与中文 README 章节一一对应，仅做英文本地化：
1. Title + tagline
2. Language badge：`[中文](README.md)`
3. Screenshots
4. Features
5. Quick Start（同样的 clone URL）
6. 底部语言切换 + 许可证

### 截图引用

所有截图引用使用相对路径 `screenshots/<filename>.png`，例如：

```markdown
![小飞机在游戏窗口上方飞过](screenshots/screen_top_on_game01.png)
```

三张图用 `&nbsp;` 空格或简单换行排版，GitHub 渲染下并排显示。

## 旧文件处理

- 覆盖现有 `README.md`（旧内容已含失效图链与占位符）
- 新建 `README.en.md`

## 验证

1. 仓库根目录存在 `README.md` 和 `README.en.md`
2. 三个截图路径都指向 `screenshots/` 下的实际文件
3. `git clone` 链接指向 `https://github.com/wx528/MessageFlight.git`
4. 两个文件互相指向对方
5. 许可证链接 `LICENSE` 有效
