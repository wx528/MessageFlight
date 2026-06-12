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
