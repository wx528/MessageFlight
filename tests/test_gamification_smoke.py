"""End-to-end smoke test for the gamification layer."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import sys
from datetime import datetime
from unittest.mock import MagicMock

import pytest
from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


@pytest.fixture
def fixed_noon(monkeypatch):
    class _FixedDT:
        @classmethod
        def now(cls):
            return datetime(2026, 1, 1, 12, 0)

    monkeypatch.setattr("message_flight.achievement_engine.datetime", _FixedDT)


def test_gamification_end_to_end(qapp, fixed_noon, tmp_path, monkeypatch):
    from message_flight.achievement_engine import AchievementEngine
    from message_flight.config import APP, ORG, AppConfig, load_config, save_config
    from message_flight.plane_presets import UNLOCKABLE_PRESETS, list_available_presets

    cfg = AppConfig(
        unlocked_presets=set(),
        achievement_progress={},
        distinct_notification_sources=set(),
        presets_used=set(),
        clicks=0,
        tts_count=0,
    )
    assert cfg.unlocked_presets == set()
    assert cfg.achievement_progress == {}

    engine = AchievementEngine(cfg)
    unlocked = MagicMock()
    milestone = MagicMock()
    engine.unlocked.connect(unlocked)
    engine.milestone.connect(milestone)

    engine.record_notification(source="WeChat")
    unlocked.assert_called_once_with("first_flight")
    assert "sleigh" in cfg.unlocked_presets

    available = list_available_presets(cfg.unlocked_presets)
    available_keys = [k for k, _, _ in available]
    assert "sleigh" in available_keys
    other_unlockables = set(UNLOCKABLE_PRESETS.keys()) - {"sleigh"}
    assert not any(k in available_keys for k in other_unlockables)

    for key in available_keys:
        engine.record_preset_used(key)
    milestone.assert_any_call("try_them_all")
    assert "try_them_all" in cfg.achievement_progress.get("_fired_milestones", set())

    for _ in range(49):
        engine.record_tts_speak()
    engine.record_tts_speak()
    milestone.assert_any_call("loud_mouth")
    assert cfg.tts_count == 50

    ini_dir = tmp_path / "qsettings"
    ini_dir.mkdir()
    monkeypatch.setenv("MESSAGEFLIGHT_CONFIG_DIR", str(ini_dir))
    settings = QSettings(QSettings.Format.IniFormat, QSettings.Scope.UserScope, ORG, APP)
    settings.clear()
    settings.sync()

    save_config(cfg, settings=settings)
    loaded = load_config(settings=settings)

    assert loaded.unlocked_presets == cfg.unlocked_presets
    assert loaded.achievement_progress == cfg.achievement_progress
    assert loaded.distinct_notification_sources == cfg.distinct_notification_sources
    assert loaded.presets_used == cfg.presets_used
    assert loaded.clicks == cfg.clicks
    assert loaded.tts_count == cfg.tts_count

    engine2 = AchievementEngine(loaded)
    re_unlocked = MagicMock()
    re_milestone = MagicMock()
    engine2.unlocked.connect(re_unlocked)
    engine2.milestone.connect(re_milestone)
    engine2.record_notification(source="Another")
    engine2.record_tts_speak()
    engine2.record_preset_used("airplane")
    re_unlocked.assert_not_called()
    re_milestone.assert_not_called()
