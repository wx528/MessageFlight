"""Speech-to-text via MiniMax ASR cloud API.

Provides:
- ``STTReader``: abstract base defining the ``transcribe(audio_bytes)`` interface
- ``MiniMaxSTTReader``: concrete implementation that POSTs raw PCM
  audio to the MiniMax ASR endpoint and emits the transcribed text
  via the ``transcribed`` signal.

Mirrors the TTS module's pattern (base class + concrete subclass
that uses QNetworkAccessManager for async HTTP).
"""
from __future__ import annotations

import json
import logging
from abc import ABCMeta, abstractmethod
from typing import Optional

from PyQt6 import QtNetwork
from PyQt6.QtCore import QObject, QUrl, pyqtSignal
from PyQt6.sip import wrappertype

logger = logging.getLogger(__name__)


class _STTReaderMeta(wrappertype, ABCMeta):
    """Metaclass that resolves the conflict between QObject's metaclass
    and :class:`ABCMeta` so concrete subclasses can multiply inherit
    ``STTReader`` and ``QObject`` cleanly."""


class STTReader(metaclass=_STTReaderMeta):
    """Abstract base for STT providers.

    Subclasses must implement ``transcribe(audio_bytes)`` and emit
    ``transcribed(text, audio)`` on success or ``error_occurred(msg, audio)``
    on failure. The base class itself is a mixin (no state) and does
    not need to be initialised.
    """

    @abstractmethod
    def transcribe(self, audio_bytes: bytes) -> None:
        """Asynchronously transcribe *audio_bytes*. Override in subclasses."""


class MiniMaxSTTReader(STTReader, QObject):
    """Calls the MiniMax ASR endpoint with raw 16kHz mono PCM audio.

    Signals:
        transcribed(text, audio_bytes): Emitted with the recognized text
            and the original audio on success.
        error_occurred(error_msg, audio_bytes): Emitted with a human-readable
            error and the original audio on any failure. The audio is
            included so the caller can decide whether to retry.
    """

    transcribed = pyqtSignal(str, bytes)
    error_occurred = pyqtSignal(str, bytes)

    _ENDPOINT = "https://api.minimaxi.com/v1/asr"
    _TIMEOUT_MS = 10000
    _SAMPLE_RATE = 16000

    def __init__(
        self,
        api_key: str = "",
        model: str = "whisper-1",
        parent: Optional[QObject] = None,
    ):
        QObject.__init__(self, parent)
        self._api_key = api_key
        self._model = model
        self._network = QtNetwork.QNetworkAccessManager()
        self._reply_audio_map: dict[int, bytes] = {}  # id(reply) -> audio
        self._network.finished.connect(self._on_reply_finished)

    def set_api_key(self, api_key: str) -> None:
        self._api_key = api_key

    def transcribe(self, audio_bytes: bytes) -> None:
        """Send *audio_bytes* (16kHz mono PCM) to MiniMax ASR."""
        if not self._api_key:
            logger.error("MiniMaxSTTReader.transcribe: api_key is empty")
            self.error_occurred.emit("MiniMax API key is empty", audio_bytes)
            return

        if not audio_bytes:
            logger.error("MiniMaxSTTReader.transcribe: empty audio")
            self.error_occurred.emit("empty audio", audio_bytes)
            return

        request = QtNetwork.QNetworkRequest(QUrl(self._ENDPOINT))
        request.setTransferTimeout(self._TIMEOUT_MS)
        request.setHeader(
            QtNetwork.QNetworkRequest.KnownHeaders.ContentTypeHeader,
            "audio/pcm",
        )
        request.setRawHeader(b"Authorization", f"Bearer {self._api_key}".encode())
        request.setRawHeader(b"X-Model", self._model.encode())

        reply = self._network.post(request, audio_bytes)
        self._reply_audio_map[id(reply)] = audio_bytes
        logger.info("MiniMaxSTTReader.transcribe: posted %d bytes", len(audio_bytes))

    def _on_reply_finished(self, reply: QtNetwork.QNetworkReply) -> None:
        original_audio = self._reply_audio_map.pop(id(reply), b"")

        if reply.error() != QtNetwork.QNetworkReply.NetworkError.NoError:
            err_msg = f"MiniMax ASR network error: {reply.errorString()}"
            logger.error("MiniMaxSTTReader._on_reply_finished: %s", err_msg)
            self.error_occurred.emit(err_msg, original_audio)
            reply.deleteLater()
            return

        status_code = reply.attribute(QtNetwork.QNetworkRequest.Attribute.HttpStatusCodeAttribute)
        if status_code != 200:
            err_msg = f"MiniMax ASR HTTP {status_code}: {reply.errorString()}"
            logger.error("MiniMaxSTTReader._on_reply_finished: %s", err_msg)
            self.error_occurred.emit(err_msg, original_audio)
            reply.deleteLater()
            return

        data = reply.readAll()
        raw_bytes = bytes(data.data()) if data.data() else b""
        if not raw_bytes:
            err_msg = "MiniMax ASR returned empty body"
            logger.error("MiniMaxSTTReader._on_reply_finished: %s", err_msg)
            self.error_occurred.emit(err_msg, original_audio)
            reply.deleteLater()
            return

        try:
            response_text = raw_bytes.decode("utf-8")
            response_json = json.loads(response_text)
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            err_msg = f"MiniMax ASR response parse error: {e}"
            logger.error("MiniMaxSTTReader._on_reply_finished: %s", err_msg)
            self.error_occurred.emit(err_msg, original_audio)
            reply.deleteLater()
            return

        text = response_json.get("text", "").strip()
        if not text:
            err_msg = "MiniMax ASR returned empty text"
            logger.error("MiniMaxSTTReader._on_reply_finished: %s", err_msg)
            self.error_occurred.emit(err_msg, original_audio)
            reply.deleteLater()
            return

        logger.info("MiniMaxSTTReader._on_reply_finished: text=%r", text[:80])
        self.transcribed.emit(text, original_audio)
        reply.deleteLater()
