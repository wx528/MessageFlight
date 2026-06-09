"""Tests for tray app TTS integration (Task 04)."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from unittest.mock import MagicMock, patch

import pytest


def test_on_real_notification_calls_tts_speak():
    """When a real notification arrives, tray_app must call tts.speak() with the display text."""
    from message_flight.tray_app import TrayApplication

    with patch("message_flight.tray_app.QApplication"), \
         patch("message_flight.tray_app.QSystemTrayIcon"), \
         patch("message_flight.tray_app.FlightWidget"), \
         patch("message_flight.tray_app.QMenu"), \
         patch("message_flight.tray_app.QAction"), \
         patch("message_flight.tray_app.WINSOK_AVAILABLE", False), \
         patch("message_flight.tray_app.TrayApplication._create_tray_icon", return_value=MagicMock()), \
         patch("message_flight.tray_app.SAPIReader") as mock_tts_cls:
        mock_tts = MagicMock()
        mock_tts_cls.return_value = mock_tts
        app = TrayApplication()
        app._on_real_notification("WeChat", "hello")
        mock_tts.speak.assert_called_once()
