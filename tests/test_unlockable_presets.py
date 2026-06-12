"""Tests for the 5 unlockable PlanePreset subclasses."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import sys

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


@pytest.mark.parametrize("preset_key", [
    "sleigh",
    "duck",
    "rainbow_rocket",
    "gold_ufo",
    pytest.param("pixel_bird", marks=pytest.mark.xfail(reason="implemented in Task 11")),
])
def test_unlockable_preset_is_registered(preset_key):
    from message_flight.plane_presets import UNLOCKABLE_PRESETS
    assert preset_key in UNLOCKABLE_PRESETS
    assert UNLOCKABLE_PRESETS[preset_key].__name__.endswith("Preset")


@pytest.mark.parametrize("preset_key", [
    "sleigh",
    "duck",
    "rainbow_rocket",
    "gold_ufo",
    pytest.param("pixel_bird", marks=pytest.mark.xfail(reason="implemented in Task 11")),
])
def test_unlockable_preset_can_be_instantiated(preset_key):
    from message_flight.plane_presets import UNLOCKABLE_PRESETS
    p = UNLOCKABLE_PRESETS[preset_key]()
    assert p.name
    assert p.icon
    assert p.system_prompt


@pytest.mark.parametrize("preset_key", [
    "sleigh",
    "duck",
    "rainbow_rocket",
    "gold_ufo",
    pytest.param("pixel_bird", marks=pytest.mark.xfail(reason="implemented in Task 11")),
])
def test_unlockable_preset_draws_without_raising(qapp, preset_key):
    from message_flight.plane_presets import UNLOCKABLE_PRESETS
    p = UNLOCKABLE_PRESETS[preset_key]()
    params = p.get_default_params()
    img = QImage(120, 120, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    painter = QPainter(img)
    try:
        p.draw(painter, params)
    finally:
        painter.end()
