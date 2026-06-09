"""Text-to-speech notification reader.

Provides ``TTSReader`` abstract base class and two concrete implementations:
- ``SAPIReader``  – Windows SAPI via pywin32 (falls back to no-op if unavailable)
- ``MiniMaxReader`` – MiniMax online TTS engine via Qt async network + media player
"""
from __future__ import annotations

import sys

from PyQt6.QtCore import QByteArray, QObject, QUrl, pyqtSignal
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest


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
            return
        try:
            text = self._title_template.replace("{message}", message)
        except Exception as e:
            print(f"TTS format error: {e}", file=sys.stderr)
            return
        try:
            self._speak_impl(text)
        except Exception as e:
            print(f"TTS speak error: {e}", file=sys.stderr)

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
            self._enabled = False
            return
        try:
            import win32com.client

            self._speaker = win32com.client.Dispatch("SAPI.SpVoice")
        except Exception:
            self._enabled = False

    def _speak_impl(self, text: str) -> None:
        self._speaker.Speak(text)


class MiniMaxReader(TTSReader, QObject):
    """MiniMax TTS via QNetworkAccessManager + QMediaPlayer.

    Asynchronously calls the MiniMax API and plays the returned MP3.
    On any error, emits ``error_occurred`` so TTSManager can fall back
    to SAPIReader.
    """

    playback_finished = pyqtSignal()
    error_occurred = pyqtSignal(str)

    _ENDPOINT = "https://api.minimax.chat/v1/tts"
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
        self._buffer = None  # type: QByteArray | None

        self._network.finished.connect(self._on_reply_finished)
        self._player.playbackStateChanged.connect(self._on_state_changed)

    def _speak_impl(self, text: str) -> None:
        if not self._api_key:
            self.error_occurred.emit("MiniMax API key is empty")
            return

        request = QNetworkRequest(QUrl(self._ENDPOINT))
        request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json")
        request.setRawHeader(b"Authorization", f"Bearer {self._api_key}".encode())

        payload = {
            "text": text,
            "voice_id": self._voice_id,
            "speed": self._speed,
            "vol": self._vol,
            "pitch": 0,
        }
        import json
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._network.post(request, body)

    def _on_reply_finished(self, reply: QNetworkReply) -> None:
        if reply.error() != QNetworkReply.NetworkError.NoError:
            self.error_occurred.emit(f"MiniMax network error: {reply.errorString()}")
            reply.deleteLater()
            return

        data = reply.readAll()
        if data.isEmpty():
            self.error_occurred.emit("MiniMax returned empty audio")
            reply.deleteLater()
            return

        self._buffer = QByteArray(data)
        import tempfile
        import os
        fd, path = tempfile.mkstemp(suffix=".mp3")
        try:
            os.write(fd, self._buffer.data())
        finally:
            os.close(fd)
        self._player.setSource(QUrl.fromLocalFile(path))
        self._player.play()
        reply.deleteLater()

    def _on_state_changed(self, state) -> None:
        from PyQt6.QtMultimedia import QMediaPlayer as _QMP
        if state == _QMP.PlaybackState.StoppedState:
            self.playback_finished.emit()
            source = self._player.source()
            if source.isLocalFile():
                import os
                try:
                    os.remove(source.toLocalFile())
                except OSError:
                    pass
