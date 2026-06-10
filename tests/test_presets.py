"""Tests for PlanePreset ABC and ParamDef dataclass (Task 01)."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from message_flight.plane_presets.base import ParamDef, PlanePreset


def test_param_def_stores_fields():
    p = ParamDef(name="radius", label="半径", type="int", default=30, min=10, max=100)
    assert p.name == "radius"
    assert p.label == "半径"
    assert p.type == "int"
    assert p.default == 30
    assert p.min == 10
    assert p.max == 100


def test_param_def_optional_fields_default_none():
    p = ParamDef(name="color", label="颜色", type="color", default="#FF0000")
    assert p.min is None
    assert p.max is None
    assert p.step is None


def test_plane_preset_is_abstract():
    with pytest.raises(TypeError):
        PlanePreset()


from message_flight.plane_presets.airplane import AirplanePreset, AirplaneParameters


def test_airplane_preset_has_name_and_icon():
    p = AirplanePreset()
    assert p.name == "飞机"
    assert p.icon == "✈️"


def test_airplane_preset_default_params():
    p = AirplanePreset()
    params = p.get_default_params()
    assert isinstance(params, AirplaneParameters)
    assert params.plane_color == "#FF69B4"
    assert params.wing_color == "#FF1493"


def test_airplane_preset_get_parameters():
    p = AirplanePreset()
    param_defs = p.get_parameters()
    assert len(param_defs) >= 9
    names = [pd.name for pd in param_defs]
    assert "plane_color" in names
    assert "wing_color" in names


def test_airplane_draw_does_not_crash():
    from unittest.mock import MagicMock
    p = AirplanePreset()
    params = p.get_default_params()
    painter = MagicMock()
    p.draw(painter, params)
    assert painter.drawEllipse.call_count >= 3


def test_airplane_parameters_is_dataclass():
    import dataclasses
    assert dataclasses.is_dataclass(AirplaneParameters)


from message_flight.plane_presets import get_preset, list_presets


def test_get_preset_returns_airplane():
    p = get_preset("airplane")
    assert isinstance(p, AirplanePreset)


def test_get_preset_unknown_returns_airplane_fallback():
    p = get_preset("nonexistent")
    assert isinstance(p, AirplanePreset)


def test_list_presets_includes_airplane():
    keys = [k for k, _, _ in list_presets()]
    assert "airplane" in keys


from message_flight.plane_presets.rocket import RocketPreset, RocketParameters


def test_rocket_preset_has_name_and_icon():
    p = RocketPreset()
    assert p.name == "火箭"
    assert p.icon == "🚀"


def test_rocket_preset_default_params():
    p = RocketPreset()
    params = p.get_default_params()
    assert isinstance(params, RocketParameters)
    assert params.body_length == 60


def test_rocket_draw_does_not_crash():
    from unittest.mock import MagicMock
    p = RocketPreset()
    painter = MagicMock()
    p.draw(painter, p.get_default_params())
    assert painter.drawPath.call_count >= 1 or painter.drawRect.call_count >= 1


from message_flight.plane_presets.ufo import UFOPreset, UFOParameters


def test_ufo_preset_has_name_and_icon():
    p = UFOPreset()
    assert p.name == "UFO"
    assert p.icon == "🛸"


def test_ufo_preset_default_params():
    p = UFOPreset()
    params = p.get_default_params()
    assert isinstance(params, UFOParameters)
    assert params.disc_radius == 30


def test_ufo_draw_does_not_crash():
    from unittest.mock import MagicMock
    p = UFOPreset()
    painter = MagicMock()
    p.draw(painter, p.get_default_params())
    assert painter.drawEllipse.call_count >= 1


from message_flight.plane_presets.bird import BirdPreset, BirdParameters


def test_bird_preset_has_name_and_icon():
    p = BirdPreset()
    assert p.name == "小鸟"
    assert p.icon == "🐦"


def test_bird_preset_default_params():
    p = BirdPreset()
    params = p.get_default_params()
    assert isinstance(params, BirdParameters)


def test_bird_draw_does_not_crash():
    from unittest.mock import MagicMock
    p = BirdPreset()
    painter = MagicMock()
    p.draw(painter, p.get_default_params())
    assert painter.drawPath.call_count >= 1
