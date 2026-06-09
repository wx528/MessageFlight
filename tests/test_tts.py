"""Tests for the TTS notification reader (Task 04)."""
from unittest.mock import patch

import pytest

from message_flight.tts import MiniMaxReader, SAPIReader, TTSReader


def test_disabled_tts_is_noop():
    """A reader created with enabled=False must silently ignore speak() calls."""
    reader = TTSReader(enabled=False)
    assert reader._enabled is False
    reader.speak("test")  # no crash


def test_sapi_reader_downgrades_when_win32com_missing():
    """SAPIReader should silently downgrade when win32com is unavailable."""
    def mock_init(self):
        self._enabled = False
        self._speaker = None

    with patch.object(SAPIReader, "_init_sapi", mock_init):
        reader = SAPIReader(enabled=True)
    assert reader._enabled is False
    assert reader._speaker is None


def test_default_title_template():
    """The default title_template must be '{message}'."""
    reader = TTSReader(enabled=False)
    assert reader._title_template == "{message}"


def test_custom_title_template():
    """A custom title_template passed to __init__ must be stored."""
    reader = TTSReader(enabled=False, title_template="hi {message}")
    assert reader._title_template == "hi {message}"


def test_template_format():
    """Template formatting must insert the message into the placeholder."""
    reader = TTSReader(enabled=False, title_template="您有新消息了。{message}")
    assert "您有新消息了。hello" == reader._title_template.format(message="hello")


def test_minimax_reader_init():
    """MiniMaxReader should store api_key and voice_id."""
    reader = MiniMaxReader(api_key="test-key", voice_id="female-shaonv", enabled=False)
    assert reader._api_key == "test-key"
    assert reader._voice_id == "female-shaonv"


def test_minimax_reader_empty_key_emits_error(qtbot):
    """MiniMaxReader with empty api_key must emit error_occurred."""
    reader = MiniMaxReader(api_key="", enabled=True)
    with qtbot.waitSignal(reader.error_occurred, timeout=1000):
        reader.speak("test")


