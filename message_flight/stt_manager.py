"""Orchestrate wake word → STT → command dispatch.

State machine:
    IDLE
      │ (wake_word_detected)
      ▼
    LISTENING_FOR_COMMAND
      │ (silence detected OR 5s timeout)
      ▼
    PROCESSING
      │ (transcribed OR error)
      ▼
    IDLE  (after 1s grace period)
"""
from __future__ import annotations

import io
import logging
import math
import struct
from enum import Enum
from typing import Optional

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from message_flight.config import AppConfig
from message_flight.stt import MiniMaxSTTReader
from message_flight.voice_commands import parse_command
from message_flight.wake_word import OpenWakeWordListener, SherpaOnnxListener, create_listener

logger = logging.getLogger(__name__)

# Audio parameters (must match OpenWakeWordListener)
SAMPLE_RATE = 16000
SAMPLE_WIDTH = 2  # int16 = 2 bytes

# Silence detection
SILENCE_RMS_THRESHOLD = 200   # 16-bit PCM RMS below this counts as silence
SILENCE_FRAME_COUNT = 6        # consecutive silent frames to end utterance (~0.5s)

# Timeouts
COMMAND_TIMEOUT_MS = 5000      # max recording time
RETURN_TO_IDLE_MS = 1000       # grace period after command/error


# Cached prompt sound (generated once, reused across detections)
_DING_SOUND: Any = None


def _play_ding() -> None:
    """Play a short 'ding' prompt sound when the wake word is detected.

    Generates a 150ms sine-wave chime in-memory and plays it via
    pygame.mixer.  Falls back silently if pygame or numpy is unavailable.
    The sound is generated once and cached for reuse.
    """
    global _DING_SOUND
    try:
        import numpy as np
        import pygame.mixer

        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=22050)

        if _DING_SOUND is None:
            sr = 22050
            duration = 0.15  # seconds
            freq = 880  # A5 note
            t = np.linspace(0, duration, int(sr * duration), endpoint=False)
            # Exponential decay envelope for a pleasant chime
            wave = (np.sin(2 * np.pi * freq * t) * np.exp(-t * 20) * 0.4 * 32767).astype(np.int16)
            # Stereo: duplicate mono channel
            stereo = np.column_stack([wave, wave])
            _DING_SOUND = pygame.mixer.Sound(buffer=stereo.tobytes())

        _DING_SOUND.play()
    except Exception as e:
        logger.debug("_play_ding: failed to play prompt sound: %s", e)


class STTManagerState(Enum):
    IDLE = "idle"
    LISTENING_FOR_COMMAND = "listening"
    PROCESSING = "processing"


class STTManager(QObject):
    """Coordinate WakeWordListener + STTReader + VoiceCommandParser.

    Signals:
        state_changed(state): STTManagerState.value — drives tray icon.
        command_recognized(VoiceCommand.value): Fired when a command is matched.
        transcript_failed(reason): One of "empty", "no_match", "network".
        listening_started(): Fired when wake word detected and recording starts.
    """

    state_changed = pyqtSignal(str)
    command_recognized = pyqtSignal(str)
    transcript_failed = pyqtSignal(str)
    listening_started = pyqtSignal()

    def __init__(
        self,
        config: AppConfig,
        listener: Optional[OpenWakeWordListener | SherpaOnnxListener] = None,
        stt: Optional[MiniMaxSTTReader] = None,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._config = config
        self._state = STTManagerState.IDLE
        self._listener: Optional[OpenWakeWordListener | SherpaOnnxListener] = listener
        self._stt: Optional[MiniMaxSTTReader] = stt

        # Inject dependencies if provided, else create from config
        if self._listener is None and config.stt_enabled:
            self._listener = create_listener(wake_word_key=config.stt_wake_word)
        if self._stt is None:
            self._stt = MiniMaxSTTReader(api_key=config.minimax_subscription_key)

        self._audio_buffer = bytearray()
        self._silent_frames = 0
        self._skip_frames = 3  # discard first ~240ms (wake word tail)
        self._silence_timer: Optional[QTimer] = None
        self._idle_timer: Optional[QTimer] = None

        # Wire up
        if self._listener is not None:
            self._listener.wake_word_detected.connect(self._on_wake_word)
            self._listener.audio_frame.connect(self._on_audio_chunk)
            self._listener.error_occurred.connect(self._on_listener_error)
            # For SherpaOnnxListener: auto-start when model download completes
            if hasattr(self._listener, "model_ready"):
                self._listener.model_ready.connect(self._on_model_ready)
        if self._stt is not None:
            self._stt.transcribed.connect(self._on_stt_transcribed)
            self._stt.error_occurred.connect(self._on_stt_error)

    @property
    def state(self) -> STTManagerState:
        return self._state

    def start(self) -> None:
        if not self._config.stt_enabled:
            logger.info("STTManager.start: stt disabled, skipping")
            return
        if self._listener is not None:
            self._listener.start()

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
        if self._silence_timer is not None:
            self._silence_timer.stop()
        if self._idle_timer is not None:
            self._idle_timer.stop()

    def set_enabled(self, enabled: bool) -> None:
        self._config.stt_enabled = enabled
        if enabled:
            self.start()
        else:
            self.stop()

    def _set_state(self, new_state: STTManagerState) -> None:
        if self._state != new_state:
            logger.info("STTManager: state %s -> %s", self._state.value, new_state.value)
            self._state = new_state
            self.state_changed.emit(new_state.value)

    def _on_wake_word(self) -> None:
        if self._state != STTManagerState.IDLE:
            # Already in command flow; ignore double-trigger
            return
        logger.info("STTManager: wake word detected")
        _play_ding()
        self._set_state(STTManagerState.LISTENING_FOR_COMMAND)
        if self._listener is not None:
            self._listener.pause()
        self._audio_buffer = bytearray()
        self._silent_frames = 0
        self._skip_frames = 3  # discard first ~240ms (wake word tail)
        self.listening_started.emit()

        # Start hard timeout
        self._silence_timer = QTimer(self)
        self._silence_timer.setSingleShot(True)
        self._silence_timer.timeout.connect(self._on_silence_timeout)
        self._silence_timer.start(COMMAND_TIMEOUT_MS)

    def _on_audio_chunk(self, audio_chunk: bytes) -> None:
        """Called once per 80ms frame of 16kHz mono int16 PCM (2560 bytes).

        In production this is invoked by a connection from the wake-word
        listener's frame signal. Tests call it directly to drive the
        state machine.
        """
        if self._state != STTManagerState.LISTENING_FOR_COMMAND:
            return
        # Discard the first few frames after wake-word detection to
        # avoid feeding the wake-word's tail audio into the STT buffer.
        if self._skip_frames > 0:
            self._skip_frames -= 1
            return
        self._audio_buffer.extend(audio_chunk)

        if self._is_silent(audio_chunk):
            self._silent_frames += 1
            if self._silent_frames >= SILENCE_FRAME_COUNT:
                self._finish_command_audio()
        else:
            self._silent_frames = 0

    def _on_silence_timeout(self) -> None:
        if self._state == STTManagerState.LISTENING_FOR_COMMAND:
            self._finish_command_audio()

    def _finish_command_audio(self) -> None:
        if self._silence_timer is not None:
            self._silence_timer.stop()
        if not self._audio_buffer:
            self.transcript_failed.emit("empty")
            self._schedule_return_to_idle()
            return
        self._set_state(STTManagerState.PROCESSING)
        audio = bytes(self._audio_buffer)
        if self._stt is not None:
            self._stt.transcribe(audio)

    def _on_stt_transcribed(self, text: str, _audio: bytes) -> None:
        cmd = parse_command(text)
        if cmd is None:
            self.transcript_failed.emit("no_match")
            self._schedule_return_to_idle()
            return
        logger.info("STTManager: command recognized: %s", cmd.value)
        self.command_recognized.emit(cmd.value)
        self._schedule_return_to_idle()

    def _on_stt_error(self, error_msg: str, _audio: bytes) -> None:
        logger.error("STTManager: STT error: %s", error_msg)
        self.transcript_failed.emit("network")
        self._schedule_return_to_idle()

    def _on_listener_error(self, error_msg: str) -> None:
        logger.error("STTManager: listener error: %s", error_msg)
        self.transcript_failed.emit("mic")
        if self._state != STTManagerState.IDLE:
            self._schedule_return_to_idle()

    def _on_model_ready(self) -> None:
        """Called when SherpaOnnxListener finishes downloading the model."""
        logger.info("STTManager: model ready, starting listener")
        if self._listener is not None:
            self._listener.start()

    def _schedule_return_to_idle(self) -> None:
        if self._idle_timer is not None:
            self._idle_timer.stop()
            self._idle_timer.deleteLater()
        self._idle_timer = QTimer(self)
        self._idle_timer.setSingleShot(True)
        self._idle_timer.timeout.connect(self._return_to_idle)
        self._idle_timer.start(RETURN_TO_IDLE_MS)

    def _return_to_idle(self) -> None:
        if self._listener is not None:
            self._listener.resume()
        self._set_state(STTManagerState.IDLE)

    @staticmethod
    def _is_silent(audio_chunk: bytes) -> bool:
        """Compute RMS of a 16-bit PCM chunk and compare to threshold."""
        if not audio_chunk:
            return True
        try:
            import numpy as np
            samples = np.frombuffer(audio_chunk, dtype=np.int16).astype(np.float64)
            rms = np.sqrt(np.mean(samples * samples))
        except Exception:
            # Fallback for environments without numpy
            n_samples = len(audio_chunk) // 2
            if n_samples == 0:
                return True
            samples = struct.unpack(f"<{n_samples}h", audio_chunk)
            total = sum(s * s for s in samples)
            rms = math.sqrt(total / n_samples)
        return rms < SILENCE_RMS_THRESHOLD
