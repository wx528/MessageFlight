# MessageFlight 性能优化实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 根据桌面宠物技术调研报告，对 MessageFlight 进行针对性性能优化，降低 CPU 占用、提升动画帧率稳定性。

**Architecture:** 采用"脏矩形更新 + 绘制缓存"双层优化策略。将程序化绘制改为预渲染缓存，并将全屏重绘改为局部更新，显著减少每帧 CPU 工作量。

**Tech Stack:** Python 3.8+, PyQt6, pytest

---

## 现状分析

**当前瓶颈（基于代码审查和调研报告）：**

| 问题 | 位置 | 影响 |
|------|------|------|
| 全屏重绘 | `plane_banner.py:58,63,75,117,127` | 每帧重绘整个 widget（横幅+飞船） |
| 程序化绘制 | `plane_banner.py:190-193` | 每帧调用 `_preset.draw()` 进行 CPU 密集型绘制 |
| 悬浮动画全屏刷新 | `set_plane_offset` → `update()` | 飞船上下浮动时横幅区域也被重绘 |
| 无绘制缓存 | - | 相同的几何图形每帧重新计算顶点 |

**优化收益预估：**
- 脏矩形更新：减少 30-50% 重绘面积
- 绘制缓存：减少 60-80% CPU 绘制时间
- 综合：帧率更稳定，CPU 占用降低

---

## Phase 1: 脏矩形更新（Dirty Rect Update）

### Task 1: 为 PlaneBanner 添加脏矩形更新支持

**Files:**
- Modify: `message_flight/plane_banner.py`
- Test: `tests/test_plane_banner.py`

**背景：** 当前所有 `.update()` 调用都是全屏重绘。根据调研报告 3.2 节，应改为仅更新变化区域。

**分析：**
- `set_plane_offset()`：只有飞船上下移动（约 12px 范围），横幅不动
- `set_facing_direction()`：飞船和横幅位置互换，需要更新两者
- `set_text()`：只改变横幅内容和宽度

**实施步骤：**

- [ ] **Step 1: 添加辅助方法计算飞船和横幅的脏矩形**

在 `PlaneBanner` 中添加：

```python
def _plane_rect(self) -> QRect:
    """Return the bounding rect of the plane area."""
    float_y = int(self._plane_offset * 6)
    # Plane is drawn at approximately (banner_width+10, 15+float_y) with size ~70x70
    return QRect(self._banner_width + 10, 15 + float_y - 5, 80, 80)

def _banner_rect(self) -> QRect:
    """Return the bounding rect of the banner area."""
    float_y = int(self._plane_offset * 6)
    return QRect(0, 20 + float_y - 5, self._banner_width + 20, self._banner_height + 10)
```

- [ ] **Step 2: 修改 `set_plane_offset` 使用脏矩形**

```python
def set_plane_offset(self, val: float):
    old_rect = self._plane_rect()
    self._plane_offset = val
    new_rect = self._plane_rect()
    self.update(old_rect.united(new_rect))
```

- [ ] **Step 3: 修改 `set_text` 使用脏矩形**

当文本改变时，只需要更新横幅区域和飞船位置（因为宽度变化会影响飞船位置）：

```python
def set_text(self, text: str):
    old_banner_rect = self._banner_rect()
    old_plane_rect = self._plane_rect()
    self._text = text
    fm = QFontMetrics(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
    tw = fm.horizontalAdvance(text) + 40
    self._banner_width = max(200, tw)
    self._recalculate_size()
    # 重绘旧区域 + 新区域
    self.update(old_banner_rect.united(old_plane_rect).united(self._banner_rect()).united(self._plane_rect()))
```

- [ ] **Step 4: 修改 `set_facing_direction` 使用脏矩形**

方向改变时整个布局翻转，仍然需要全屏更新（但可以优化为左右两半）：

```python
def set_facing_direction(self, direction: int) -> None:
    self._facing_direction = direction
    self.update()  # 方向改变需要全屏，但这种情况很少发生
```

- [ ] **Step 5: 运行测试验证**

```bash
pytest tests/test_plane_banner.py -v
```

---

## Phase 2: 飞船绘制缓存（Render Cache）

### Task 2: 实现飞船绘制缓存

**Files:**
- Modify: `message_flight/plane_banner.py`
- Test: `tests/test_plane_banner.py`

**背景：** 调研报告 4.1 节指出，程序化绘制每帧都进行 CPU 几何计算是主要瓶颈。应将飞船预渲染到 QPixmap，后续帧直接 blit。

**设计：**
- 添加 `_plane_cache: QPixmap` 缓存飞船图像
- 当颜色、预设、旋转、缩放改变时重新生成缓存
- `paintEvent` 中直接 `drawPixmap` 而不是调用 `_preset.draw()`

**实施步骤：**

- [ ] **Step 1: 添加缓存生成方法**

```python
def _generate_plane_cache(self) -> None:
    """Render the plane preset to an off-screen pixmap for fast blitting."""
    cache_size = 80 * max(1.0, getattr(self._params, 'body_scale', 1.0))
    self._plane_cache = QPixmap(int(cache_size), int(cache_size))
    self._plane_cache.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(self._plane_cache)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    # Apply rotation if any
    rotation = getattr(self._params, 'rotation', 0.0)
    if rotation != 0.0:
        painter.translate(cache_size / 2, cache_size / 2)
        painter.rotate(rotation)
        painter.translate(-cache_size / 2, -cache_size / 2)
    
    self._preset.draw(painter, self._params)
    painter.end()
```

- [ ] **Step 2: 在需要时使缓存失效并重新生成**

缓存失效条件：
- `update_colors()` 被调用
- `apply_preset()` 被调用
- `set_facing_direction()` 不改变缓存（镜像由 painter 处理）

修改 `update_colors`：
```python
def update_colors(self, ..., **kwargs) -> None:
    # ... 现有逻辑 ...
    self._generate_plane_cache()
    self.update()
```

修改 `apply_preset`：
```python
def apply_preset(self, preset, params) -> None:
    # ... 现有逻辑 ...
    self._generate_plane_cache()
    self.update()
```

- [ ] **Step 3: 修改 paintEvent 使用缓存**

```python
def paintEvent(self, event):
    painter = QPainter(self)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    # 裁剪到需要重绘的区域（event.rect()）
    painter.setClipRect(event.rect())
    
    float_y = int(self._plane_offset * 6)
    # ... 挂载点计算逻辑 ...
    
    # 绘制横幅（如果缓存未生成则生成）
    if not hasattr(self, '_plane_cache') or self._plane_cache.isNull():
        self._generate_plane_cache()
    
    # 绘制横幅
    self._draw_banner(painter, bx, by, tail_on_right=...)
    
    # 绘制飞船（使用缓存）
    painter.drawPixmap(plane_x, plane_y, self._plane_cache)
    
    painter.end()
```

- [ ] **Step 4: 运行测试验证**

```bash
pytest tests/test_plane_banner.py -v
```

---

## Phase 3: 减少不必要的 Update 调用

### Task 3: 批量更新优化

**Files:**
- Modify: `message_flight/plane_banner.py`
- Test: `tests/test_plane_banner.py`

**背景：** 调研报告 4.1 节提到，`update()` 调用应尽量合并。当前 `update_colors` 内部循环修改多个颜色，但只在最后调用一次 `update()`，这已经做得很好。但需要确认其他地方没有重复调用。

**实施步骤：**

- [ ] **Step 1: 审查所有 update() 调用点**

检查 `plane_banner.py` 中的所有 `self.update()`：
1. `set_text` - 必要（内容和尺寸变化）
2. `set_facing_direction` - 必要（方向变化）
3. `set_plane_offset` - 已优化为脏矩形
4. `update_colors` - 必要（颜色变化）
5. `apply_preset` - 必要（预设变化）

- [ ] **Step 2: 添加防抖动（可选）**

如果某些场景会快速连续调用多次 update，可以添加简单的防抖动：

```python
# 在 PlaneBanner.__init__ 中
self._pending_update = False

def _schedule_update(self):
    if not self._pending_update:
        self._pending_update = True
        QTimer.singleShot(0, self._do_update)

def _do_update(self):
    self._pending_update = False
    self.update()
```

**注意：** 仅在实测发现重复调用问题后才添加此优化。

---

## Phase 4: 内存管理优化

### Task 4: 设置 QPixmapCache 上限

**Files:**
- Modify: `message_flight/tray_app.py`
- Test: `tests/test_tray_app.py`

**背景：** 调研报告 4.4 节建议设置 `QPixmapCache` 上限防止内存泄漏。

**实施步骤：**

- [ ] **Step 1: 在 TrayApplication 初始化时设置缓存上限**

```python
from PyQt6.QtGui import QPixmapCache

class TrayApplication:
    def __init__(self) -> None:
        # 设置 Qt 内部 pixmap 缓存上限为 50MB
        QPixmapCache.setCacheLimit(1024 * 50)
        # ... 现有逻辑 ...
```

- [ ] **Step 2: 运行测试验证**

```bash
pytest tests/test_tray_app.py -v
```

---

## Phase 5: 性能测试与验证

### Task 5: 添加性能基准测试

**Files:**
- Create: `tests/test_performance.py`

**目标：** 建立可重复的性能基准，确保优化有效。

**实施步骤：**

- [ ] **Step 1: 创建性能测试文件**

```python
"""Performance benchmarks for PlaneBanner rendering."""
import time
from unittest.mock import MagicMock, patch

import pytest

from message_flight.plane_banner import PlaneBanner


class TestPlaneBannerPerformance:
    """Measure rendering performance to prevent regressions."""

    def test_100_paint_events_under_50ms(self):
        """100 consecutive paint events should complete in < 50ms total."""
        with patch("PyQt6.QtWidgets.QWidget.__init__"), \
             patch.object(PlaneBanner, "setFixedSize"):
            banner = PlaneBanner()
        
        # Simulate 100 paint events (about 1.6s of 60fps animation)
        start = time.perf_counter()
        for _ in range(100):
            banner.paintEvent(MagicMock())
        elapsed = time.perf_counter() - start
        
        assert elapsed < 0.050, f"100 paint events took {elapsed*1000:.1f}ms, expected < 50ms"

    def test_plane_offset_update_does_not_redraw_banner(self):
        """Setting plane_offset should only trigger partial update."""
        with patch("PyQt6.QtWidgets.QWidget.__init__"), \
             patch.object(PlaneBanner, "setFixedSize"):
            banner = PlaneBanner()
        
        update_calls = []
        banner.update = lambda *args: update_calls.append(args)
        
        banner.set_plane_offset(0.5)
        
        # Should be called with a rect (dirty rect), not empty (full rect)
        assert len(update_calls) == 1
        assert len(update_calls[0]) > 0, "Expected dirty rect update, got full update"
```

- [ ] **Step 2: 运行性能测试**

```bash
pytest tests/test_performance.py -v
```

- [ ] **Step 3: 运行完整测试套件**

```bash
pytest tests/ -v
```

---

## 优化优先级总结

| 优先级 | 优化项 | 预期收益 | 复杂度 |
|--------|--------|---------|--------|
| 🔴 P0 | 飞船绘制缓存 | CPU 降低 60-80% | 中 |
| 🟡 P1 | 脏矩形更新 | 重绘面积减少 30-50% | 低 |
| 🟢 P2 | QPixmapCache 上限 | 防止内存泄漏 | 低 |
| 🟢 P3 | 批量 update 合并 | 减少冗余重绘 | 低 |
| 🔵 P4 | 性能基准测试 | 防止回归 | 中 |

**推荐实施顺序：** P0 → P1 → P2 → P4 → P3

**验证标准：**
- 所有现有测试通过
- 新增性能测试通过
- 肉眼观察动画流畅度无明显变化（或更好）
- 长时间运行（30分钟）内存占用稳定
