"""Custom QWidget that draws a plane with a notification banner."""
from typing import Optional

from PyQt6.QtCore import pyqtProperty
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPainterPath
from PyQt6.QtWidgets import QWidget

from message_flight.plane_presets import get_preset


class PlaneBanner(QWidget):
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

    def _recalculate_size(self) -> None:
        """Recalculate widget size based on banner width and mount point offset."""
        attach_x = getattr(self._params, 'banner_attach_x', 0)
        extra = max(0, -2 * attach_x, attach_x - 80)
        self.setFixedSize(self._banner_width + 80 + extra, 80)

    def set_text(self, text: str):
        self._text = text
        fm = QFontMetrics(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        tw = fm.horizontalAdvance(text) + 40
        self._banner_width = max(200, tw)
        self._recalculate_size()
        self.update()

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
        self._plane_offset = val
        self.update()

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
        self.update()

    def apply_preset(self, preset, params) -> None:
        """Replace the active preset and its params, then request a repaint."""
        self._preset = preset
        self._params = params
        self._recalculate_size()
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
            plane_y = 15 + float_y

            mount_x = plane_x + attach_x
            mount_y = plane_y + attach_y

            bx = mount_x - self._banner_width - 10
            by = mount_y - self._banner_height // 2

            self._draw_banner(painter, bx, by, tail_on_right=True)
            self._draw_plane(painter, plane_x, plane_y, facing=1)
        else:
            # 右→左：飞船在左，横幅在右
            plane_x = extra_left
            plane_y = 15 + float_y

            # facing=-1 时 _draw_plane 内部进行了 scale(-1,1) + translate(-70,0)
            # 局部坐标 (x,y) 在世界坐标中 = (plane_x + 70 - x, plane_y + y)
            mount_x = plane_x + 70 - attach_x
            mount_y = plane_y + attach_y

            bx = mount_x + 10
            by = mount_y - self._banner_height // 2

            self._draw_banner(painter, bx, by, tail_on_right=False)
            self._draw_plane(painter, plane_x, plane_y, facing=-1)

        painter.end()

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
        """Draw the plane at (px, py).

        Args:
            facing: 1 = head points right; -1 = head points left.
        """
        painter.save()
        painter.translate(px, py)
        if facing == -1:
            painter.scale(-1, 1)
            painter.translate(-70, 0)
        self._preset.draw(painter, self._params)
        painter.restore()
