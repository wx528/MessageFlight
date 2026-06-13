"""Tests for STTManager state machine."""
import os
import sys
from unittest.mock import MagicMock

import pytest
from PyQt6.QtWidgets import QApplication

from message_flight.config import AppConfig

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


def _make_manager(qapp, *, stt_enabled: bool = True) -> tuple:
    """Build an STTManager with mocked listener and STT reader."""
    from message_flight.stt_manager import STTManager

    cfg = AppConfig(stt_enabled=stt_enabled)
    listener = MagicMock()
    listener.is_running = False
    listener.is_paused = False

    stt = MagicMock()
    stt.transcribed = MagicMock()
    stt.error_occurred = MagicMock()

    mgr = STTManager(cfg, listener=listener, stt=stt)
    mgr._listener = listener
    mgr._stt = stt
    return mgr, listener, stt


def test_state_starts_idle_when_enabled(qapp) -> None:
    mgr, _listener, _stt = _make_manager(qapp)
    assert mgr.state.value == "idle"
    mgr.stop()


def test_wake_word_transitions_to_listening(qapp) -> None:
    mgr, listener, _stt = _make_manager(qapp)
    listener.start()
    mgr.start()
    mgr._on_wake_word()
    assert mgr.state.value == "listening"
    listener.pause.assert_called_once()
    mgr.stop()


def test_command_match_returns_to_idle(qapp) -> None:
    from message_flight.voice_commands import VoiceCommand

    mgr, listener, stt = _make_manager(qapp)
    captured = []
    mgr.command_recognized.connect(lambda c: captured.append(c))
    mgr.start()
    listener.is_paused = True
    mgr._state = mgr._state.__class__.LISTENING_FOR_COMMAND

    mgr._on_stt_transcribed("暂停", b"")
    assert captured == [VoiceCommand.PAUSE.value]
    mgr.stop()


def test_no_command_match_emits_transcript_failed(qapp) -> None:
    mgr, listener, _stt = _make_manager(qapp)
    captured = []
    mgr.transcript_failed.connect(lambda r: captured.append(r))
    mgr.start()
    mgr._state = mgr._state.__class__.LISTENING_FOR_COMMAND

    mgr._on_stt_transcribed("今天天气不错", b"")
    assert captured == ["no_match"]
    mgr.stop()


def test_stt_error_returns_to_idle(qapp) -> None:
    mgr, listener, _stt = _make_manager(qapp)
    captured = []
    mgr.transcript_failed.connect(lambda r: captured.append(r))
    mgr.start()
    mgr._state = mgr._state.__class__.LISTENING_FOR_COMMAND

    mgr._on_stt_error("network failed", b"")
    assert captured == ["network"]
    mgr.stop()


def test_silence_detection_triggers_stt(qapp) -> None:
    mgr, listener, stt = _make_manager(qapp)
    mgr.start()
    mgr._state = mgr._state.__class__.LISTENING_FOR_COMMAND
    mgr._skip_frames = 0  # bypass wake-word tail skip for this test

    # Feed 10 frames of silence (low energy) — silence threshold is 6 frames
    fake_chunk = b"\x00\x00" * 1280  # 80ms of silence
    for _ in range(10):
        mgr._on_audio_chunk(fake_chunk)

    stt.transcribe.assert_called_once()
    mgr.stop()


def test_audio_below_silence_threshold_does_not_trigger(qapp) -> None:
    mgr, _listener, stt = _make_manager(qapp)
    mgr.start()
    mgr._state = mgr._state.__class__.LISTENING_FOR_COMMAND
    mgr._skip_frames = 0  # bypass wake-word tail skip for this test

    # Only 3 frames of silence — below 6-frame threshold
    fake_chunk = b"\x00\x00" * 1280
    for _ in range(3):
        mgr._on_audio_chunk(fake_chunk)

    stt.transcribe.assert_not_called()
    mgr.stop()


def test_disabled_starts_does_nothing(qapp) -> None:
    mgr, listener, stt = _make_manager(qapp, stt_enabled=False)
    mgr.start()
    assert listener.start.call_count == 0
    mgr.stop()


def test_set_enabled_false_stops_listener(qapp) -> None:
    mgr, listener, _stt = _make_manager(qapp)
    mgr.start()
    mgr.set_enabled(False)
    listener.stop.assert_called()


def test_set_enabled_true_starts_listener(qapp) -> None:
    mgr, listener, _stt = _make_manager(qapp, stt_enabled=False)
    mgr.set_enabled(True)
    assert listener.start.call_count == 1
    mgr.stop()


def test_double_wake_word_within_1s_ignored(qapp) -> None:
    """STTManager should not re-enter LISTENING while already in command flow."""
    mgr, listener, _stt = _make_manager(qapp)
    mgr.start()
    mgr._state = mgr._state.__class__.LISTENING_FOR_COMMAND

    captured_state = []
    mgr.state_changed.connect(lambda s: captured_state.append(s))

    # Second wake word fires while already listening
    mgr._on_wake_word()
    # No additional state transition should occur
    assert captured_state == []
    mgr.stop()


def test_audio_buffer_passed_to_stt(qapp) -> None:
    mgr, _listener, stt = _make_manager(qapp)
    mgr.start()
    mgr._state = mgr._state.__class__.LISTENING_FOR_COMMAND
    mgr._skip_frames = 0  # bypass wake-word tail skip for this test

    fake_chunk = b"\x00\x00" * 1280
    for _ in range(6):
        mgr._on_audio_chunk(fake_chunk)

    call_args = stt.transcribe.call_args.args[0]
    # 6 frames × 1280 samples × 2 bytes = 15360 bytes
    assert len(call_args) == 6 * 1280 * 2
    mgr.stop()


def test_listening_emits_listening_started_signal(qapp) -> None:
    mgr, listener, _stt = _make_manager(qapp)
    captured = []
    mgr.listening_started.connect(lambda: captured.append(True))
    listener.start()
    mgr.start()
    mgr._on_wake_word()
    assert captured == [True]
    mgr.stop()


def test_silence_timeout_triggers_stt_with_partial_audio(qapp) -> None:
    """5s hard timeout should still trigger STT with whatever audio was buffered."""
    from message_flight.stt_manager import COMMAND_TIMEOUT_MS
    mgr, _listener, stt = _make_manager(qapp)
    mgr.start()
    mgr._state = mgr._state.__class__.LISTENING_FOR_COMMAND
    mgr._skip_frames = 0  # bypass wake-word tail skip for this test

    # Feed 2 frames (below silence threshold) — NOT enough to trigger silence detection
    fake_chunk = b"\x00\x00" * 1280
    mgr._on_audio_chunk(fake_chunk)
    mgr._on_audio_chunk(fake_chunk)

    # Manually trigger the timeout handler
    assert COMMAND_TIMEOUT_MS == 5000  # spec value
    mgr._on_silence_timeout()

    # STT should be called with whatever was buffered
    stt.transcribe.assert_called_once()
    assert len(stt.transcribe.call_args.args[0]) == 2 * 1280 * 2
    mgr.stop()


def test_listener_error_returns_to_idle(qapp) -> None:
    """Listener error during LISTENING should still return the manager to IDLE."""
    mgr, _listener, _stt = _make_manager(qapp)
    captured = []
    mgr.transcript_failed.connect(lambda r: captured.append(r))
    mgr.start()
    mgr._state = mgr._state.__class__.LISTENING_FOR_COMMAND

    mgr._on_listener_error("mic died")

    assert captured == ["mic"]
    # State stays LISTENING immediately; _schedule_return_to_idle() is async
    # The 1s timer is started but not fired in this test
    assert mgr.state.value == "listening"  # not yet returned
    # Manually fire the return-to-idle timer by calling _return_to_idle directly
    mgr._return_to_idle()
    assert mgr.state.value == "idle"


def test_audio_frames_flow_from_listener_to_stt_manager(qapp) -> None:
    """End-to-end: listener.audio_frame must reach STTManager._on_audio_chunk.

    Regression test for the production wiring bug where the listener was
    paused during LISTENING_FOR_COMMAND but no audio frames were forwarded
    to STTManager, so every command timed out with an empty buffer.

    This mirrors what tray_app._init_stt_manager wires in production.
    """
    from PyQt6.QtCore import QObject, pyqtSignal

    from message_flight.stt_manager import STTManager

    class _FakeListener(QObject):
        wake_word_detected = pyqtSignal()
        error_occurred = pyqtSignal(str)
        audio_frame = pyqtSignal(object)

        def __init__(self) -> None:
            super().__init__()
            self.started = False
            self.paused = False

        def start(self) -> None:
            self.started = True

        def pause(self) -> None:
            self.paused = True

        def resume(self) -> None:
            self.paused = False

        def stop(self) -> None:
            self.started = False

    cfg = AppConfig(stt_enabled=True)
    listener = _FakeListener()
    stt = MagicMock()
    stt.transcribed = MagicMock()
    stt.error_occurred = MagicMock()

    mgr = STTManager(cfg, listener=listener, stt=stt)  # type: ignore[arg-type]
    mgr.start()

    # Frames arriving before wake word are ignored (state == IDLE)
    silence = b"\x00\x00" * 1280
    listener.audio_frame.emit(silence)
    assert len(mgr._audio_buffer) == 0

    # Fire wake word: enters LISTENING_FOR_COMMAND
    listener.wake_word_detected.emit()
    assert mgr.state.value == "listening"
    assert listener.paused is True

    # Now frames must be buffered and silence detection must drive STT
    # 3 frames are skipped (wake word tail), then 6 silent frames trigger STT
    for _ in range(10):
        listener.audio_frame.emit(silence)

    stt.transcribe.assert_called_once()
    audio_passed = stt.transcribe.call_args.args[0]
    # 3 frames skipped (wake word tail), then 6 silent frames buffered + trigger
    assert len(audio_passed) == 6 * 1280 * 2
    mgr.stop()
