"""Tests for message_flight.notification_worker module."""
from message_flight.notification_worker import NotificationWorker


def test_worker_init_state():
    w = NotificationWorker()
    try:
        assert w._initialized is False
        assert w._running is True
        assert w._seen_ids == set()
    finally:
        w._running = False
        w.quit()
        w.wait(1000)
