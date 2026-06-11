"""Text-to-speech notification reader.

Provides ``TTSReader`` abstract base class and two concrete implementations:
- ``SAPIReader``  – Windows SAPI via pywin32 (falls back to no-op if unavailable)
- ``MiniMaxReader`` – MiniMax online TTS engine via Qt async network + pygame audio
"""
from __future__ import annotations

import binascii
import json
import logging
import os
import sys
import tempfile
import uuid

from PyQt6.QtCore import QByteArray, QObject, QTimer, QUrl, pyqtSignal
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

logger = logging.getLogger(__name__)


class TTSReader:
    """Abstract TTS reader that formats a message through a template and
    delegates speaking to :meth:`_speak_impl`.
    """

    def __init__(self, enabled: bool = True, title_template: str = "{message}"):
        self._enabled = enabled
        self._title_template = title_template

    def speak(self, message: str) -> None:
        """If enabled, format *message* with :attr:`_title_template` and speak it."""
        if not self._enabled:
            logger.debug("TTSReader.speak: skipped (disabled)")
            return
        try:
            text = self._title_template.replace("{message}", message)
        except Exception as e:
            logger.error("TTS format error: %s", e)
            return
        try:
            logger.debug("TTSReader.speak: speaking text=%r", text)
            self._speak_impl(text)
        except Exception as e:
            logger.error("TTS speak error: %s", e)

    def _speak_impl(self, text: str) -> None:
        """Concrete subclasses must override this method."""
        raise NotImplementedError


class SAPIReader(TTSReader):
    """Windows SAPI TTS via ``win32com.client``.

    If ``pywin32`` is not installed or the platform is not Windows,
    initialization silently fails and :meth:`speak` becomes a no-op.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self._enabled:
            self._init_sapi()

    def _init_sapi(self) -> None:
        if sys.platform != "win32":
            logger.warning("SAPIReader: not on Windows, disabling")
            self._enabled = False
            return
        try:
            import win32com.client

            self._speaker = win32com.client.Dispatch("SAPI.SpVoice")
            logger.info("SAPIReader: SAPI initialized successfully")
        except Exception as e:
            logger.warning("SAPIReader: failed to initialize SAPI: %s", e)
            self._enabled = False

    # SVSFlagsAsync = 1 — speak asynchronously so we don't block the UI
    _SVS_FLAGS_ASYNC = 1

    def _speak_impl(self, text: str) -> None:
        logger.debug("SAPIReader._speak_impl: speaking asynchronously")
        self._speaker.Speak(text, self._SVS_FLAGS_ASYNC)


class MiniMaxReader(TTSReader, QObject):
    """MiniMax TTS via QNetworkAccessManager + pygame.mixer.

    Asynchronously calls the MiniMax API and plays the returned MP3.
    On any error, emits ``error_occurred`` so TTSManager can fall back
    to SAPIReader.
    """

    playback_finished = pyqtSignal()
    # error_occurred(error_message: str, original_text: str)
    # original_text is passed so TTSManager can fall back with the correct message
    error_occurred = pyqtSignal(str, str)

    _ENDPOINT = "https://api.minimaxi.com/v1/t2a_v2"
    _DEFAULT_VOICE = "male-qn-qingse"
    _TIMEOUT_MS = 10000

    def __init__(
        self,
        api_key: str = "",
        voice_id: str = _DEFAULT_VOICE,
        speed: float = 1.0,
        vol: float = 1.0,
        enabled: bool = True,
        title_template: str = "{message}",
    ):
        TTSReader.__init__(self, enabled=enabled, title_template=title_template)
        QObject.__init__(self)
        self._api_key = api_key
        self._voice_id = voice_id
        self._speed = speed
        self._vol = vol
        self._network = QNetworkAccessManager()
        self._active_audio_files: set[str] = set()  # Track temp files for cleanup
        self._last_text = ""  # Last text sent to MiniMax, for error fallback
        self._reply_text_map: dict[int, str] = {}  # id(reply) -> original text

        self._network.finished.connect(self._on_reply_finished)
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self.cleanup)
        logger.info("MiniMaxReader: initialized with voice_id=%s", voice_id)

    def _speak_impl(self, text: str) -> None:
        self._last_text = text
        if not self._api_key:
            logger.error("MiniMaxReader._speak_impl: api_key is empty")
            self.error_occurred.emit("MiniMax API key is empty", text)
            return

        logger.info("MiniMaxReader._speak_impl: sending TTS request for text=%r", text[:50])

        request = QNetworkRequest(QUrl(self._ENDPOINT))
        request.setTransferTimeout(self._TIMEOUT_MS)
        request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json")
        request.setRawHeader(b"Authorization", f"Bearer {self._api_key}".encode())

        payload = {
            "model": "speech-2.8-hd",
            "text": text,
            "stream": False,
            "voice_setting": {
                "voice_id": self._voice_id,
                "speed": self._speed,
                "vol": self._vol,
                "pitch": 0,
            },
            "audio_setting": {
                "sample_rate": 32000,
                "bitrate": 128000,
                "format": "mp3",
                "channel": 1,
            },
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        logger.debug("MiniMaxReader._speak_impl: request body=%s", body.decode("utf-8")[:200])
        reply = self._network.post(request, body)
        self._reply_text_map[id(reply)] = text

    def _on_reply_finished(self, reply: QNetworkReply) -> None:
        status_code = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
        logger.info("MiniMaxReader._on_reply_finished: HTTP status=%s", status_code)

        original_text = self._reply_text_map.pop(id(reply), self._last_text)

        if reply.error() != QNetworkReply.NetworkError.NoError:
            err_msg = f"MiniMax network error: {reply.errorString()}"
            logger.error("MiniMaxReader._on_reply_finished: %s", err_msg)
            self.error_occurred.emit(err_msg, original_text)
            reply.deleteLater()
            return

        data = reply.readAll()
        if data.isEmpty():
            logger.error("MiniMaxReader._on_reply_finished: empty response")
            self.error_occurred.emit("MiniMax returned empty response", original_text)
            reply.deleteLater()
            return

        try:
            response_text = data.data().decode("utf-8")
            logger.debug("MiniMaxReader._on_reply_finished: response=%s", response_text[:500])
            response_json = json.loads(response_text)
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            logger.error("MiniMaxReader._on_reply_finished: failed to parse response: %s", e)
            self.error_occurred.emit(f"MiniMax response parse error: {e}", original_text)
            reply.deleteLater()
            return

        # Check base_resp for API errors
        base_resp = response_json.get("base_resp", {})
        status_code_api = base_resp.get("status_code", 0)
        if status_code_api != 0:
            status_msg = base_resp.get("status_msg", "unknown error")
            err_msg = f"MiniMax API error {status_code_api}: {status_msg}"
            logger.error("MiniMaxReader._on_reply_finished: %s", err_msg)
            self.error_occurred.emit(err_msg, original_text)
            reply.deleteLater()
            return

        # Extract hex-encoded audio
        audio_hex = response_json.get("data", {}).get("audio", "")
        if not audio_hex:
            logger.error("MiniMaxReader._on_reply_finished: no audio in response")
            self.error_occurred.emit("MiniMax returned no audio data", self._last_text)
            reply.deleteLater()
            return

        try:
            audio_bytes = binascii.unhexlify(audio_hex)
            logger.info("MiniMaxReader._on_reply_finished: decoded %d bytes of audio", len(audio_bytes))
        except binascii.Error as e:
            logger.error("MiniMaxReader._on_reply_finished: failed to decode audio hex: %s", e)
            self.error_occurred.emit(f"MiniMax audio decode error: {e}", self._last_text)
            reply.deleteLater()
            return

        self._buffer = QByteArray(audio_bytes)
        # Use uuid to avoid filename collisions between concurrent requests
        audio_path = os.path.join(tempfile.gettempdir(), f"messageflight_{uuid.uuid4().hex}.mp3")
        with open(audio_path, "wb") as f:
            f.write(self._buffer.data())

        self._active_audio_files.add(audio_path)
        logger.info("MiniMaxReader._on_reply_finished: saved audio to %s (%d bytes)", audio_path, len(audio_bytes))

        # Use pygame.mixer to play audio (reliable cross-platform MP3 playback)
        self._play_audio_with_pygame(audio_path)
        reply.deleteLater()

    def _play_audio_with_pygame(self, audio_path: str) -> None:
        """Play audio file using pygame.mixer."""
        try:
            import pygame

            # Initialize pygame mixer if not already initialized
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=32000)
                logger.info("MiniMaxReader: pygame.mixer initialized")

            # Load and play the audio
            sound = pygame.mixer.Sound(audio_path)
            sound.set_volume(self._vol)
            sound.play()
            logger.info("MiniMaxReader: playing audio from %s", audio_path)

            # Track this file for cleanup
            timer = QTimer(self)
            timer.setSingleShot(True)
            # Capture audio_path by value to avoid closure issues
            timer.timeout.connect(lambda _path=audio_path, _timer=timer: self._cleanup_after_playback(_path, _timer))
            timer.start(100)  # Check every 100ms

        except Exception as e:
            logger.error("MiniMaxReader: failed to play audio with pygame: %s", e)
            self._remove_audio_file(audio_path)
            self.error_occurred.emit(f"Audio playback error: {e}", self._last_text)

    def _cleanup_after_playback(self, audio_path: str, timer: QTimer) -> None:
        """Check if pygame audio playback has finished and clean up the file."""
        try:
            import pygame
            if not pygame.mixer.get_busy():
                logger.debug("MiniMaxReader: playback finished for %s", audio_path)
                self.playback_finished.emit()
                timer.stop()
                timer.deleteLater()
                self._remove_audio_file(audio_path)
            else:
                # Still playing, check again
                timer.start(100)
        except Exception:
            timer.stop()
            timer.deleteLater()
            self._remove_audio_file(audio_path)

    def _remove_audio_file(self, audio_path: str) -> None:
        """Remove a temporary audio file and update tracking."""
        self._active_audio_files.discard(audio_path)
        if os.path.exists(audio_path):
            try:
                os.remove(audio_path)
                logger.debug("MiniMaxReader: removed temp file %s", audio_path)
            except OSError as e:
                logger.warning("MiniMaxReader: failed to remove temp file %s: %s", audio_path, e)

    def cleanup(self) -> None:
        """Remove all active temp audio files. Called on application exit."""
        for path in list(self._active_audio_files):
            self._remove_audio_file(path)
        self._active_audio_files.clear()
