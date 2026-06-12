"""Tests for OpenWakeWordListener."""
import os
import sys
from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtCore import QCoreApplication

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    app = QCoreApplication.instance() or QCoreApplication(sys.argv)
    yield app


def test_constructs_with_default_model() -> None:
    from message_flight.wake_word import OpenWakeWordListener

    with patch("openwakeword.model.Model") as mock_model:
        listener = OpenWakeWordListener()
        mock_model.assert_called_once()
        assert listener.is_running is False
        assert listener.is_paused is False


def test_constructs_with_named_model() -> None:
    from message_flight.wake_word import OpenWakeWordListener

    with patch("openwakeword.model.Model") as mock_model:
        listener = OpenWakeWordListener(model_name="alexa", sensitivity=0.7)
        mock_model.assert_called_once()
        call_kwargs = mock_model.call_args.kwargs
        assert call_kwargs.get("wakeword_models") == ["alexa"]
        assert listener._worker._threshold == 0.7


def test_construct_fails_when_model_load_raises() -> None:
    from message_flight.wake_word import OpenWakeWordListener, WakeWordInitError

    with patch("openwakeword.model.Model", side_effect=RuntimeError("download failed")):
        with pytest.raises(WakeWordInitError):
            OpenWakeWordListener()


def test_start_opens_mic_stream_and_emits_on_detection(qapp) -> None:
    from message_flight.wake_word import OpenWakeWordListener

    with patch("openwakeword.model.Model") as mock_model_cls, \
         patch("sounddevice.InputStream") as mock_stream_cls:
        mock_model = MagicMock()
        mock_model.predict.return_value = {"hey_jarvis": 0.9}
        mock_model_cls.return_value = mock_model

        listener = OpenWakeWordListener()
        captured = []
        listener.wake_word_detected.connect(lambda: captured.append(True))

        listener.start()
        assert listener.is_running is True

        # Simulate one audio callback delivering a frame
        callback = mock_stream_cls.call_args.kwargs["callback"]
        fake_audio = MagicMock()
        callback(fake_audio, 1280, None, None)

        # Model predict should be called and detection should emit
        mock_model.predict.assert_called()
        assert len(captured) == 1

        listener.stop()


def test_pause_stops_emitting_while_resumed(qapp) -> None:
    from message_flight.wake_word import OpenWakeWordListener

    with patch("openwakeword.model.Model") as mock_model_cls, \
         patch("sounddevice.InputStream") as mock_stream_cls:
        mock_model = MagicMock()
        mock_model.predict.return_value = {"hey_jarvis": 0.9}
        mock_model_cls.return_value = mock_model

        listener = OpenWakeWordListener(debounce_seconds=0.0)
        captured = []
        listener.wake_word_detected.connect(lambda: captured.append(True))
        listener.start()
        callback = mock_stream_cls.call_args.kwargs["callback"]

        # While unpaused, frames trigger emit
        callback(MagicMock(), 1280, None, None)
        assert len(captured) == 1

        # Pause: frames should NOT trigger emit
        listener.pause()
        callback(MagicMock(), 1280, None, None)
        callback(MagicMock(), 1280, None, None)
        assert len(captured) == 1  # no new emissions

        # Resume: frames trigger emit again
        listener.resume()
        callback(MagicMock(), 1280, None, None)
        assert len(captured) == 2

        listener.stop()


def test_start_emits_error_occurred_when_mic_unavailable(qapp) -> None:
    """If sounddevice.InputStream raises, error_occurred must fire with a useful message."""
    from message_flight.wake_word import OpenWakeWordListener

    with patch("openwakeword.model.Model"), \
         patch("sounddevice.InputStream", side_effect=OSError("no default device")):
        listener = OpenWakeWordListener()
        captured = []
        listener.error_occurred.connect(lambda msg: captured.append(msg))

        listener.start()

        assert listener.is_running is False
        assert len(captured) == 1
        assert "microphone" in captured[0].lower()


def test_debounce_ignores_duplicate_within_window(qapp) -> None:
    from message_flight.wake_word import OpenWakeWordListener

    with patch("openwakeword.model.Model") as mock_model_cls, \
         patch("sounddevice.InputStream") as mock_stream_cls:
        mock_model = MagicMock()
        mock_model.predict.return_value = {"hey_jarvis": 0.9}
        mock_model_cls.return_value = mock_model

        listener = OpenWakeWordListener(debounce_seconds=1.0)
        captured = []
        listener.wake_word_detected.connect(lambda: captured.append(True))
        listener.start()

        callback = mock_stream_cls.call_args.kwargs["callback"]
        callback(MagicMock(), 1280, None, None)
        callback(MagicMock(), 1280, None, None)
        callback(MagicMock(), 1280, None, None)

        # Only first should emit; rest debounced
        assert len(captured) == 1

        listener.stop()


def test_stop_closes_mic_stream(qapp) -> None:
    from message_flight.wake_word import OpenWakeWordListener

    with patch("openwakeword.model.Model"), \
         patch("sounddevice.InputStream") as mock_stream_cls:
        mock_stream = MagicMock()
        mock_stream_cls.return_value = mock_stream

        listener = OpenWakeWordListener()
        listener.start()
        listener.stop()

        assert listener.is_running is False
        mock_stream.stop.assert_called()
        mock_stream.close.assert_called()
