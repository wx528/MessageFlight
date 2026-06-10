"""Tests for message_flight.notification_worker module."""
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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


@pytest.mark.skipif(sys.platform != "win32", reason="winsdk only available on Windows")
def test_poll_extracts_text_elements():
    """Test that _poll correctly extracts text from notification bindings."""
    worker = NotificationWorker()

    mock_notification = MagicMock()
    mock_notification.id = 1
    mock_notification.app_info.display_info.display_name = "TestApp"

    mock_text_element = MagicMock()
    mock_text_element.text = "Test message"

    class FakeIterator:
        def __init__(self, items):
            self._items = items
            self._index = 0

        @property
        def has_current(self):
            return self._index < len(self._items)

        @property
        def current(self):
            return self._items[self._index]

        def move_next(self):
            self._index += 1
            return self.has_current

        def __iter__(self):
            return self

        def __next__(self):
            if not self.has_current:
                raise StopIteration
            item = self.current
            self.move_next()
            return item

    class FakeTextElements:
        def __init__(self, items):
            self._items = items

        def __iter__(self):
            return FakeIterator(self._items)

    fake_texts = FakeTextElements([mock_text_element])

    mock_binding = MagicMock()
    mock_binding.get_text_elements.return_value = fake_texts

    mock_visual = MagicMock()
    mock_visual.get_binding.return_value = mock_binding

    mock_notification.notification.visual = mock_visual

    with patch("message_flight.notification_worker.UserNotificationListener") as mock_listener_cls:
        mock_listener = MagicMock()
        mock_listener.get_access_status.return_value = 1
        mock_listener.get_notifications_async = AsyncMock(return_value=[mock_notification])
        mock_listener_cls.current = mock_listener

        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            access, result = loop.run_until_complete(worker._poll())
            assert access == 1
            assert len(result) == 1
            assert result[0]["app"] == "TestApp"
            assert result[0]["text"] == "Test message"
        finally:
            loop.close()
