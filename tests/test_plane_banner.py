"""Tests for PlaneBanner component decomposition (Task 03)."""
import inspect
from unittest.mock import MagicMock, patch

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

