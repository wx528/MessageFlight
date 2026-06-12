"""Custom QWidget that draws a plane with a notification banner."""
import contextlib
from typing import Optional

from PyQt6.QtCore import (  # type: ignore[attr-defined]
    QDateTime,
    QRect,
    Qt,
    QTimer,
    pyqtProperty,
    pyqtSignal,
)
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPixmap
from PyQt6.QtWidgets import QWidget

from message_flight.plane_presets import get_preset

_DRAG_THRESHOLD_PX = 5
_CLICK_MAX_DURATION_MS = 250


class PlaneBanner(QWidget):
    clicked = pyqtSignal()

    def __init__(
        self,
        parent=None,
        *,
        plane_color: str = "#FF69B4",
        wing_color: str = "#FF1493",
        accent_color: str = "#FFFFFF",
        decor_color: str = "#FF69B4",
        banner_color: str = "#FFB6C1",
        text_color: str = "#FFFFFF",
        thruster_outer_color: str = "#FFA500",
        thruster_middle_color: str = "#FF4500",
        thruster_inner_color: str = "#FFFF00",
    ):
        super().__init__(parent)
        self._banner_width = 280
        self._banner_height = 50
        self._text = ""
        self._text_color = QColor(text_color)
        self._preset = get_preset("airplane")
        self._params = self._preset.get_default_params()
        # Apply any color overrides from constructor
        for attr_name in (
            "plane_color", "wing_color", "accent_color", "decor_color",
            "banner_color", "thruster_outer_color", "thruster_middle_color",
            "thruster_inner_color",
        ):
            val = locals()[attr_name]
            if hasattr(self._params, attr_name):
                setattr(self._params, attr_name, val)
        self._plane_offset = 0.0
        self._facing_direction = 1  # 1 = 朝右, -1 = 朝左
        self.setFixedSize(self._banner_width + 80, 80)

        # 交互状态
        self._click_feedback_text = ""
        self._click_feedback_timer = None
        self._dragging = False
        self._drag_start_pos = None
        self._drag_start_global = None
        self._press_pos = None
        self._press_time_ms = 0

    def _ensure_feedback_timer(self):
        if self._click_feedback_timer is None:
            try:
                self._click_feedback_timer = QTimer(self)
                self._click_feedback_timer.setSingleShot(True)
                self._click_feedback_timer.timeout.connect(self._hide_click_feedback)
            except RuntimeError:
                pass

    def _hide_click_feedback(self):
        self._click_feedback_text = ""
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_pos = event.pos()
            self._press_time_ms = QDateTime.currentMSecsSinceEpoch()
            self._dragging = True
            self._drag_start_pos = event.pos()
            self._drag_start_global = event.globalPosition().toPoint()
            # 显示点击反馈
            self._click_feedback_text = "✈️ 收到!"
            self._ensure_feedback_timer()
            if self._click_feedback_timer is not None:
                self._click_feedback_timer.start(1500)
            self.update()
            # 通知父窗口暂停飞行动画
            parent = self.parent()
            if parent and hasattr(parent, "set_paused"):
                parent.set_paused(True)
            event.accept()

    def mouseMoveEvent(self, event):
        if self._dragging and self.parent():
            delta = event.globalPosition().toPoint() - self._drag_start_global
            new_pos = self.pos() + delta
            # 限制在屏幕范围内
            new_pos.setX(max(-self.width() + 50, min(new_pos.x(), self.parent().width() - 50)))
            new_pos.setY(max(-self.height() + 50, min(new_pos.y(), self.parent().height() - 50)))
            self.move(new_pos)
            self._drag_start_global = event.globalPosition().toPoint()
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self._press_pos is not None:
                moved = (event.pos() - self._press_pos).manhattanLength()
                held_ms = QDateTime.currentMSecsSinceEpoch() - self._press_time_ms
                if moved < _DRAG_THRESHOLD_PX and held_ms < _CLICK_MAX_DURATION_MS:
                    self.clicked.emit()
                self._press_pos = None
            self._dragging = False
            self._drag_start_pos = None
            self._drag_start_global = None
            # 通知父窗口恢复飞行动画
            parent = self.parent()
            if parent and hasattr(parent, "set_paused"):
                parent.set_paused(False)
            event.accept()

    def is_dragging(self) -> bool:
        return self._dragging

    def _generate_plane_cache(self) -> None:
        """Render the plane preset to an off-screen pixmap for fast blitting."""
        size = 100
        self._plane_cache = QPixmap(size, size)
        self._plane_cache.fill(Qt.GlobalColor.transparent)
        painter = QPainter(self._plane_cache)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Translate by (20,20) so negative coordinates (e.g. bird wings) don't get clipped
        painter.translate(20, 20)
        rotation = getattr(self._params, 'rotation', 0.0)
        if rotation != 0.0:
            painter.translate(35, 40)
            painter.rotate(rotation)
            painter.translate(-35, -40)
        self._preset.draw(painter, self._params)
        painter.end()

    def _recalculate_size(self) -> None:
        """Recalculate widget size based on banner width and mount point offset."""
        attach_x = getattr(self._params, 'banner_attach_x', 0)
        extra = max(0, -2 * attach_x, attach_x - 80)
        self.setFixedSize(self._banner_width + 100 + extra, 100)

    def set_text(self, text: str):
        self._text = text
        fm = QFontMetrics(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        tw = fm.horizontalAdvance(text) + 40
        self._banner_width = max(200, tw)
        self._recalculate_size()
        self.update()

    def _plane_rect(self) -> QRect:
        """Return the bounding rect of the plane area (approximate)."""
        float_y = int(self._plane_offset * 6)
        attach_x = getattr(self._params, 'banner_attach_x', 0)
        extra_left = max(0, -attach_x)
        if self._facing_direction == 1:
            plane_x = extra_left + self._banner_width + 10
        else:
            plane_x = extra_left
        return QRect(plane_x, 35 + float_y, 100, 100)

    def _banner_rect(self) -> QRect:
        """Return the bounding rect of the banner area."""
        float_y = int(self._plane_offset * 6)
        attach_x = getattr(self._params, 'banner_attach_x', 0)
        extra_left = max(0, -attach_x)
        if self._facing_direction == 1:
            plane_x = extra_left + self._banner_width + 10
            mount_x = plane_x + attach_x
            bx = mount_x - self._banner_width - 10
        else:
            plane_x = extra_left
            mount_x = plane_x + 100 - attach_x
            bx = mount_x + 10
        by = 35 + float_y + getattr(self._params, 'banner_attach_y', 35) - self._banner_height // 2
        return QRect(bx, by, self._banner_width + 20, self._banner_height + 20)

    def set_facing_direction(self, direction: int) -> None:
        """Set the facing direction (1 = right, -1 = left) and trigger repaint."""
        self._facing_direction = direction
        self.update()

    def _get_color(self, name: str) -> QColor:
        """Return a QColor for the given attribute name from _params."""
        value = getattr(self._params, name, "#FFFFFF")
        return QColor(value)

    def get_plane_offset(self):
        return self._plane_offset

    def set_plane_offset(self, val: float):
        old_rect = self._plane_rect()
        self._plane_offset = val
        new_rect = self._plane_rect()
        self.update(old_rect.united(new_rect))

    plane_offset = pyqtProperty(float, get_plane_offset, set_plane_offset)

    def update_colors(
        self,
        *,
        plane_color: Optional[str] = None,
        wing_color: Optional[str] = None,
        accent_color: Optional[str] = None,
        decor_color: Optional[str] = None,
        banner_color: Optional[str] = None,
        text_color: Optional[str] = None,
        thruster_outer_color: Optional[str] = None,
        thruster_middle_color: Optional[str] = None,
        thruster_inner_color: Optional[str] = None,
    ) -> None:
        """Replace any of the 9 color attributes and request a repaint.

        All arguments are keyword-only to match the ``__init__`` style.
        A ``None`` argument leaves the corresponding color unchanged, which
        lets callers forward ``**cfg.colors`` without worrying about missing
        keys. A single ``update()`` is issued at the end so the repaint is
        coalesced.
        """
        params_mapping = {
            "plane_color": plane_color,
            "wing_color": wing_color,
            "accent_color": accent_color,
            "decor_color": decor_color,
            "banner_color": banner_color,
            "thruster_outer_color": thruster_outer_color,
            "thruster_middle_color": thruster_middle_color,
            "thruster_inner_color": thruster_inner_color,
        }
        for attr, value in params_mapping.items():
            if value is not None and hasattr(self._params, attr):
                setattr(self._params, attr, value)
        if text_color is not None:
            self._text_color = QColor(text_color)
            if hasattr(self._params, "text_color"):
                self._params.text_color = text_color
        with contextlib.suppress(AttributeError):
            del self._plane_cache
        self.update()

    def apply_preset(self, preset, params) -> None:
        """Replace the active preset and its params, then request a repaint."""
        self._preset = preset
        self._params = params
        # sync banner/text colors if the new params carry them
        if hasattr(params, "text_color"):
            self._text_color = QColor(params.text_color)
        self._recalculate_size()
        with contextlib.suppress(AttributeError):
            del self._plane_cache
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        float_y = int(self._plane_offset * 6)

        attach_x = getattr(self._params, 'banner_attach_x', 0)
        attach_y = getattr(self._params, 'banner_attach_y', 35)
        extra_left = max(0, -attach_x)

        if self._facing_direction == 1:
            # 左→右：飞船在右，横幅在左
            plane_x = extra_left + self._banner_width + 10
            plane_y = 35 + float_y

            mount_x = plane_x + attach_x
            mount_y = plane_y + attach_y

            bx = mount_x - self._banner_width - 10
            by = mount_y - self._banner_height // 2

            self._draw_banner(painter, bx, by, tail_on_right=True)
            self._draw_plane(painter, plane_x, plane_y, facing=1)
        else:
            # 右→左：飞船在左，横幅在右
            plane_x = extra_left
            plane_y = 35 + float_y

            # facing=-1 时 _draw_plane 内部进行了 scale(-1,1) + translate(-100,0)
            # 局部坐标 (x,y) 在世界坐标中 = (plane_x + 100 - x, plane_y + y)
            mount_x = plane_x + 100 - attach_x
            mount_y = plane_y + attach_y

            bx = mount_x + 10
            by = mount_y - self._banner_height // 2

            self._draw_banner(painter, bx, by, tail_on_right=False)
            self._draw_plane(painter, plane_x, plane_y, facing=-1)

        # 绘制点击反馈气泡
        if self._click_feedback_text:
            self._draw_click_feedback(painter)

        painter.end()

    def _draw_click_feedback(self, painter: QPainter):
        """Draw a temporary click feedback bubble above the plane."""
        fm = QFontMetrics(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
        text_w = fm.horizontalAdvance(self._click_feedback_text) + 16
        text_h = fm.height() + 8
        bubble_x = (self.width() - text_w) // 2
        bubble_y = 5

        path = QPainterPath()
        path.addRoundedRect(bubble_x, bubble_y, text_w, text_h, 8, 8)
        painter.fillPath(path, QColor(0, 0, 0, 180))

        painter.setPen(Qt.GlobalColor.white)
        font = QFont("Microsoft YaHei", 10, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(bubble_x, bubble_y, text_w, text_h, Qt.AlignmentFlag.AlignCenter, self._click_feedback_text)

    def _draw_banner(self, painter: QPainter, bx: int, by: int, tail_on_right: bool):
        """Draw the notification banner at (bx, by).

        Args:
            tail_on_right: True = tail on right edge (plane on right);
                           False = tail on left edge (plane on left).
        """
        path = QPainterPath()
        rect_w = self._banner_width
        rect_h = self._banner_height
        radius = 12

        path.moveTo(bx + radius, by)
        path.lineTo(bx + rect_w - radius, by)
        path.arcTo(bx + rect_w - radius * 2, by, radius * 2, radius * 2, 90, -90)
        path.lineTo(bx + rect_w, by + rect_h - radius)
        path.arcTo(bx + rect_w - radius * 2, by + rect_h - radius * 2, radius * 2, radius * 2, 0, -90)
        path.lineTo(bx + radius, by + rect_h)
        path.arcTo(bx, by + rect_h - radius * 2, radius * 2, radius * 2, -90, -90)
        path.lineTo(bx, by + radius)
        path.arcTo(bx, by, radius * 2, radius * 2, 180, -90)
        path.closeSubpath()

        tail_y = by + rect_h // 2
        if tail_on_right:
            tail_x = bx + rect_w
            path.moveTo(tail_x, tail_y - 6)
            path.lineTo(tail_x + 10, tail_y)
            path.lineTo(tail_x, tail_y + 6)
        else:
            tail_x = bx
            path.moveTo(tail_x, tail_y - 6)
            path.lineTo(tail_x - 10, tail_y)
            path.lineTo(tail_x, tail_y + 6)
        path.closeSubpath()

        painter.fillPath(path, self._get_color("banner_color"))

        painter.setPen(self._text_color)
        font = QFont("Microsoft YaHei", 12, QFont.Weight.Bold)
        painter.setFont(font)
        fm = QFontMetrics(font)
        text_y = by + (rect_h + fm.ascent() - fm.descent()) // 2
        painter.drawText(bx + 20, text_y, self._text)

    def _draw_plane(self, painter: QPainter, px: int, py: int, facing: int):
        """Draw the plane at (px, py) using cached pixmap.

        Args:
            facing: 1 = head points right; -1 = head points left.
        """
        if not hasattr(self, '_plane_cache') or self._plane_cache.isNull():
            self._generate_plane_cache()
        painter.save()
        painter.translate(px, py)
        if facing == -1:
            painter.scale(-1, 1)
            painter.translate(-100, 0)
        painter.drawPixmap(0, 0, self._plane_cache)
        painter.restore()
