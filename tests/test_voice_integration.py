"""End-to-end integration test for the voice input pipeline.

This test wires the wake-word listener -> STT manager -> command parser
end-to-end with a real QObject-backed fake listener and a real
MiniMaxSTTReader whose network layer is mocked. It exercises the
production wiring path that the per-module unit tests bypass.
"""
import os
import sys
from unittest.mock import MagicMock

import pytest
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication

from message_flight.config import AppConfig
from message_flight.voice_commands import VoiceCommand

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


class _RealListener(QObject):
    """QObject-backed fake that mimics OpenWakeWordListener's public surface.

    Emits real Qt signals so STTManager's signal connections work without
    the MagicMock-vs-pyqtBoundSignal incompatibility.
    """

    wake_word_detected = pyqtSignal()
    error_occurred = pyqtSignal(str)
    audio_frame = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_running = False
        self._is_paused = False
        self._frames_emitted = 0

    def start(self) -> None:
        self._is_running = True

    def stop(self) -> None:
        self._is_running = False

    def pause(self) -> None:
        self._is_paused = True

    def resume(self) -> None:
        self._is_paused = False

    def feed_wake_word(self) -> None:
        """Simulate the listener detecting the wake word."""
        if not self._is_running or self._is_paused:
            return
        self.wake_word_detected.emit()

    def feed_audio(self, chunk: bytes) -> None:
        """Simulate the mic stream delivering an 80ms PCM frame."""
        if not self._is_running:
            return
        self._frames_emitted += 1
        self.audio_frame.emit(chunk)

    @property
    def is_running(self) -> bool:
        return bool(self._is_running)

    @property
    def is_paused(self) -> bool:
        return bool(self._is_paused)


def _silence_chunk(size: int = 2560) -> bytes:
    """80ms of 16kHz mono int16 silence = 1280 samples * 2 bytes."""
    return b"\x00\x00" * (size // 2)


def _tone_chunk(size: int = 2560, amplitude: int = 5000) -> bytes:
    """80ms of 16kHz mono int16 tone (above silence threshold)."""
    import struct
    n = size // 2
    return b"".join(struct.pack("<h", amplitude) for _ in range(n))


def test_end_to_end_wake_word_then_pause_command(qapp) -> None:
    """Full happy path: wake word fires -> audio frames -> STT returns 'pause' -> command routed."""
    from message_flight.stt_manager import STTManager

    cfg = AppConfig(stt_enabled=True)
    listener = _RealListener()
    stt = MagicMock()
    stt.transcribed = MagicMock()
    stt.error_occurred = MagicMock()

    mgr = STTManager(cfg, listener=listener, stt=stt)  # type: ignore[arg-type]
    listener.start()
    mgr.start()

    # Production wiring: tray_app._init_stt_manager does this; tests must too
    listener.audio_frame.connect(mgr._on_audio_chunk)

    captured_commands: list[str] = []
    mgr.command_recognized.connect(captured_commands.append)

    # Step 1: wake word fires
    assert mgr.state.value == "idle"
    listener.feed_wake_word()

    # Wait for Qt event loop to deliver the cross-thread signal
    QApplication.processEvents()
    assert mgr.state.value == "listening"
    assert listener.is_paused is True

    # Step 2: user speaks "暂停" — feed tone then silence to trigger STT
    for _ in range(5):
        listener.feed_audio(_tone_chunk())  # speech
    for _ in range(7):  # > SILENCE_FRAME_COUNT=6
        listener.feed_audio(_silence_chunk())  # silence triggers finish

    QApplication.processEvents()
    # STT should be called with the buffered audio
    stt.transcribe.assert_called_once()
    buffered_audio = stt.transcribe.call_args.args[0]
    # 5 tone frames + 6 silence frames (the 6th triggers the finish) = 11
    assert len(buffered_audio) == 11 * 2560

    # Step 3: simulate ASR returning "暂停"
    audio_arg = buffered_audio
    mgr._on_stt_transcribed("暂停", audio_arg)

    QApplication.processEvents()
    assert captured_commands == [VoiceCommand.PAUSE.value]
    # The return-to-idle is scheduled via 1s QTimer; manually fire it
    mgr._return_to_idle()
    assert mgr.state.value == "idle"

    mgr.stop()


def test_end_to_end_no_match_emits_failed_signal(qapp) -> None:
    """Wake word -> STT returns nonsense -> transcript_failed('no_match') -> toast territory."""
    from message_flight.stt_manager import STTManager

    cfg = AppConfig(stt_enabled=True)
    listener = _RealListener()
    stt = MagicMock()
    stt.transcribed = MagicMock()
    stt.error_occurred = MagicMock()

    mgr = STTManager(cfg, listener=listener, stt=stt)  # type: ignore[arg-type]
    listener.start()
    mgr.start()

    # Production wiring: tray_app._init_stt_manager does this; tests must too
    listener.audio_frame.connect(mgr._on_audio_chunk)

    captured_failures: list[str] = []
    mgr.transcript_failed.connect(captured_failures.append)

    listener.feed_wake_word()
    QApplication.processEvents()

    for _ in range(5):
        listener.feed_audio(_tone_chunk())
    for _ in range(7):
        listener.feed_audio(_silence_chunk())
    QApplication.processEvents()

    # Simulate ASR returning nonsense
    mgr._on_stt_transcribed("今天天气不错", b"")
    QApplication.processEvents()

    assert captured_failures == ["no_match"]
    mgr.stop()


def test_end_to_end_resume_command(qapp) -> None:
    """Wake word -> ASR 'resume' -> VoiceCommand.RESUME.value emitted."""
    from message_flight.stt_manager import STTManager

    cfg = AppConfig(stt_enabled=True)
    listener = _RealListener()
    stt = MagicMock()
    stt.transcribed = MagicMock()
    stt.error_occurred = MagicMock()

    mgr = STTManager(cfg, listener=listener, stt=stt)  # type: ignore[arg-type]
    listener.start()
    mgr.start()

    # Production wiring: tray_app._init_stt_manager does this; tests must too
    listener.audio_frame.connect(mgr._on_audio_chunk)

    captured: list[str] = []
    mgr.command_recognized.connect(captured.append)

    listener.feed_wake_word()
    QApplication.processEvents()
    for _ in range(5):
        listener.feed_audio(_tone_chunk())
    for _ in range(7):
        listener.feed_audio(_silence_chunk())
    QApplication.processEvents()

    mgr._on_stt_transcribed("resume", b"")
    QApplication.processEvents()

    assert captured == [VoiceCommand.RESUME.value]
    mgr.stop()


def test_end_to_end_stt_network_error(qapp) -> None:
    """Wake word -> audio -> STT error -> transcript_failed('network') -> idle."""
    from message_flight.stt_manager import STTManager

    cfg = AppConfig(stt_enabled=True)
    listener = _RealListener()
    stt = MagicMock()
    stt.transcribed = MagicMock()
    stt.error_occurred = MagicMock()

    mgr = STTManager(cfg, listener=listener, stt=stt)  # type: ignore[arg-type]
    listener.start()
    mgr.start()

    # Production wiring: tray_app._init_stt_manager does this; tests must too
    listener.audio_frame.connect(mgr._on_audio_chunk)

    captured_failures: list[str] = []
    mgr.transcript_failed.connect(captured_failures.append)

    listener.feed_wake_word()
    QApplication.processEvents()
    for _ in range(5):
        listener.feed_audio(_tone_chunk())
    for _ in range(7):
        listener.feed_audio(_silence_chunk())
    QApplication.processEvents()

    # Simulate STT network error
    mgr._on_stt_error("connection refused", b"")
    QApplication.processEvents()

    assert captured_failures == ["network"]
    mgr.stop()


def test_end_to_end_audio_ignored_when_not_listening(qapp) -> None:
    """Audio frames arriving outside LISTENING state must be ignored."""
    from message_flight.stt_manager import STTManager

    cfg = AppConfig(stt_enabled=True)
    listener = _RealListener()
    stt = MagicMock()

    mgr = STTManager(cfg, listener=listener, stt=stt)  # type: ignore[arg-type]
    listener.start()
    mgr.start()

    # Production wiring: tray_app._init_stt_manager does this; tests must too
    listener.audio_frame.connect(mgr._on_audio_chunk)

    # Feed audio in IDLE state — must NOT trigger STT
    for _ in range(20):
        listener.feed_audio(_tone_chunk())
        listener.feed_audio(_silence_chunk())
    QApplication.processEvents()

    stt.transcribe.assert_not_called()
    mgr.stop()
