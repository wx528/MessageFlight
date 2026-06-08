"""Custom QWidget that draws a plane with a notification banner."""
from PyQt6.QtCore import Qt, pyqtProperty
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QFontMetrics
from PyQt6.QtWidgets import QWidget


class PlaneBanner(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._banner_width = 280
        self._banner_height = 50
        self._text = ""
        self._plane_color = QColor("#FF69B4")
        self._banner_color = QColor("#FFB6C1")
        self._text_color = QColor("#FFFFFF")
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
        c = self._plane_color
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(c)
        painter.drawEllipse(10, 18, 45, 22)
        painter.drawEllipse(48, 19, 14, 20)

        painter.setBrush(QColor("#FFFFFF"))
        painter.drawEllipse(52, 24, 6, 6)
        painter.drawEllipse(38, 24, 5, 5)

        painter.setBrush(QColor("#FF69B4"))
        painter.drawEllipse(60, 26, 4, 6)
        painter.setBrush(QColor("#FFB6C1"))
        painter.drawEllipse(56, 22, 12, 3)
        painter.drawEllipse(56, 33, 12, 3)

    def _draw_wings(self, painter: QPainter):
        wing_color = QColor("#FF1493")
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(wing_color)
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
        painter.setPen(Qt.PenStyle.NoPen)
        outer_w = int(14 * intensity)
        painter.setBrush(QColor("#FFA500"))
        painter.drawEllipse(5, 25, outer_w, 10)
        painter.setBrush(QColor("#FF4500"))
        painter.drawEllipse(5, 25, int(10 * intensity), 7)
        painter.setBrush(QColor("#FFFF00"))
        painter.drawEllipse(5, 25, int(5 * intensity), 4)

    def _draw_plane(self, painter: QPainter):
        self._draw_thruster(painter)
        self._draw_fuselage(painter)
        self._draw_wings(painter)
