"""Tests for FlightWidget customization (Task 01) + flight mode presets (Task 06)."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import sys
from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtWidgets import QApplication

from message_flight.config import FLIGHT_MODE_NAMES, FLIGHT_MODES


@pytest.fixture(scope="module")
def qapp():
    """Module-scoped QApplication — required for any PyQt6 widget construction."""
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


def _make_widget(qapp, **kwargs):
    """Build a FlightWidget with heavy mocking to skip animation/geometry setup.

    PlaneBanner.__init__ calls setFixedSize which needs QApplication — that's
    provided by the qapp fixture. We still mock the animation setup methods
    because they need a real event loop running.
    """
    from message_flight.flight_widget import FlightWidget
    fake_geometry = type("G", (), {"width": lambda self: 1920, "height": lambda self: 1080})()
    fake_screen = type("S", (), {"geometry": lambda self: fake_geometry})()
    with patch("PyQt6.QtWidgets.QApplication.primaryScreen", return_value=fake_screen), \
         patch.object(FlightWidget, "_setup_float_animation"), \
         patch.object(FlightWidget, "_setup_fly_animation"):
        return FlightWidget(**kwargs)


def test_default_constructor_no_args_uses_defaults(qapp):
    """不传任何参数时应使用默认值（向后兼容）"""
    widget = _make_widget(qapp)
    assert widget._float_duration_ms == 1500
    assert widget._fly_duration_ms == 8000
    assert widget._fly_loop_count == -1
    assert widget._fly_bounce is False
    assert widget._fly_path == "horizontal"
    assert widget._initial_y_ratio == 0.25
    assert widget._re_flight_y_ratio == 0.2
    assert widget._vertical_jitter == 100
    assert widget._re_flight_jitter == 120
    assert widget._re_flight_jitter_min_ratio == -1.0
    assert widget._notification_interval_ms == 5000


def test_fly_bounce_flag_stored(qapp):
    """fly_bounce=True 应被保存为实例属性"""
    widget = _make_widget(qapp, fly_bounce=True)
    assert widget._fly_bounce is True


def test_fly_path_horizontal_default(qapp):
    """默认路径是 horizontal"""
    widget = _make_widget(qapp)
    assert widget._fly_path == "horizontal"


def test_fly_path_horizontal_explicit(qapp):
    """显式传 horizontal 必须工作"""
    widget = _make_widget(qapp, fly_path="horizontal")
    assert widget._fly_path == "horizontal"


def test_fly_path_zigzag_top_down_accepted(qapp):
    """zigzag_top_down 路径必须被接受"""
    widget = _make_widget(qapp, fly_path="zigzag_top_down")
    assert widget._fly_path == "zigzag_top_down"


def test_fly_path_zigzag_bottom_up_accepted(qapp):
    """zigzag_bottom_up 路径必须被接受"""
    widget = _make_widget(qapp, fly_path="zigzag_bottom_up")
    assert widget._fly_path == "zigzag_bottom_up"


def test_fly_path_around_accepted(qapp):
    """around 路径必须被接受"""
    widget = _make_widget(qapp, fly_path="around")
    assert widget._fly_path == "around"


def test_fly_path_invalid_raises_value_error(qapp):
    """未知 fly_path 必须 raise ValueError"""
    with pytest.raises(ValueError, match="fly_path must be one of"):
        _make_widget(qapp, fly_path="spiral")


def test_custom_durations(qapp):
    """传入 float_duration_ms 和 fly_duration_ms 后被保存"""
    widget = _make_widget(qapp, float_duration_ms=2000, fly_duration_ms=5000)
    assert widget._float_duration_ms == 2000
    assert widget._fly_duration_ms == 5000


def test_custom_jitter_and_ratio(qapp):
    """initial_y_ratio 和 vertical_jitter 应被保存"""
    widget = _make_widget(qapp, initial_y_ratio=0.4, vertical_jitter=50)
    assert widget._initial_y_ratio == 0.4
    assert widget._vertical_jitter == 50


def test_custom_notification_interval(qapp):
    """notification_interval_ms 应被保存"""
    widget = _make_widget(qapp, notification_interval_ms=8000)
    assert widget._notification_interval_ms == 8000


def test_compute_start_y_uses_ratio_and_jitter(qapp):
    """_compute_start_y 应基于 initial_y_ratio 和 vertical_jitter"""
    widget = _make_widget(qapp, initial_y_ratio=0.5, vertical_jitter=10)
    widget.screen_h = 1000
    for _ in range(50):
        y = widget._compute_start_y()
        assert 490 <= y <= 510


def test_keyword_only_arguments(qapp):
    """所有参数必须是 keyword-only（位置传参应失败）"""
    from message_flight.flight_widget import FlightWidget
    fake_geometry = type("G", (), {"width": lambda self: 1920, "height": lambda self: 1080})()
    fake_screen = type("S", (), {"geometry": lambda self: fake_geometry})()
    with pytest.raises(TypeError):
        with patch("PyQt6.QtWidgets.QApplication.primaryScreen", return_value=fake_screen), \
             patch.object(FlightWidget, "_setup_float_animation"), \
             patch.object(FlightWidget, "_setup_fly_animation"):
            FlightWidget(2000)  # type: ignore[misc]


def test_bounce_direction_initial_state(qapp):
    """初始 _fly_direction 应为 1（左→右）"""
    widget = _make_widget(qapp, fly_bounce=True)
    assert widget._fly_direction == 1


def test_bounce_with_finite_loop_count_stops_at_limit(qapp):
    """fly_bounce=True with fly_loop_count=N: after N finishes, _fly_stopped should be True."""
    widget = _make_widget(qapp, fly_bounce=True, fly_loop_count=2)
    widget.fly_anim = MagicMock()
    assert widget._fly_loop_count == 2
    assert widget._fly_count == 0
    # Simulate first finish (left → right)
    widget._fly_direction = 1
    widget._on_fly_finished()
    assert widget._fly_count == 1
    assert widget._fly_stopped is False
    # Simulate second finish (right → left)
    widget._fly_direction = -1
    widget._on_fly_finished()
    assert widget._fly_count == 2
    assert widget._fly_stopped is True


def test_flight_widget_accepts_plane_colors_kwarg(qapp):
    """plane_colors dict must be forwarded to the inner PlaneBanner at construction time."""
    palette = {
        "plane_color": "#00FF00",
        "wing_color": "#111111",
        "accent_color": "#222222",
        "decor_color": "#333333",
        "banner_color": "#444444",
        "text_color": "#555555",
        "thruster_outer_color": "#666666",
        "thruster_middle_color": "#777777",
        "thruster_inner_color": "#888888",
    }
    widget = _make_widget(qapp, plane_colors=palette)
    assert widget.plane._params.plane_color.lower() == "#00ff00"
    assert widget.plane._params.wing_color.lower() == "#111111"
    assert widget.plane._params.thruster_inner_color.lower() == "#888888"


def test_flight_widget_accepts_all_flight_mode_kwargs(qapp):
    """For each of the 3 flight modes, unpacking FLIGHT_MODES[name] must build a valid FlightWidget.

    This guards the contract that ``cfg.flight_kwargs`` (loaded from
    QSettings) can always be splatted into ``FlightWidget(**cfg.flight_kwargs)``
    without crashing and that key instance attributes are populated.
    """
    for name in FLIGHT_MODE_NAMES:
        kwargs = FLIGHT_MODES[name]
        widget = _make_widget(qapp, **kwargs)
        # Spot-check the 7 attributes the presets actually use
        assert widget._fly_bounce == kwargs["fly_bounce"], name
        assert widget._fly_loop_count == kwargs["fly_loop_count"], name
        assert widget._fly_path == kwargs["fly_path"], name
        assert widget._fly_duration_ms == kwargs["fly_duration_ms"], name
        assert widget._float_duration_ms == kwargs["float_duration_ms"], name
        assert widget._vertical_jitter == kwargs["vertical_jitter"], name
        assert widget._notification_interval_ms == kwargs["notification_interval_ms"], name
        del widget


def test_vertical_pong_path_is_valid(qapp):
    """fly_path='vertical_pong' must be accepted without raising."""
    widget = _make_widget(qapp, fly_path="vertical_pong")
    assert widget._fly_path == "vertical_pong"


def test_re_flight_x_ratio_default(qapp):
    """Default re_flight_x_ratio must be 0.5."""
    widget = _make_widget(qapp)
    assert widget._re_flight_x_ratio == 0.5


def test_set_flight_kwargs_hot_updates_without_crash(qapp):
    """set_flight_kwargs must update internal params and restart animation."""
    widget = _make_widget(qapp)
    assert widget._fly_bounce is False
    assert widget._fly_loop_count == -1

    widget.set_flight_kwargs(fly_bounce=True, fly_loop_count=3, fly_duration_ms=3000)
    assert widget._fly_bounce is True
    assert widget._fly_loop_count == 3
    assert widget._fly_duration_ms == 3000
    assert widget._fly_count == 0  # reset
    assert widget._fly_direction == 1  # reset


def test_zigzag_initial_state(qapp):
    """zigzag_top_down 初始状态：row=0, direction=1"""
    widget = _make_widget(qapp, fly_path="zigzag_top_down")
    assert widget._zigzag_row == 0
    assert widget._zigzag_direction == 1


def test_zigzag_bottom_up_initial_state(qapp):
    """zigzag_bottom_up 初始状态：row=0, direction=1"""
    widget = _make_widget(qapp, fly_path="zigzag_bottom_up")
    assert widget._zigzag_row == 0
    assert widget._zigzag_direction == 1


def test_around_initial_state(qapp):
    """around 初始状态：step=0"""
    widget = _make_widget(qapp, fly_path="around")
    assert widget._around_step == 0


def test_zigzag_on_finished_advances_row(qapp):
    """zigzag_top_down _on_fly_finished 应推进 row 并反转方向"""
    widget = _make_widget(qapp, fly_path="zigzag_top_down")
    widget.fly_anim = MagicMock()
    widget.screen_h = 1080
    widget._zigzag_row = 0
    widget._zigzag_direction = 1
    widget._fly_count = 0
    widget._on_fly_finished()
    assert widget._zigzag_row == 1
    assert widget._zigzag_direction == -1


def test_around_on_finished_advances_step(qapp):
    """around _on_fly_finished 应推进 step"""
    widget = _make_widget(qapp, fly_path="around")
    widget.fly_anim = MagicMock()
    widget.screen_h = 1080
    widget._around_step = 0
    widget._fly_count = 0
    widget._on_fly_finished()
    assert widget._around_step == 1


def test_notification_queue_property_exposed(qapp):
    """FlightWidget 暴露 notification_queue 属性"""
    from message_flight.notification_queue import NotificationQueue
    widget = _make_widget(qapp)
    assert isinstance(widget.notification_queue, NotificationQueue)
    assert widget.notification_queue.is_empty()


def test_enqueue_first_notification_shows_immediately(qapp):
    """第一条 enqueue 应该立即显示（队列为空时打断当前动画）"""
    widget = _make_widget(qapp)
    with patch.object(widget, "show_notification") as mock_show:
        widget.enqueue_notification("first")
        mock_show.assert_called_once_with("first")
    assert widget.notification_queue.is_empty()


def test_enqueue_second_notification_does_not_show(qapp):
    """队列非空时 enqueue 不应立即显示（避免打断当前动画）"""
    widget = _make_widget(qapp)
    # 手动放入一个通知到队列（模拟"飞机正在飞第一个"）
    widget._notification_queue.enqueue("first-still-flying")
    with patch.object(widget, "show_notification") as mock_show:
        widget.enqueue_notification("second")
        # 队列非空，show_notification 不应被调用
        mock_show.assert_not_called()
    assert len(widget.notification_queue) == 2
    assert widget.notification_queue.peek() == "first-still-flying"


def test_on_fly_finished_drains_queue_sets_text(qapp):
    """_on_fly_finished 应消费队首并更新飞机文字（不重置动画位置）"""
    widget = _make_widget(qapp, fly_path="horizontal")
    widget.fly_anim = MagicMock()
    widget.plane.set_text = MagicMock()
    widget._fly_count = 0
    widget._fly_stopped = False
    widget._notification_queue.enqueue("queued-msg")
    # 调用 _on_fly_finished 会消费队首 + 继续水平路径
    widget._on_fly_finished()
    widget.plane.set_text.assert_called_once_with("queued-msg")
    assert widget.notification_queue.is_empty()


def test_enqueue_drops_oldest_when_full(qapp):
    """队列满时 enqueue 应丢弃最旧的消息"""
    widget = _make_widget(qapp, notification_queue_max_size=2)
    widget.fly_anim = MagicMock()
    # 第一条立即显示（show_notification 会清空队列）
    widget.enqueue_notification("a")
    # 模拟"飞机还在飞第一个"，手动入队一个
    widget._notification_queue.enqueue("b")
    widget._notification_queue.enqueue("c")  # 队列已满 [b, c]
    # 再次 enqueue：会丢弃队首 b
    dropped = widget._notification_queue.enqueue("d")
    assert dropped == "b"
    assert len(widget.notification_queue) == 2
    assert widget.notification_queue.peek() == "c"
