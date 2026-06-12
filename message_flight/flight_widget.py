"""Main flight widget that animates the plane across the screen."""
import random
from typing import Any, Optional

from PyQt6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, Qt, QTimer
from PyQt6.QtWidgets import QApplication, QWidget

from message_flight.demo_notifications import NOTIFICATIONS
from message_flight.notification_queue import NotificationQueue
from message_flight.plane_banner import PlaneBanner

_VALID_FLY_PATHS = (
    "horizontal",
    "vertical_pong",
    "zigzag_top_down",
    "zigzag_bottom_up",
    "around",
)


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
        notification_queue_max_size: int = 20,
        plane_colors: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        # Note: WA_TransparentForMouseEvents removed to allow plane interaction

        primary_screen = QApplication.primaryScreen()
        if primary_screen is None:
            raise RuntimeError("No primary screen available")
        screen = primary_screen.geometry()
        self.screen_w = screen.width()
        self.screen_h = screen.height()
        self.setGeometry(0, 0, self.screen_w, self.screen_h)

        self.plane: PlaneBanner
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

        # 飞行状态
        self._fly_count = 0
        self._fly_direction = 1  # 1 = left→right, -1 = right→left
        self._pong_direction = 1  # 1 = down, -1 = up
        self._fly_stopped = False

        # zigzag / around 状态
        self._zigzag_row = 0
        self._zigzag_direction = 1  # 1 = left→right, -1 = right→left
        self._around_step = 0

        # 通知队列
        self._notification_queue = NotificationQueue(max_size=notification_queue_max_size)
        self._last_dropped_count = 0

        start_y = self._compute_start_y()
        self.plane.move(-self.plane.width(), start_y)

        self._setup_float_animation()
        self._setup_fly_animation()

        self.msg_index = 0
        # 禁用自动轮播演示消息（只在用户点击"发送演示通知"时切换）
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._next_message)
        # 不再自动启动 timer
        # self.timer.start(self._notification_interval_ms)

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
            self._setup_vertical_pong()
            return
        if self._fly_path == "zigzag_top_down":
            self._setup_zigzag_top_down()
            return
        if self._fly_path == "zigzag_bottom_up":
            self._setup_zigzag_bottom_up()
            return
        if self._fly_path == "around":
            self._setup_around()
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

    def _setup_vertical_pong(self):
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

    def _setup_zigzag_top_down(self):
        self._zigzag_row = 0
        self._zigzag_direction = 1
        start_y = 0
        end_y = start_y
        duration = int(self._fly_duration_ms * 0.6)
        self.fly_anim = QPropertyAnimation(self.plane, b"pos")
        self.fly_anim.setDuration(duration)
        self.fly_anim.setStartValue(QPoint(-self.plane.width(), start_y))
        self.fly_anim.setEndValue(QPoint(self.screen_w + 50, end_y))
        self.fly_anim.setEasingCurve(QEasingCurve.Type.Linear)
        self.fly_anim.finished.connect(self._on_fly_finished)
        self.fly_anim.start()

    def _setup_zigzag_bottom_up(self):
        self._zigzag_row = 0
        self._zigzag_direction = 1
        start_y = self.screen_h - self.plane.height()
        end_y = start_y
        duration = int(self._fly_duration_ms * 0.6)
        self.fly_anim = QPropertyAnimation(self.plane, b"pos")
        self.fly_anim.setDuration(duration)
        self.fly_anim.setStartValue(QPoint(-self.plane.width(), start_y))
        self.fly_anim.setEndValue(QPoint(self.screen_w + 50, end_y))
        self.fly_anim.setEasingCurve(QEasingCurve.Type.Linear)
        self.fly_anim.finished.connect(self._on_fly_finished)
        self.fly_anim.start()

    def _setup_around(self):
        self._around_step = 0
        margin = 20
        start_y = int(self.screen_h * self._initial_y_ratio)
        self.fly_anim = QPropertyAnimation(self.plane, b"pos")
        self.fly_anim.setDuration(int(self._fly_duration_ms * 0.5))
        self.fly_anim.setStartValue(QPoint(-self.plane.width(), start_y))
        self.fly_anim.setEndValue(QPoint(self.screen_w + margin, start_y))
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

        # 队列里有等待显示的通知：切换横幅文字，但保持当前飞行轨迹不重置
        next_text = self._notification_queue.dequeue()
        if next_text is not None:
            self.plane.set_text(next_text)

        if self._fly_path == "vertical_pong":
            self._on_vertical_pong_finished()
            return
        if self._fly_path in ("zigzag_top_down", "zigzag_bottom_up"):
            self._on_zigzag_finished()
            return
        if self._fly_path == "around":
            self._on_around_finished()
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
            self.plane.set_facing_direction(self._fly_direction)
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

    def _on_vertical_pong_finished(self):
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

    def _on_zigzag_finished(self):
        row_height = max(80, self.screen_h // 4)
        self._zigzag_row += 1
        self._zigzag_direction *= -1

        going_down = self._fly_path == "zigzag_top_down"
        current_y = self._zigzag_row * row_height
        if not going_down:
            current_y = self.screen_h - self.plane.height() - (self._zigzag_row * row_height)

        if going_down and current_y > self.screen_h:
            if self._fly_bounce:
                self._zigzag_row = 0
                self._zigzag_direction = 1
                current_y = 0
            else:
                self.fly_anim.stop()
                self._fly_stopped = True
                return
        if not going_down and current_y < -self.plane.height():
            if self._fly_bounce:
                self._zigzag_row = 0
                self._zigzag_direction = 1
                current_y = self.screen_h - self.plane.height()
            else:
                self.fly_anim.stop()
                self._fly_stopped = True
                return

        duration = int(self._fly_duration_ms * 0.6)
        if self._zigzag_direction == 1:  # left → right
            start_x = -self.plane.width()
            end_x = self.screen_w + 50
            self.plane.set_facing_direction(1)
        else:  # right → left
            start_x = self.screen_w + 50
            end_x = -self.plane.width()
            self.plane.set_facing_direction(-1)

        self.plane.move(start_x, current_y)
        self.fly_anim.setDuration(duration)
        self.fly_anim.setStartValue(QPoint(start_x, current_y))
        self.fly_anim.setEndValue(QPoint(end_x, current_y))
        self.fly_anim.start()

    def _on_around_finished(self):
        margin = 20
        self._around_step = (self._around_step + 1) % 4

        if self._around_step == 0:
            # 回到起点：左中 → 右中
            start_y = int(self.screen_h * self._initial_y_ratio)
            self.plane.move(-self.plane.width(), start_y)
            self.fly_anim.setDuration(int(self._fly_duration_ms * 0.5))
            self.fly_anim.setStartValue(QPoint(-self.plane.width(), start_y))
            self.fly_anim.setEndValue(QPoint(self.screen_w + margin, start_y))
            self.plane.set_facing_direction(1)
        elif self._around_step == 1:
            # 右中 → 右下
            start_x = self.screen_w + margin
            start_y = int(self.screen_h * self._initial_y_ratio)
            end_y = self.screen_h + margin
            self.plane.move(start_x, start_y)
            self.fly_anim.setDuration(int(self._fly_duration_ms * 0.3))
            self.fly_anim.setStartValue(QPoint(start_x, start_y))
            self.fly_anim.setEndValue(QPoint(start_x, end_y))
            self.plane.set_facing_direction(1)
        elif self._around_step == 2:
            # 右下 → 左下
            start_y = self.screen_h + margin
            self.plane.move(self.screen_w + margin, start_y)
            self.fly_anim.setDuration(int(self._fly_duration_ms * 0.5))
            self.fly_anim.setStartValue(QPoint(self.screen_w + margin, start_y))
            self.fly_anim.setEndValue(QPoint(-self.plane.width(), start_y))
            self.plane.set_facing_direction(-1)
        elif self._around_step == 3:
            # 左下 → 左上
            start_x = -self.plane.width()
            start_y = self.screen_h + margin
            end_y = -self.plane.height()
            self.plane.move(start_x, start_y)
            self.fly_anim.setDuration(int(self._fly_duration_ms * 0.3))
            self.fly_anim.setStartValue(QPoint(start_x, start_y))
            self.fly_anim.setEndValue(QPoint(start_x, end_y))
            self.plane.set_facing_direction(-1)
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
        self._pong_direction = 1
        self._zigzag_row = 0
        self._zigzag_direction = 1
        self._around_step = 0
        self.plane.set_facing_direction(1)
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
            # timer 不再自动启动
            # self.timer.start()

    def is_paused(self):
        return self._paused

    @property
    def notification_queue(self) -> NotificationQueue:
        """暴露队列以便外部代码（设置对话框、测试）查询或清空。"""
        return self._notification_queue

    def enqueue_notification(self, text: str) -> None:
        """入队一条通知，必要时立即显示（队列之前为空时）。

        队列非空时不立即显示，避免打断当前动画；这些通知会在
        :meth:`_on_fly_finished` 中按 FIFO 顺序逐条显示。
        """
        was_empty = self._notification_queue.is_empty()
        dropped = self._notification_queue.enqueue(text)
        if dropped is not None:
            self._last_dropped_count += 1
        if was_empty:
            next_text = self._notification_queue.dequeue()
            if next_text is not None:
                self.show_notification(next_text)

    def show_notification(self, text: str):
        """显示一条真实通知，并重置飞行动画按当前路径模式飞出"""
        self.plane.set_text(text)
        self.fly_anim.stop()
        # 重置飞行状态
        self._fly_direction = 1
        self._pong_direction = 1
        self._zigzag_row = 0
        self._zigzag_direction = 1
        self._around_step = 0
        self._fly_count = 0
        self._fly_stopped = False
        # 根据当前路径模式重新初始化飞行动画
        self._setup_fly_animation()
        self.timer.stop()
