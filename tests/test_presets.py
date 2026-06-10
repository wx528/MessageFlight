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
