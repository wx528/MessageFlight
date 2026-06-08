"""Main flight widget that animates the plane across the screen."""
import random

from PyQt6.QtCore import Qt, QPropertyAnimation, QPoint, QEasingCurve, QTimer
from PyQt6.QtWidgets import QApplication, QWidget

from message_flight.demo_notifications import NOTIFICATIONS
from message_flight.plane_banner import PlaneBanner


class FlightWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        screen = QApplication.primaryScreen().geometry()
        self.screen_w = screen.width()
        self.screen_h = screen.height()
        self.setGeometry(0, 0, self.screen_w, self.screen_h)

        self.plane = PlaneBanner(self)
        self.plane.set_text(NOTIFICATIONS[0])

        start_y = self.screen_h // 4 + random.randint(-100, 100)
        self.plane.move(-self.plane.width(), start_y)

        self._setup_float_animation()
        self._setup_fly_animation()

        self.msg_index = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._next_message)
        self.timer.start(5000)

        self._paused = False

    def _setup_float_animation(self):
        self.float_anim = QPropertyAnimation(self.plane, b"plane_offset")
        self.float_anim.setDuration(1500)
        self.float_anim.setStartValue(0.0)
        self.float_anim.setEndValue(1.0)
        self.float_anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self.float_anim.setLoopCount(-1)
        self.float_anim.start()

    def _setup_fly_animation(self):
        start_y = self.screen_h // 4 + random.randint(-80, 80)
        end_y = start_y + random.randint(-30, 30)
        self.fly_anim = QPropertyAnimation(self.plane, b"pos")
        self.fly_anim.setDuration(8000)
        self.fly_anim.setStartValue(QPoint(-self.plane.width(), start_y))
        self.fly_anim.setEndValue(QPoint(self.screen_w + 50, end_y))
        self.fly_anim.setEasingCurve(QEasingCurve.Type.Linear)
        self.fly_anim.finished.connect(self._on_fly_finished)
        self.fly_anim.start()

    def _on_fly_finished(self):
        start_y = self.screen_h // 5 + random.randint(-120, 150)
        end_y = start_y + random.randint(-40, 40)
        self.fly_anim.setStartValue(QPoint(-self.plane.width(), start_y))
        self.fly_anim.setEndValue(QPoint(self.screen_w + 50, end_y))
        self.fly_anim.start()

    def _next_message(self):
        self.msg_index = (self.msg_index + 1) % len(NOTIFICATIONS)
        self.plane.set_text(NOTIFICATIONS[self.msg_index])

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide()

    def set_paused(self, paused: bool):
        self._paused = paused
        if paused:
            self.fly_anim.pause()
            self.float_anim.pause()
            self.timer.stop()
        else:
            self.fly_anim.resume()
            self.float_anim.resume()
            self.timer.start()

    def is_paused(self):
        return self._paused

    def show_notification(self, text: str):
        """显示一条真实通知，并重置飞行动画让飞机立刻从左侧飞出"""
        self.plane.set_text(text)
        # 重置位置到左侧外，确保用户能立刻看到
        start_y = self.screen_h // 5 + random.randint(-100, 100)
        end_y = start_y + random.randint(-40, 40)
        self.fly_anim.stop()
        self.fly_anim.setStartValue(QPoint(-self.plane.width(), start_y))
        self.fly_anim.setEndValue(QPoint(self.screen_w + 50, end_y))
        self.fly_anim.start()
        # 暂停假数据轮播 15 秒，让用户看清真实通知
        self.timer.stop()
        QTimer.singleShot(15000, self.timer.start)
