"""Text-to-speech notification reader.

Provides ``TTSReader`` abstract base class and two concrete implementations:
- ``SAPIReader``  – Windows SAPI via pywin32 (falls back to no-op if unavailable)
- ``MiniMaxReader`` – MiniMax online TTS engine via Qt async network + media player
"""
from __future__ import annotations

import binascii
import json
import logging
import os
import sys
import tempfile

from PyQt6.QtCore import QByteArray, QObject, QUrl, pyqtSignal
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
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

    def _speak_impl(self, text: str) -> None:
        # SVSFlagsAsync = 1, speak asynchronously so we don't block the UI
        logger.debug("SAPIReader._speak_impl: speaking asynchronously")
        self._speaker.Speak(text, 1)


class MiniMaxReader(TTSReader, QObject):
    """MiniMax TTS via QNetworkAccessManager + QMediaPlayer.

    Asynchronously calls the MiniMax API and plays the returned MP3.
    On any error, emits ``error_occurred`` so TTSManager can fall back
    to SAPIReader.
    """

    playback_finished = pyqtSignal()
    error_occurred = pyqtSignal(str)

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
        self._player = QMediaPlayer()
        self._audio_output = QAudioOutput()
        self._player.setAudioOutput(self._audio_output)
        self._audio_output.setVolume(1.0)
        self._buffer = None  # type: QByteArray | None

        self._network.finished.connect(self._on_reply_finished)
        self._player.playbackStateChanged.connect(self._on_state_changed)
        logger.info("MiniMaxReader: initialized with voice_id=%s", voice_id)

    def _speak_impl(self, text: str) -> None:
        if not self._api_key:
            logger.error("MiniMaxReader._speak_impl: api_key is empty")
            self.error_occurred.emit("MiniMax API key is empty")
            return

        logger.info("MiniMaxReader._speak_impl: sending TTS request for text=%r", text[:50])

        request = QNetworkRequest(QUrl(self._ENDPOINT))
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
        self._network.post(request, body)

    def _on_reply_finished(self, reply: QNetworkReply) -> None:
        status_code = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
        logger.info("MiniMaxReader._on_reply_finished: HTTP status=%s", status_code)

        if reply.error() != QNetworkReply.NetworkError.NoError:
            err_msg = f"MiniMax network error: {reply.errorString()}"
            logger.error("MiniMaxReader._on_reply_finished: %s", err_msg)
            self.error_occurred.emit(err_msg)
            reply.deleteLater()
            return

        data = reply.readAll()
        if data.isEmpty():
            logger.error("MiniMaxReader._on_reply_finished: empty response")
            self.error_occurred.emit("MiniMax returned empty response")
            reply.deleteLater()
            return

        try:
            response_text = bytes(data).decode("utf-8")
            logger.debug("MiniMaxReader._on_reply_finished: response=%s", response_text[:500])
            response_json = json.loads(response_text)
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            logger.error("MiniMaxReader._on_reply_finished: failed to parse response: %s", e)
            self.error_occurred.emit(f"MiniMax response parse error: {e}")
            reply.deleteLater()
            return

        # Check base_resp for API errors
        base_resp = response_json.get("base_resp", {})
        status_code_api = base_resp.get("status_code", 0)
        if status_code_api != 0:
            status_msg = base_resp.get("status_msg", "unknown error")
            err_msg = f"MiniMax API error {status_code_api}: {status_msg}"
            logger.error("MiniMaxReader._on_reply_finished: %s", err_msg)
            self.error_occurred.emit(err_msg)
            reply.deleteLater()
            return

        # Extract hex-encoded audio
        audio_hex = response_json.get("data", {}).get("audio", "")
        if not audio_hex:
            logger.error("MiniMaxReader._on_reply_finished: no audio in response")
            self.error_occurred.emit("MiniMax returned no audio data")
            reply.deleteLater()
            return

        try:
            audio_bytes = binascii.unhexlify(audio_hex)
            logger.info("MiniMaxReader._on_reply_finished: decoded %d bytes of audio", len(audio_bytes))
        except binascii.Error as e:
            logger.error("MiniMaxReader._on_reply_finished: failed to decode audio hex: %s", e)
            self.error_occurred.emit(f"MiniMax audio decode error: {e}")
            reply.deleteLater()
            return

        self._buffer = QByteArray(audio_bytes)
        fd, path = tempfile.mkstemp(suffix=".mp3")
        try:
            os.write(fd, self._buffer.data())
        finally:
            os.close(fd)
        logger.debug("MiniMaxReader._on_reply_finished: saved audio to %s", path)
        self._player.setSource(QUrl.fromLocalFile(path))
        self._player.play()
        reply.deleteLater()

    def _on_state_changed(self, state) -> None:
        from PyQt6.QtMultimedia import QMediaPlayer as _QMP
        if state == _QMP.PlaybackState.StoppedState:
            logger.debug("MiniMaxReader._on_state_changed: playback stopped")
            self.playback_finished.emit()
            source = self._player.source()
            if source.isLocalFile():
                try:
                    os.remove(source.toLocalFile())
                except OSError:
                    pass
