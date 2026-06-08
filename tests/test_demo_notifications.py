"""Tests for message_flight.demo_notifications module."""
from message_flight.demo_notifications import NOTIFICATIONS


def test_notifications_non_empty_list():
    assert isinstance(NOTIFICATIONS, list)
    assert len(NOTIFICATIONS) > 0


def test_notifications_all_strings():
    for n in NOTIFICATIONS:
        assert isinstance(n, str)
        assert len(n) > 0
