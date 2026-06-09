"""Main flight widget that animates the plane across the screen."""
import random

from PyQt6.QtCore import Qt, QPropertyAnimation, QPoint, QEasingCurve, QTimer
from PyQt6.QtWidgets import QApplication, QWidget

from message_flight.demo_notifications import NOTIFICATIONS
from message_flight.plane_banner import PlaneBanner


_VALID_FLY_PATHS = ("horizontal", "vertical_pong", "zigzag_top_down", "zigzag_bottom_up", "around")


class FlightWidget(QWidget):
    def __init__(
        self,
        *,
        float_duration_ms: int = 1500,
        fly_duration_ms: int = 8000,
        fly_loop_count: int = -1,
        fly_bounce: bool = False,
        fly_path: str = "horizontal",
        initial_y_ratio: float = 0.25,
        re_flight_y_ratio: float = 0.2,
        re_flight_x_ratio: float = 0.5,
        vertical_jitter: int = 100,
        re_flight_jitter: int = 120,
        re_flight_jitter_min_ratio: float = -1.0,
        notification_interval_ms: int = 5000,
        plane_colors: dict = None,
    ):
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

        if plane_colors is None:
            self.plane = PlaneBanner(self)
        else:
            self.plane = PlaneBanner(self, **plane_colors)
        self.plane.set_text(NOTIFICATIONS[0])

        # 飞行行为配置
        self._float_duration_ms = int(float_duration_ms)
        self._fly_duration_ms = int(fly_duration_ms)
        self._fly_loop_count = int(fly_loop_count)
        self._fly_bounce = bool(fly_bounce)
        self._fly_path = fly_path
        self._initial_y_ratio = float(initial_y_ratio)
        self._re_flight_y_ratio = float(re_flight_y_ratio)
        self._re_flight_x_ratio = max(0.0, min(1.0, float(re_flight_x_ratio)))
        self._vertical_jitter = int(vertical_jitter)
        self._re_flight_jitter = int(re_flight_jitter)
        self._re_flight_jitter_min_ratio = float(re_flight_jitter_min_ratio)
        self._notification_interval_ms = int(notification_interval_ms)

        if self._fly_path not in _VALID_FLY_PATHS:
            raise ValueError(
                f"fly_path must be one of {_VALID_FLY_PATHS}, got {self._fly_path!r}"
            )
        if self._fly_path in ("zigzag_top_down", "zigzag_bottom_up"):
            raise NotImplementedError(
                f"{self._fly_path} path not implemented in this task"
            )
        if self._fly_path == "around":
            raise NotImplementedError("around path not implemented in this task")

        # 飞行状态
        self._fly_count = 0
        self._fly_direction = 1  # 1 = left→right, -1 = right→left
        self._pong_direction = 1  # 1 = down, -1 = up
        self._fly_stopped = False

        start_y = self._compute_start_y()
        self.plane.move(-self.plane.width(), start_y)

        self._setup_float_animation()
        self._setup_fly_animation()

        self.msg_index = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._next_message)
        self.timer.start(self._notification_interval_ms)

        self._paused = False

    def _compute_start_y(self) -> int:
        """根据 initial_y_ratio + vertical_jitter 算 y 坐标。"""
        base = int(self.screen_h * self._initial_y_ratio)
        return base + random.randint(-self._vertical_jitter, self._vertical_jitter)

    def _setup_float_animation(self):
        self.float_anim = QPropertyAnimation(self.plane, b"plane_offset")
        self.float_anim.setDuration(self._float_duration_ms)
        self.float_anim.setStartValue(0.0)
        self.float_anim.setEndValue(1.0)
        self.float_anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self.float_anim.setLoopCount(-1)
        self.float_anim.start()

    def _setup_fly_animation(self):
        if self._fly_path == "vertical_pong":
            start_x = int(self.screen_w * self._re_flight_x_ratio) + random.randint(-100, 100)
            start_y = -self.plane.height()
            end_y = self.screen_h + 50
            self.fly_anim = QPropertyAnimation(self.plane, b"pos")
            self.fly_anim.setDuration(self._fly_duration_ms)
            self.fly_anim.setStartValue(QPoint(start_x, start_y))
            self.fly_anim.setEndValue(QPoint(start_x, end_y))
            self.fly_anim.setEasingCurve(QEasingCurve.Type.Linear)
            self.fly_anim.finished.connect(self._on_fly_finished)
            self.fly_anim.start()
            return

        start_y = self._compute_start_y()
        end_y = start_y + random.randint(-30, 30)
        self.fly_anim = QPropertyAnimation(self.plane, b"pos")
        self.fly_anim.setDuration(self._fly_duration_ms)
        self.fly_anim.setStartValue(QPoint(-self.plane.width(), start_y))
        self.fly_anim.setEndValue(QPoint(self.screen_w + 50, end_y))
        self.fly_anim.setEasingCurve(QEasingCurve.Type.Linear)
        self.fly_anim.finished.connect(self._on_fly_finished)
        self.fly_anim.start()

    def _on_fly_finished(self):
        if self._fly_stopped:
            return

        self._fly_count += 1
        if 0 < self._fly_loop_count <= self._fly_count:
            # 达到循环次数，飞机停在最后一次结束位置
            self.fly_anim.stop()
            self._fly_stopped = True
            return

        if self._fly_path == "vertical_pong":
            current_pos = self.plane.pos()
            new_x = current_pos.x() + random.randint(30, 80)

            if new_x > self.screen_w + 100:
                if self._fly_bounce and not self._fly_stopped:
                    new_x = int(self.screen_w * self._re_flight_x_ratio) + random.randint(-100, 100)
                    self.plane.move(new_x, -self.plane.height())
                    self.fly_anim.setStartValue(QPoint(new_x, -self.plane.height()))
                    self.fly_anim.setEndValue(QPoint(new_x, self.screen_h + 50))
                    self.fly_anim.start()
                else:
                    self.fly_anim.stop()
                    self._fly_stopped = True
                return

            if self._pong_direction == 1:  # was going down
                self._pong_direction = -1
                self.plane.move(new_x, self.screen_h + 50)
                self.fly_anim.setStartValue(QPoint(new_x, self.screen_h + 50))
                self.fly_anim.setEndValue(QPoint(new_x, -self.plane.height()))
            else:  # was going up
                self._pong_direction = 1
                self.plane.move(new_x, -self.plane.height())
                self.fly_anim.setStartValue(QPoint(new_x, -self.plane.height()))
                self.fly_anim.setEndValue(QPoint(new_x, self.screen_h + 50))
            self.fly_anim.start()
            return

        start_y_base = int(self.screen_h * self._re_flight_y_ratio)
        start_y = start_y_base + random.randint(
            int(self._re_flight_jitter * self._re_flight_jitter_min_ratio),
            self._re_flight_jitter,
        )

        if self._fly_bounce:
            # 来回飞：切换方向，从对面进入
            if self._fly_direction == 1:
                new_start_x = self.screen_w + 50
                new_end_x = -self.plane.width()
                self._fly_direction = -1
            else:
                new_start_x = -self.plane.width()
                new_end_x = self.screen_w + 50
                self._fly_direction = 1
            self.plane._facing_direction = self._fly_direction
            self.plane.update()
            end_y = start_y + random.randint(-30, 30)
            self.plane.move(new_start_x, start_y)
            self.fly_anim.setStartValue(QPoint(new_start_x, start_y))
            self.fly_anim.setEndValue(QPoint(new_end_x, end_y))
            self.fly_anim.start()
        else:
            # 单向飞：从左到右，循环
            end_y = start_y + random.randint(-30, 30)
            self.fly_anim.setStartValue(QPoint(-self.plane.width(), start_y))
            self.fly_anim.setEndValue(QPoint(self.screen_w + 50, end_y))
            self.fly_anim.start()

    def _next_message(self):
        self.msg_index = (self.msg_index + 1) % len(NOTIFICATIONS)
        self.plane.set_text(NOTIFICATIONS[self.msg_index])

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide()

    def set_flight_kwargs(self, **kwargs) -> None:
        """热更新飞行参数，无需重启应用。"""
        if "fly_path" in kwargs:
            self._fly_path = kwargs["fly_path"]
        if "fly_loop_count" in kwargs:
            self._fly_loop_count = int(kwargs["fly_loop_count"])
        if "fly_bounce" in kwargs:
            self._fly_bounce = bool(kwargs["fly_bounce"])
        if "fly_duration_ms" in kwargs:
            self._fly_duration_ms = int(kwargs["fly_duration_ms"])
        if "float_duration_ms" in kwargs:
            self._float_duration_ms = int(kwargs["float_duration_ms"])
        if "notification_interval_ms" in kwargs:
            self._notification_interval_ms = int(kwargs["notification_interval_ms"])
            self.timer.setInterval(self._notification_interval_ms)
        if "vertical_jitter" in kwargs:
            self._vertical_jitter = int(kwargs["vertical_jitter"])
        if "re_flight_y_ratio" in kwargs:
            self._re_flight_y_ratio = float(kwargs["re_flight_y_ratio"])
        if "re_flight_x_ratio" in kwargs:
            self._re_flight_x_ratio = max(0.0, min(1.0, float(kwargs["re_flight_x_ratio"])))
        if "re_flight_jitter" in kwargs:
            self._re_flight_jitter = int(kwargs["re_flight_jitter"])

        # 重置飞行状态，用新参数重新开始
        self._fly_count = 0
        self._fly_direction = 1
        self.plane._facing_direction = 1
        self.plane.update()
        self._fly_count = 0
        self._fly_stopped = False
        if hasattr(self, "fly_anim"):
            self.fly_anim.stop()
        if hasattr(self, "float_anim"):
            self.float_anim.stop()
        self._setup_float_animation()
        self._setup_fly_animation()

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
        start_y = self._compute_start_y()
        end_y = start_y + random.randint(-30, 30)
        self.fly_anim.stop()
        # show_notification 总是强制单向从左到右（用户行为兼容）
        self._fly_direction = 1
        self._pong_direction = 1
        self._fly_count = 0
        self._fly_stopped = False
        self.fly_anim.setStartValue(QPoint(-self.plane.width(), start_y))
        self.fly_anim.setEndValue(QPoint(self.screen_w + 50, end_y))
        self.fly_anim.start()
        self.timer.stop()
        QTimer.singleShot(15000, self.timer.start)
