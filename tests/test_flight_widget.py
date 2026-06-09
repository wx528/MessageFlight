"""Tests for FlightWidget customization (Task 01)."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import sys
import pytest
from unittest.mock import patch, MagicMock

from PyQt6.QtWidgets import QApplication


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
    fake_geometry = type("G", (), {"width": lambda self: 1920, "height": lambda self: 1080})()
    fake_screen = type("S", (), {"geometry": lambda self: fake_geometry})()
    with patch("PyQt6.QtWidgets.QApplication.primaryScreen", return_value=fake_screen), \
         patch.object(__import__("message_flight.flight_widget", fromlist=["FlightWidget"]).FlightWidget,
                      "_setup_float_animation"), \
         patch.object(__import__("message_flight.flight_widget", fromlist=["FlightWidget"]).FlightWidget,
                      "_setup_fly_animation"):
        from message_flight.flight_widget import FlightWidget
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


def test_fly_path_zigzag_raises_not_implemented(qapp):
    """zigzag 路径必须 raise NotImplementedError"""
    with pytest.raises(NotImplementedError, match="zigzag"):
        _make_widget(qapp, fly_path="zigzag_top_down")
    with pytest.raises(NotImplementedError, match="zigzag"):
        _make_widget(qapp, fly_path="zigzag_bottom_up")


def test_fly_path_around_raises_not_implemented(qapp):
    """around 路径必须 raise NotImplementedError"""
    with pytest.raises(NotImplementedError, match="around"):
        _make_widget(qapp, fly_path="around")


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
    base = int(1000 * 0.5)  # 500
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
    assert widget.plane._plane_color.name().lower() == "#00ff00"
    assert widget.plane._wing_color.name().lower() == "#111111"
    assert widget.plane._thruster_inner_color.name().lower() == "#888888"
