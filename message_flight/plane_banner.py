"""Custom QWidget that draws a plane with a notification banner."""
from PyQt6.QtCore import Qt, pyqtProperty
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QFontMetrics
from PyQt6.QtWidgets import QWidget


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
        self._plane_offset = 0.0
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

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        float_y = int(self._plane_offset * 6)

        painter.save()
        painter.translate(self._banner_width + 10, 15 + float_y)
        # z-order: thruster (back) → fuselage (middle) → wings (front)
        self._draw_thruster(painter)
        self._draw_fuselage(painter)
        self._draw_wings(painter)
        painter.restore()

        banner_y = 20 + float_y
        path = QPainterPath()
        rect_w = self._banner_width
        rect_h = self._banner_height
        radius = 12

        path.moveTo(radius, banner_y)
        path.lineTo(rect_w - radius, banner_y)
        path.arcTo(rect_w - radius * 2, banner_y, radius * 2, radius * 2, 90, -90)
        path.lineTo(rect_w, banner_y + rect_h - radius)
        path.arcTo(rect_w - radius * 2, banner_y + rect_h - radius * 2, radius * 2, radius * 2, 0, -90)
        path.lineTo(radius, banner_y + rect_h)
        path.arcTo(0, banner_y + rect_h - radius * 2, radius * 2, radius * 2, -90, -90)
        path.lineTo(0, banner_y + radius)
        path.arcTo(0, banner_y, radius * 2, radius * 2, 180, -90)
        path.closeSubpath()

        tail_x = rect_w
        tail_y = banner_y + rect_h // 2
        path.moveTo(tail_x, tail_y - 6)
        path.lineTo(tail_x + 10, tail_y)
        path.lineTo(tail_x, tail_y + 6)
        path.closeSubpath()

        painter.fillPath(path, self._banner_color)

        painter.setPen(self._text_color)
        font = QFont("Microsoft YaHei", 12, QFont.Weight.Bold)
        painter.setFont(font)
        fm = QFontMetrics(font)
        text_y = banner_y + (rect_h + fm.ascent() - fm.descent()) // 2
        painter.drawText(20, text_y, self._text)
        painter.end()

    def _draw_fuselage(self, painter: QPainter):
        """Draw fuselage body, nose, white dots, and pink decor."""
        c = self._plane_color
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(c)
        painter.drawEllipse(10, 18, 45, 22)
        painter.drawEllipse(48, 19, 14, 20)

        painter.setBrush(self._accent_color)
        painter.drawEllipse(52, 24, 6, 6)
        painter.drawEllipse(38, 24, 5, 5)

        painter.setBrush(self._decor_color)
        painter.drawEllipse(60, 26, 4, 6)
        painter.setBrush(self._banner_color)
        painter.drawEllipse(56, 22, 12, 3)
        painter.drawEllipse(56, 33, 12, 3)

    def _draw_wings(self, painter: QPainter):
        """Draw top wing and tail fin."""
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._wing_color)
        wing_path = QPainterPath()
        wing_path.moveTo(25, 25)
        wing_path.lineTo(15, 8)
        wing_path.lineTo(35, 8)
        wing_path.lineTo(40, 25)
        wing_path.closeSubpath()
        painter.drawPath(wing_path)

        tail_path = QPainterPath()
        tail_path.moveTo(12, 28)
        tail_path.lineTo(2, 18)
        tail_path.lineTo(12, 22)
        tail_path.closeSubpath()
        painter.drawPath(tail_path)

    def _draw_thruster(self, painter: QPainter, intensity: float = 1.0):
        """Draw the thruster flame at the plane's tail.

        Args:
            painter: QPainter instance.
            intensity: Flame width multiplier (0.5-1.5), default 1.0.
                Scales ellipse widths; height stays fixed.
        """
        painter.setPen(Qt.PenStyle.NoPen)

        # 三层 y 错落（25/26/27）让火焰视觉上更自然
        outer_w = int(14 * intensity)
        painter.setBrush(self._thruster_outer_color)
        painter.drawEllipse(5, 25, outer_w, 10)

        mid_w = int(10 * intensity)
        painter.setBrush(self._thruster_middle_color)
        painter.drawEllipse(5, 26, mid_w, 7)

        inner_w = int(5 * intensity)
        painter.setBrush(self._thruster_inner_color)
        painter.drawEllipse(5, 27, inner_w, 4)
