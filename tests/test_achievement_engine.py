"""Tests for AchievementEngine."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import sys
from datetime import datetime
from unittest.mock import MagicMock

import pytest
from PyQt6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


@pytest.fixture
def fixed_noon(monkeypatch):
    """Fix datetime.now() to 12:00 so time-of-day triggers don't fire
    unexpectedly in tests that only want to exercise count/set triggers."""
    class _FixedDT:
        @classmethod
        def now(cls):
            return datetime(2026, 1, 1, 12, 0)
    monkeypatch.setattr("message_flight.achievement_engine.datetime", _FixedDT)


def test_engine_emits_unlocked_on_first_notification(qapp, fixed_noon):
    from message_flight.achievement_engine import AchievementEngine
    from message_flight.config import GamificationState

    state = GamificationState()
    engine = AchievementEngine(state)
    fired = MagicMock()
    engine.unlocked.connect(fired)

    engine.record_notification(source="WeChat")

    fired.assert_called_once_with("first_flight")
    assert "sleigh" in state.unlocked_presets


def test_engine_does_not_double_emit_unlocked(qapp, fixed_noon):
    from message_flight.achievement_engine import AchievementEngine
    from message_flight.config import GamificationState

    state = GamificationState()
    engine = AchievementEngine(state)
    fired = MagicMock()
    engine.unlocked.connect(fired)

    engine.record_notification(source="WeChat")
    engine.record_notification(source="Outlook")
    engine.record_notification(source="Slack")

    # first_flight fires once, not on every subsequent call
    assert fired.call_count == 1
    assert fired.call_args_list[0].args == ("first_flight",)


def test_engine_centurion_fires_at_100(qapp, fixed_noon):
    from message_flight.achievement_engine import AchievementEngine
    from message_flight.config import GamificationState

    state = GamificationState()
    engine = AchievementEngine(state)
    fired = MagicMock()
    engine.unlocked.connect(fired)

    for _ in range(99):
        engine.record_notification(source="app")
    assert fired.call_count == 1  # only first_flight so far

    engine.record_notification(source="app100")
    ids = [c.args[0] for c in fired.call_args_list]
    assert "centurion" in ids


def test_engine_social_butterfly_fires_at_5_distinct(qapp, fixed_noon):
    from message_flight.achievement_engine import AchievementEngine
    from message_flight.config import GamificationState

    state = GamificationState()
    engine = AchievementEngine(state)
    fired = MagicMock()
    engine.unlocked.connect(fired)

    for src in ("A", "B", "C", "D", "E", "E", "E"):
        engine.record_notification(source=src)

    ids = [c.args[0] for c in fired.call_args_list]
    assert "social_butterfly" in ids


def test_engine_milestone_does_not_refire_on_new_engine(qapp, fixed_noon):
    """A milestone fired in one engine instance must not refire after restart."""
    from message_flight.achievement_engine import AchievementEngine
    from message_flight.config import GamificationState

    state = GamificationState()
    engine1 = AchievementEngine(state)
    fired1 = MagicMock()
    engine1.milestone.connect(fired1)

    for _ in range(10):
        engine1.record_plane_click()

    fired1.assert_called_once_with("clicker")
    assert "clicker" in state.achievement_progress.get("_fired_milestones", set())

    # Simulate process restart: create a new engine with the same state
    engine2 = AchievementEngine(state)
    fired2 = MagicMock()
    engine2.milestone.connect(fired2)
    engine2.record_plane_click()

    # Should not fire again
    fired2.assert_not_called()


def test_engine_night_owl_fires_when_hour_in_window(qapp, monkeypatch):
    from datetime import datetime

    from message_flight.achievement_engine import AchievementEngine
    from message_flight.config import GamificationState

    state = GamificationState()
    engine = AchievementEngine(state)
    fired = MagicMock()
    engine.unlocked.connect(fired)

    class _FixedDT:
        @classmethod
        def now(cls):
            return datetime(2026, 1, 1, 2, 30)
    monkeypatch.setattr("message_flight.achievement_engine.datetime", _FixedDT)

    engine.record_notification(source="WeChat")
    ids = [c.args[0] for c in fired.call_args_list]
    assert "night_owl" in ids
    assert "gold_ufo" in state.unlocked_presets


def test_engine_early_bird_fires_when_hour_in_window(qapp, monkeypatch):
    from datetime import datetime

    from message_flight.achievement_engine import AchievementEngine
    from message_flight.config import GamificationState

    state = GamificationState()
    engine = AchievementEngine(state)
    fired = MagicMock()
    engine.unlocked.connect(fired)

    class _FixedDT:
        @classmethod
        def now(cls):
            return datetime(2026, 1, 1, 6, 15)
    monkeypatch.setattr("message_flight.achievement_engine.datetime", _FixedDT)

    engine.record_notification(source="WeChat")
    ids = [c.args[0] for c in fired.call_args_list]
    assert "early_bird" in ids
    assert "pixel_bird" in state.unlocked_presets


def test_clicker_fires_after_enough_clicks(qapp, fixed_noon):
    from message_flight.achievement_engine import AchievementEngine
    from message_flight.config import GamificationState

    state = GamificationState()
    engine = AchievementEngine(state)
    fired = MagicMock()
    engine.milestone.connect(fired)

    for _ in range(9):
        engine.record_plane_click()
    fired.assert_not_called()

    engine.record_plane_click()
    fired.assert_called_once_with("clicker")

    for _ in range(5):
        engine.record_plane_click()
    assert fired.call_count == 1


def test_loud_mouth_fires_after_enough_messages(qapp, fixed_noon):
    from message_flight.achievement_engine import AchievementEngine
    from message_flight.config import GamificationState

    state = GamificationState()
    engine = AchievementEngine(state)
    fired = MagicMock()
    engine.milestone.connect(fired)

    for _ in range(49):
        engine.record_tts_speak()
    fired.assert_not_called()

    engine.record_tts_speak()
    fired.assert_called_once_with("loud_mouth")

    for _ in range(10):
        engine.record_tts_speak()
    assert fired.call_count == 1


def test_try_them_all_fires_after_all_available_presets(qapp, fixed_noon):
    from message_flight.achievement_engine import AchievementEngine
    from message_flight.config import GamificationState

    state = GamificationState()
    engine = AchievementEngine(state)
    fired = MagicMock()
    engine.milestone.connect(fired)

    for key in ("airplane", "rocket", "ufo"):
        engine.record_preset_used(key)
    fired.assert_not_called()

    engine.record_preset_used("bird")
    fired.assert_called_once_with("try_them_all")

    engine.record_preset_used("airplane")
    engine.record_preset_used("sleigh")
    assert fired.call_count == 1
