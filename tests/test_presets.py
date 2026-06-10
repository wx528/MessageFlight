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
    p.draw(painter, params, facing=1)
    assert painter.drawEllipse.call_count >= 3


def test_airplane_parameters_is_dataclass():
    import dataclasses
    assert dataclasses.is_dataclass(AirplaneParameters)
