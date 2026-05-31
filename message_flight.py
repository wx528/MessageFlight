import sys
import random
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QGraphicsDropShadowEffect, QVBoxLayout, QHBoxLayout
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QPoint, QEasingCurve, QTimer, pyqtProperty
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QFontMetrics

# ============ 模拟通知消息池 ============
NOTIFICATIONS = [
    "Meeting with Andrew in 5 min",
    "You have a new message from Mom",
    "Lunch time! 🍱",
    "Stand-up meeting starts now",
    "Don't forget to drink water",
    "Code review requested by Tom",
    "Daily report due in 30 min",
    "New email: Project Update",
]

# ============ 飞机+横幅 组件 ============
class PlaneBanner(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._banner_width = 280
        self._banner_height = 50
        self._text = ""
        self._plane_color = QColor("#FF69B4")  # 热粉色
        self._banner_color = QColor("#FFB6C1")  # 浅粉色
        self._text_color = QColor("#FFFFFF")
        self._plane_offset = 0.0  # 0~1 用于做轻微上下浮动
        self.setFixedSize(self._banner_width + 80, 80)

    def set_text(self, text: str):
        self._text = text
        # 根据文字长度动态调整横幅宽度
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

        # 轻微上下浮动
        float_y = int(self._plane_offset * 6)

        # ========== 绘制飞机 ==========
        painter.save()
        painter.translate(self._banner_width + 10, 15 + float_y)
        self._draw_plane(painter)
        painter.restore()

        # ========== 绘制横幅背景 ==========
        banner_y = 20 + float_y
        path = QPainterPath()
        rect_w = self._banner_width
        rect_h = self._banner_height
        radius = 12

        # 圆角矩形
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

        # 尾巴小三角（连接飞机）
        tail_x = rect_w
        tail_y = banner_y + rect_h // 2
        path.moveTo(tail_x, tail_y - 6)
        path.lineTo(tail_x + 10, tail_y)
        path.lineTo(tail_x, tail_y + 6)
        path.closeSubpath()

        painter.fillPath(path, self._banner_color)

        # ========== 绘制文字 ==========
        painter.setPen(self._text_color)
        font = QFont("Microsoft YaHei", 12, QFont.Weight.Bold)
        painter.setFont(font)
        fm = QFontMetrics(font)
        text_y = banner_y + (rect_h + fm.ascent() - fm.descent()) // 2
        painter.drawText(20, text_y, self._text)

        painter.end()

    def _draw_plane(self, painter: QPainter):
        """绘制一个简单可爱的小飞机"""
        c = self._plane_color
        painter.setPen(Qt.PenStyle.NoPen)

        # 机身 (椭圆)
        painter.setBrush(c)
        painter.drawEllipse(10, 18, 45, 22)

        # 机头
        painter.drawEllipse(48, 19, 14, 20)

        # 机翼
        wing_color = QColor("#FF1493")  # 深粉色
        painter.setBrush(wing_color)
        wing_path = QPainterPath()
        wing_path.moveTo(25, 25)
        wing_path.lineTo(15, 8)
        wing_path.lineTo(35, 8)
        wing_path.lineTo(40, 25)
        wing_path.closeSubpath()
        painter.drawPath(wing_path)

        # 尾翼
        tail_path = QPainterPath()
        tail_path.moveTo(12, 28)
        tail_path.lineTo(2, 18)
        tail_path.lineTo(12, 22)
        tail_path.closeSubpath()
        painter.drawPath(tail_path)

        # 窗户
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawEllipse(52, 24, 6, 6)
        painter.drawEllipse(38, 24, 5, 5)

        # 螺旋桨
        painter.setBrush(QColor("#FF69B4"))
        painter.drawEllipse(60, 26, 4, 6)
        # 桨叶
        painter.setBrush(QColor("#FFB6C1"))
        painter.drawEllipse(56, 22, 12, 3)
        painter.drawEllipse(56, 33, 12, 3)


# ============ 主窗口 ============
class FlightWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool  # 不在任务栏显示
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)  # 点击穿透

        # 获取屏幕尺寸
        screen = QApplication.primaryScreen().geometry()
        self.screen_w = screen.width()
        self.screen_h = screen.height()

        # 设置窗口全屏覆盖（只用于定位，透明部分可穿透）
        self.setGeometry(0, 0, self.screen_w, self.screen_h)

        # 创建飞机横幅组件
        self.plane = PlaneBanner(self)
        self.plane.set_text(NOTIFICATIONS[0])

        # 初始位置在屏幕左侧外
        start_y = self.screen_h // 4 + random.randint(-100, 100)
        self.plane.move(-self.plane.width(), start_y)

        # 浮动动画
        self._setup_float_animation()

        # 飞行动画
        self._setup_fly_animation()

        # 定时切换消息
        self.msg_index = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._next_message)
        self.timer.start(5000)  # 每5秒切换一次消息

    def _setup_float_animation(self):
        """飞机轻微上下浮动的动画"""
        self.float_anim = QPropertyAnimation(self.plane, b"plane_offset")
        self.float_anim.setDuration(1500)
        self.float_anim.setStartValue(0.0)
        self.float_anim.setEndValue(1.0)
        self.float_anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self.float_anim.setLoopCount(-1)  # 无限循环
        self.float_anim.start()

    def _setup_fly_animation(self):
        """从左到右飞行动画"""
        start_y = self.screen_h // 4 + random.randint(-80, 80)
        end_y = start_y + random.randint(-30, 30)

        self.fly_anim = QPropertyAnimation(self.plane, b"pos")
        self.fly_anim.setDuration(8000)  # 8秒飞过
        self.fly_anim.setStartValue(QPoint(-self.plane.width(), start_y))
        self.fly_anim.setEndValue(QPoint(self.screen_w + 50, end_y))
        self.fly_anim.setEasingCurve(QEasingCurve.Type.Linear)
        self.fly_anim.finished.connect(self._on_fly_finished)
        self.fly_anim.start()

    def _on_fly_finished(self):
        """一轮飞行结束，随机选择新Y坐标重新开始"""
        start_y = self.screen_h // 5 + random.randint(-120, 150)
        end_y = start_y + random.randint(-40, 40)
        self.fly_anim.setStartValue(QPoint(-self.plane.width(), start_y))
        self.fly_anim.setEndValue(QPoint(self.screen_w + 50, end_y))
        self.fly_anim.start()

    def _next_message(self):
        """切换下一条通知消息"""
        self.msg_index = (self.msg_index + 1) % len(NOTIFICATIONS)
        self.plane.set_text(NOTIFICATIONS[self.msg_index])

    def keyPressEvent(self, event):
        """按 ESC 退出"""
        if event.key() == Qt.Key.Key_Escape:
            self.close()


# ============ 启动 ============
if __name__ == "__main__":
    # 高DPI支持（必须在创建 QApplication 之前调用）
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)

    widget = FlightWidget()
    widget.show()
    print("MessageFlight Demo started!")
    print("Press ESC to exit")
    sys.exit(app.exec())
