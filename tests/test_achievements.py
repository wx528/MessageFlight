"""Tests for the Achievement registry and TriggerSpec types."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_counter_trigger_fires_at_target():
    """CounterTrigger(target=N) fires when count >= N."""
    from message_flight.achievements import CounterTrigger
    t = CounterTrigger(target=10)
    assert t.evaluate({"count": 5}) is False
    assert t.evaluate({"count": 10}) is True
    assert t.evaluate({"count": 11}) is True


def test_distinct_set_trigger_fires_at_target():
    from message_flight.achievements import DistinctSetTrigger
    t = DistinctSetTrigger(target=3)
    assert t.evaluate({"set": {"a"}}) is False
    assert t.evaluate({"set": {"a", "b", "c"}}) is True


def test_time_of_day_trigger_inclusive_bounds():
    from message_flight.achievements import TimeOfDayTrigger
    t = TimeOfDayTrigger(start_hour=0, end_hour=5)
    assert t.evaluate({"hour": 0}) is True
    assert t.evaluate({"hour": 4}) is True
    assert t.evaluate({"hour": 5}) is False  # end is exclusive
    assert t.evaluate({"hour": 23}) is False


def test_used_all_presets_trigger():
    from message_flight.achievements import UsedAllPresetsTrigger
    t = UsedAllPresetsTrigger(required={"airplane", "rocket", "ufo", "bird"})
    assert t.evaluate({"presets_used": {"airplane"}}) is False
    assert t.evaluate({"presets_used": {"airplane", "rocket", "ufo", "bird"}}) is True
    assert t.evaluate({"presets_used": {"airplane", "rocket", "ufo", "bird", "sleigh"}}) is True


def test_achievement_dataclass_fields():
    """Achievement is a frozen dataclass with the spec'd fields."""
    from message_flight.achievements import Achievement, CounterTrigger
    a = Achievement(
        id="first_flight",
        name_i18n_key="achievement.first_flight.name",
        description_i18n_key="achievement.first_flight.desc",
        trigger=CounterTrigger(target=1),
        unlock_preset_key="sleigh",
        icon="🎅",
    )
    assert a.id == "first_flight"
    assert a.unlock_preset_key == "sleigh"
    # Milestone achievements have unlock_preset_key = None
    b = Achievement(
        id="clicker",
        name_i18n_key="achievement.clicker.name",
        description_i18n_key="achievement.clicker.desc",
        trigger=CounterTrigger(target=10),
        unlock_preset_key=None,
        icon="🏆",
    )
    assert b.unlock_preset_key is None


def test_registry_has_exactly_eight_entries():
    from message_flight.achievements import ACHIEVEMENTS
    assert len(ACHIEVEMENTS) == 8


def test_registry_no_duplicate_ids():
    from message_flight.achievements import ACHIEVEMENTS
    ids = [a.id for a in ACHIEVEMENTS]
    assert len(ids) == len(set(ids))


def test_registry_five_with_preset_three_milestones():
    from message_flight.achievements import ACHIEVEMENTS
    with_preset = [a for a in ACHIEVEMENTS if a.unlock_preset_key]
    milestones = [a for a in ACHIEVEMENTS if a.unlock_preset_key is None]
    assert len(with_preset) == 5
    assert len(milestones) == 3


def test_registry_all_i18n_keys_resolve():
    from message_flight.achievements import ACHIEVEMENTS
    from message_flight.i18n import tr
    for a in ACHIEVEMENTS:
        assert tr(a.name_i18n_key, "en"), f"missing en: {a.name_i18n_key}"
        assert tr(a.name_i18n_key, "zh"), f"missing zh: {a.name_i18n_key}"
        assert tr(a.description_i18n_key, "en"), f"missing en: {a.description_i18n_key}"
        assert tr(a.description_i18n_key, "zh"), f"missing zh: {a.description_i18n_key}"


def test_registry_unlock_presets_are_known():
    """unlock_preset_key must refer to a preset that exists in UNLOCKABLE_PRESETS."""
    from message_flight.achievements import ACHIEVEMENTS
    from message_flight.plane_presets import UNLOCKABLE_PRESETS
    valid = set(UNLOCKABLE_PRESETS.keys())
    for a in ACHIEVEMENTS:
        if a.unlock_preset_key is None:
            continue
        assert a.unlock_preset_key in valid, f"unknown preset: {a.unlock_preset_key}"
