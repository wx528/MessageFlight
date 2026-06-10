import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import sys

import pytest
from PyQt6.QtWidgets import QApplication

from message_flight.config import AppConfig
from message_flight.plane_presets import get_preset
from message_flight.preset_editor import PresetEditorWindow, PresetPreviewWidget


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


def test_preview_widget_init_does_not_crash(qapp):
    preset = get_preset("airplane")
    params = preset.get_default_params()
    w = PresetPreviewWidget(preset, params)
    assert w._preset is preset
    assert w._params is params


def test_editor_window_init_does_not_crash(qapp):
    cfg = AppConfig()
    dlg = PresetEditorWindow(cfg)
    assert dlg._preset_combo.count() == 4


def test_editor_window_change_preset_updates_key(qapp):
    cfg = AppConfig()
    dlg = PresetEditorWindow(cfg)
    dlg._preset_combo.setCurrentIndex(2)
    assert dlg._preset_key == "ufo"
