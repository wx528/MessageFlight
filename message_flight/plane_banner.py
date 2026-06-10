"""Custom QWidget that draws a plane with a notification banner."""
from typing import Optional

from PyQt6.QtCore import Qt, pyqtProperty
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QFontMetrics
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
        self._plane_color = QColor(plane_color)
        self._wing_color = QColor(wing_color)
        self._accent_color = QColor(accent_color)
        self._decor_color = QColor(decor_color)
        self._banner_color = QColor(banner_color)
        self._text_color = QColor(text_color)
        self._thruster_outer_color = QColor(thruster_outer_color)
        self._thruster_middle_color = QColor(thruster_middle_color)
        self._thruster_inner_color = QColor(thruster_inner_color)
        from message_flight.plane_presets.airplane import AirplaneParameters
        self._preset = get_preset("airplane")
        self._params = AirplaneParameters(
            plane_color=plane_color,
            wing_color=wing_color,
            accent_color=accent_color,
            decor_color=decor_color,
            banner_color=banner_color,
            thruster_outer_color=thruster_outer_color,
            thruster_middle_color=thruster_middle_color,
            thruster_inner_color=thruster_inner_color,
        )
        self._plane_offset = 0.0
        self._facing_direction = 1  # 1 = 朝右, -1 = 朝左
        self.setFixedSize(self._banner_width + 80, 80)

    def set_text(self, text: str):
        self._text = text
        fm = QFontMetrics(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        tw = fm.horizontalAdvance(text) + 40
        self._banner_width = max(200, tw)
        self.setFixedSize(self._banner_width + 80, 80)
        self.update()

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
        mapping = {
            "plane_color": ("_plane_color", plane_color),
            "wing_color": ("_wing_color", wing_color),
            "accent_color": ("_accent_color", accent_color),
            "decor_color": ("_decor_color", decor_color),
            "banner_color": ("_banner_color", banner_color),
            "text_color": ("_text_color", text_color),
            "thruster_outer_color": ("_thruster_outer_color", thruster_outer_color),
            "thruster_middle_color": ("_thruster_middle_color", thruster_middle_color),
            "thruster_inner_color": ("_thruster_inner_color", thruster_inner_color),
        }
        for attr, value in mapping.values():
            if value is not None:
                setattr(self, attr, QColor(value))
                if hasattr(self, "_params"):
                    params_attr = attr.lstrip("_")
                    setattr(self._params, params_attr, value)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        float_y = int(self._plane_offset * 6)
        banner_y = 20 + float_y

        if self._facing_direction == 1:
            # 左→右：横幅在左，飞机在右
            self._draw_banner(painter, 0, banner_y, tail_on_right=True)
            self._draw_plane(painter, self._banner_width + 10, 15 + float_y, facing=1)
        else:
            # 右→左：飞机在左，横幅在右
            plane_w = 70  # 飞机绘制区域约 70px 宽
            gap = 10
            self._draw_plane(painter, 0, 15 + float_y, facing=-1)
            self._draw_banner(painter, plane_w + gap, banner_y, tail_on_right=False)

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

        painter.fillPath(path, self._banner_color)

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
        self._preset.draw(painter, self._params, facing=1)
        painter.restore()
