"""Tests for the SettingsDialog (Task 05) + flight mode row (Task 06)."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import sys

import pytest
from PyQt6.QtWidgets import QApplication, QDialog, QDialogButtonBox, QPushButton

from message_flight.config import (
    DEFAULT_THEME,
    FLIGHT_MODE_NAMES,
    FLIGHT_MODES,
    THEMES,
    AppConfig,
)
from message_flight.settings_dialog import SettingsDialog


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


def test_dialog_init_with_default_config_does_not_crash(qapp):
    """Constructing the dialog with a default AppConfig must not raise."""
    cfg = AppConfig(theme_name=DEFAULT_THEME, colors=dict(THEMES[DEFAULT_THEME]))
    dlg = SettingsDialog(cfg)
    # The dialog should expose exactly 9 editable fields
    assert len(dlg._line_edits) == 9
    # Each QLineEdit should hold the default color
    for key, value in THEMES[DEFAULT_THEME].items():
        assert dlg._line_edits[key].text() == value
    # The dialog must remain a QDialog subclass
    assert isinstance(dlg, QDialog)
    # OK button should be enabled (all 9 fields are valid hex)
    ok_btn = dlg._button_box.button(QDialogButtonBox.StandardButton.Ok)
    assert ok_btn is not None and ok_btn.isEnabled()


def test_click_preset_fills_all_nine_lineedits(qapp):
    """Clicking the '复古绿' preset must fill all 9 QLineEdits with the retro palette."""
    cfg = AppConfig(theme_name=DEFAULT_THEME, colors=dict(THEMES[DEFAULT_THEME]))
    dlg = SettingsDialog(cfg)
    # Find the preset button by its visible text
    target = None
    for btn in dlg.findChildren(QPushButton):
        if btn.text() == "复古绿":
            target = btn
            break
    assert target is not None, "preset button '复古绿' not found"
    target.click()

    retro = THEMES["retro"]
    for key, expected in retro.items():
        actual = dlg._line_edits[key].text()
        assert actual == expected, f"{key}: expected {expected!r}, got {actual!r}"

    # Dialog must NOT have closed just because a preset was clicked
    assert dlg.isVisible() is False or dlg.result() != QDialog.DialogCode.Accepted


def test_get_result_after_ok_returns_new_config(qapp):
    """After editing one field and accepting, get_result must reflect the edit."""
    cfg = AppConfig(theme_name=DEFAULT_THEME, colors=dict(THEMES[DEFAULT_THEME]))
    dlg = SettingsDialog(cfg)
    # Change the plane color
    new_value = "#102030"
    dlg._line_edits["plane_color"].setText(new_value)
    # Simulate the user pressing OK by calling accept() directly
    dlg.accept()
    assert dlg.result() == QDialog.DialogCode.Accepted

    result = dlg.get_result()
    assert result.theme_name == DEFAULT_THEME
    # The new plane color must be present (normalized to lowercase via QColor.name)
    assert result.colors["plane_color"].lower() == new_value.lower()
    # The other colors must remain populated (and equal the original defaults,
    # normalized to lowercase to match QColor's canonical form)
    for key, value in THEMES[DEFAULT_THEME].items():
        if key == "plane_color":
            continue
        assert result.colors[key].lower() == value.lower()


def test_click_flight_mode_button_updates_internal_state(qapp):
    """Clicking the '胡闹' flight-mode button must update _current_flight_mode + _current_flight_kwargs (but NOT colors)."""
    cfg = AppConfig(theme_name=DEFAULT_THEME, colors=dict(THEMES[DEFAULT_THEME]))
    dlg = SettingsDialog(cfg)
    # Sanity: the dialog exposes exactly 3 flight-mode buttons, one per mode name
    assert set(dlg._flight_mode_buttons.keys()) == set(FLIGHT_MODE_NAMES)
    # Find the '胡闹' button via the public attribute (mirrors the _PRESETS pattern)
    btn = dlg._flight_mode_buttons["胡闹"]
    assert isinstance(btn, QPushButton)
    btn.click()

    cyber_kwargs = FLIGHT_MODES["胡闹"]
    # 1. Internal flight mode + kwargs must reflect the click
    assert dlg._current_flight_mode == "胡闹"
    assert dlg._current_flight_kwargs["fly_bounce"] is True
    assert dlg._current_flight_kwargs["fly_loop_count"] == -1
    # 2. The dialog must NOT have closed
    assert dlg.result() != QDialog.DialogCode.Accepted
    # 3. get_result() must surface the new flight mode + kwargs
    result = dlg.get_result()
    assert result.flight_mode == "胡闹"
    assert result.flight_kwargs == cyber_kwargs


def test_flight_mode_does_not_change_colors(qapp):
    """Clicking a flight-mode button must NOT alter the 9 color QLineEdits."""
    cfg = AppConfig(theme_name=DEFAULT_THEME, colors=dict(THEMES[DEFAULT_THEME]))
    dlg = SettingsDialog(cfg)
    initial_plane_color = dlg._line_edits["plane_color"].text()
    dlg._flight_mode_buttons["胡闹"].click()
    assert dlg._line_edits["plane_color"].text() == initial_plane_color


def test_settings_dialog_exposes_language_combo(qapp):
    cfg = AppConfig(language="en")
    dlg = SettingsDialog(cfg)

    assert dlg._language_combo.currentData() == "en"
    labels = [dlg._language_combo.itemText(i) for i in range(dlg._language_combo.count())]
    assert "日本語" in labels
    assert "한국어" in labels

    dlg._language_combo.setCurrentIndex(dlg._language_combo.findData("ko"))
    result = dlg.get_result()
    assert result.language == "ko"


def test_settings_dialog_uses_selected_language_labels(qapp):
    cfg = AppConfig(language="ja")
    dlg = SettingsDialog(cfg)
    assert dlg.windowTitle() == "MessageFlight 設定"


def test_settings_dialog_returns_minimax_config(qapp):
    """SettingsDialog with minimax provider must return correct config."""
    cfg = AppConfig(tts_provider="sapi")
    dlg = SettingsDialog(cfg)
    # Switch to minimax
    dlg._provider_combo.setCurrentText("minimax")
    dlg._api_key_edit.setText("my-api-key")

    result = dlg.get_result()
    assert result.tts_provider == "minimax"
    assert result.minimax_subscription_key == "my-api-key"
