"""Tests for PlaneBanner component decomposition (Task 03) and color customization (Task 02)."""
import inspect
from unittest.mock import MagicMock, patch

from PyQt6.QtGui import QColor

from message_flight.plane_banner import PlaneBanner


def test_fuselage_method_exists():
    """_draw_fuselage 方法必须存在"""
    assert hasattr(PlaneBanner, "_draw_fuselage")
    assert callable(getattr(PlaneBanner, "_draw_fuselage"))


def test_wings_method_exists():
    """_draw_wings 方法必须存在"""
    assert hasattr(PlaneBanner, "_draw_wings")
    assert callable(getattr(PlaneBanner, "_draw_wings"))


def test_thruster_method_exists():
    """_draw_thruster 方法必须存在（新增）"""
    assert hasattr(PlaneBanner, "_draw_thruster")
    assert callable(getattr(PlaneBanner, "_draw_thruster"))


def test_thruster_accepts_intensity():
    """_draw_thruster 必须接受 intensity 参数"""
    sig = inspect.signature(PlaneBanner._draw_thruster)
    assert "intensity" in sig.parameters


def test_thruster_calls_painter_at_least_3_times():
    """_draw_thruster 应至少调用 painter.drawEllipse 3 次（3 层火焰）"""
    with patch("PyQt6.QtWidgets.QWidget.__init__"), \
         patch.object(PlaneBanner, "setFixedSize"):
        banner = PlaneBanner()
    mock_painter = MagicMock()
    banner._draw_thruster(mock_painter, intensity=1.0)
    assert mock_painter.drawEllipse.call_count >= 3


def test_thruster_intensity_scales_outer_width():
    """intensity=2.0 时外层椭圆宽度应为 28（捕获"忘记乘 intensity"bug）"""
    with patch("PyQt6.QtWidgets.QWidget.__init__"), \
         patch.object(PlaneBanner, "setFixedSize"):
        banner = PlaneBanner()
    mock_painter = MagicMock()
    banner._draw_thruster(mock_painter, intensity=2.0)
    # call_args_list[0] 是第一次 drawEllipse 调用（外层，最大）
    outer_call = mock_painter.drawEllipse.call_args_list[0]
    _, _, w, h = outer_call.args  # (x, y, w, h)
    assert w == 28  # 14 * 2.0 = 28


# ---------------------------------------------------------------------------
# Task 02: color customization tests
# ---------------------------------------------------------------------------


def test_default_colors_when_no_args():
    """不传任何参数时颜色与旧硬编码值一致（向后兼容）"""
    with patch("PyQt6.QtWidgets.QWidget.__init__"), \
         patch.object(PlaneBanner, "setFixedSize"):
        banner = PlaneBanner()
    assert banner._plane_color.name().lower() == "#ff69b4"
    assert banner._banner_color.name().lower() == "#ffb6c1"
    assert banner._text_color.name().lower() == "#ffffff"


def test_custom_plane_and_wing_colors():
    """传入 plane_color 和 wing_color 后实例属性被正确设置"""
    with patch("PyQt6.QtWidgets.QWidget.__init__"), \
         patch.object(PlaneBanner, "setFixedSize"):
        banner = PlaneBanner(plane_color="#00BFFF", wing_color="#1E90FF")
    assert banner._plane_color.name().lower() == "#00bfff"
    assert banner._wing_color.name().lower() == "#1e90ff"


def test_custom_thruster_colors():
    """推进器 3 层颜色都应能自定义"""
    with patch("PyQt6.QtWidgets.QWidget.__init__"), \
         patch.object(PlaneBanner, "setFixedSize"):
        banner = PlaneBanner(
            thruster_outer_color="#FF0000",
            thruster_middle_color="#00FF00",
            thruster_inner_color="#0000FF",
        )
    assert banner._thruster_outer_color.name().lower() == "#ff0000"
    assert banner._thruster_middle_color.name().lower() == "#00ff00"
    assert banner._thruster_inner_color.name().lower() == "#0000ff"


def test_qcolor_normalization():
    """QColor 标准化：传大写 hex 应被 QColor 转小写"""
    with patch("PyQt6.QtWidgets.QWidget.__init__"), \
         patch.object(PlaneBanner, "setFixedSize"):
        banner = PlaneBanner(plane_color="#ABCDEF")
    # QColor 标准化为小写
    assert banner._plane_color.name().lower() == "#abcdef"

