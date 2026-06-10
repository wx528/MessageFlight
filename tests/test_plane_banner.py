"""Tests for PlaneBanner color customization (Task 02) and preset delegation (Task 05)."""
from unittest.mock import MagicMock, patch

from PyQt6.QtGui import QColor

from message_flight.plane_banner import PlaneBanner

# ---------------------------------------------------------------------------
# Task 02: color customization tests
# ---------------------------------------------------------------------------


def test_default_colors_when_no_args():
    """不传任何参数时颜色与旧硬编码值一致（向后兼容）"""
    with patch("PyQt6.QtWidgets.QWidget.__init__"), \
         patch.object(PlaneBanner, "setFixedSize"):
        banner = PlaneBanner()
    assert banner._params.plane_color.lower() == "#ff69b4"
    assert banner._params.banner_color.lower() == "#ffb6c1"
    assert banner._text_color.name().lower() == "#ffffff"


def test_custom_plane_and_wing_colors():
    """传入 plane_color 和 wing_color 后实例属性被正确设置"""
    with patch("PyQt6.QtWidgets.QWidget.__init__"), \
         patch.object(PlaneBanner, "setFixedSize"):
        banner = PlaneBanner(plane_color="#00BFFF", wing_color="#1E90FF")
    assert banner._params.plane_color.lower() == "#00bfff"
    assert banner._params.wing_color.lower() == "#1e90ff"


def test_custom_thruster_colors():
    """推进器 3 层颜色都应能自定义"""
    with patch("PyQt6.QtWidgets.QWidget.__init__"), \
         patch.object(PlaneBanner, "setFixedSize"):
        banner = PlaneBanner(
            thruster_outer_color="#FF0000",
            thruster_middle_color="#00FF00",
            thruster_inner_color="#0000FF",
        )
    assert banner._params.thruster_outer_color.lower() == "#ff0000"
    assert banner._params.thruster_middle_color.lower() == "#00ff00"
    assert banner._params.thruster_inner_color.lower() == "#0000ff"


def test_qcolor_normalization():
    """QColor 标准化：传大写 hex 应被 QColor 转小写"""
    with patch("PyQt6.QtWidgets.QWidget.__init__"), \
         patch.object(PlaneBanner, "setFixedSize"):
        banner = PlaneBanner(plane_color="#ABCDEF")
    # 颜色存储在 _params 中，保持原样（字符串）
    assert banner._params.plane_color.lower() == "#abcdef"


def test_all_color_attributes_initialized():
    """All 9 color params should be stored as valid QColor instances."""
    with patch("PyQt6.QtWidgets.QWidget.__init__"), \
         patch.object(PlaneBanner, "setFixedSize"):
        banner = PlaneBanner()
    # 8 colors from _params + text_color
    params_colors = [
        "plane_color", "wing_color", "accent_color", "decor_color",
        "banner_color", "thruster_outer_color", "thruster_middle_color",
        "thruster_inner_color",
    ]
    for name in params_colors:
        value = getattr(banner._params, name)
        assert isinstance(value, str), f"{name} is not a str"
        assert QColor(value).isValid(), f"{name} is not a valid color"
    assert isinstance(banner._text_color, QColor)
    assert banner._text_color.isValid()


# ---------------------------------------------------------------------------
# Task 05: live color update API
# ---------------------------------------------------------------------------


def test_update_colors_replaces_all_nine_attributes():
    """update_colors() must replace all 8 _params colors + _text_color and trigger repaint."""
    with patch("PyQt6.QtWidgets.QWidget.__init__"), \
         patch.object(PlaneBanner, "setFixedSize"):
        banner = PlaneBanner()
    # Replace the inherited C++ update() with a MagicMock so it can be called
    # without a real Qt event loop, and so we can assert it was invoked.
    banner.update = MagicMock()
    banner.update_colors(
        plane_color="#111111",
        wing_color="#222222",
        accent_color="#333333",
        decor_color="#444444",
        banner_color="#555555",
        text_color="#666666",
        thruster_outer_color="#777777",
        thruster_middle_color="#888888",
        thruster_inner_color="#999999",
    )
    assert banner._params.plane_color.lower() == "#111111"
    assert banner._params.wing_color.lower() == "#222222"
    assert banner._params.accent_color.lower() == "#333333"
    assert banner._params.decor_color.lower() == "#444444"
    assert banner._params.banner_color.lower() == "#555555"
    assert banner._text_color.name().lower() == "#666666"
    assert banner._params.thruster_outer_color.lower() == "#777777"
    assert banner._params.thruster_middle_color.lower() == "#888888"
    assert banner._params.thruster_inner_color.lower() == "#999999"
    # Repaint should be requested exactly once (coalesced).
    banner.update.assert_called_once()


# ---------------------------------------------------------------------------
# Task 05: preset delegation
# ---------------------------------------------------------------------------


def test_plane_banner_uses_airplane_preset_by_default():
    from message_flight.plane_presets import AirplanePreset
    from message_flight.plane_presets.airplane import AirplaneParameters
    with patch("PyQt6.QtWidgets.QWidget.__init__"), \
         patch.object(PlaneBanner, "setFixedSize"):
        banner = PlaneBanner()
    assert isinstance(banner._preset, AirplanePreset)
    assert isinstance(banner._params, AirplaneParameters)


def test_plane_banner_update_colors_sets_preset_params():
    with patch("PyQt6.QtWidgets.QWidget.__init__"), \
         patch.object(PlaneBanner, "setFixedSize"):
        banner = PlaneBanner()
    banner.update = MagicMock()
    banner.update_colors(plane_color="#ABCDEF", wing_color="#123456")
    assert banner._params.plane_color == "#ABCDEF"
    assert banner._params.wing_color == "#123456"


def test_update_colors_does_not_set_text_color_on_preset_params():
    """text_color is banner-only (not a vehicle color), so it must not
    leak onto the AirplaneParameters dataclass via phantom attribute.
    Without the hasattr guard, dataclasses.asdict() in the editor
    would silently drop the change because text_color is not a declared field.
    """
    from dataclasses import asdict
    with patch("PyQt6.QtWidgets.QWidget.__init__"), \
         patch.object(PlaneBanner, "setFixedSize"):
        banner = PlaneBanner()
    banner.update = MagicMock()
    banner.update_colors(text_color="#AABBCC")
    assert banner._text_color.name().lower() == "#aabbcc"
    # AirplaneParameters now has text_color field; update_colors should
    # update it like any other color parameter.
    assert banner._params.text_color == "#AABBCC"
