"""Tests for the TTS notification reader (Task 04)."""
from unittest.mock import patch

import pytest

from message_flight.tts import OnlineTTSReader, SAPIReader, TTSReader


def test_disabled_tts_is_noop():
    """A reader created with enabled=False must silently ignore speak() calls."""
    reader = TTSReader(enabled=False)
    assert reader._enabled is False
    reader.speak("test")  # no crash


def test_sapi_reader_downgrades_when_win32com_missing():
    """If win32com.client cannot be imported, SAPIReader must downgrade to disabled."""
    with patch.dict("sys.modules", {"win32com": None, "win32com.client": None}):
        with patch("builtins.__import__", side_effect=ImportError("no module")):
            reader = SAPIReader(enabled=True)
    assert reader._enabled is False


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


