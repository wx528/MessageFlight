from __future__ import annotations

import json
import logging
from typing import Optional

from PyQt6.QtCore import QObject, QTimer, QUrl, pyqtSignal
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

logger = logging.getLogger(__name__)


class PersonaRewriter(QObject):
    """Async rewriter that posts the original text to the MiniMax text
    completion endpoint and emits the rewritten text via
    :signal:`rewrite_finished`.

    On any error (no key, network failure, non-zero ``base_resp.status_code``,
    empty assistant content), the *original* text is emitted so the caller
    can keep its normal TTS + banner flow.
    """

    rewrite_finished = pyqtSignal(str)

    _ENDPOINT = "https://api.minimaxi.com/v1/text/chatcompletion_v2"
    _MODEL = "MiniMax-Text-01"
    _TIMEOUT_MS = 8000

    def __init__(
        self,
        api_key: str = "",
        preset_key: str = "airplane",
        system_prompt: str = "",
        enabled: bool = True,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._api_key = api_key
        self._preset_key = preset_key
        self._system_prompt = system_prompt
        self._enabled = enabled
        self._nam: Optional[QNetworkAccessManager] = None
        self._pending: dict[int, str] = {}

    def _make_nam(self) -> QNetworkAccessManager:
        return QNetworkAccessManager(self)

    def _get_nam(self) -> QNetworkAccessManager:
        if self._nam is None:
            self._nam = self._make_nam()
            self._nam.finished.connect(self._on_reply_finished)
        return self._nam

    def set_config(self, api_key: str, preset_key: str, system_prompt: str, enabled: bool) -> None:
        self._api_key = api_key
        self._preset_key = preset_key
        self._system_prompt = system_prompt
        self._enabled = enabled

    def rewrite(self, message: str) -> Optional[str]:
        """Schedule a rewrite.

        Returns the rewritten text synchronously only when the rewriter
        short-circuits (disabled / empty key / empty prompt / empty
        message). Otherwise returns ``None`` and the rewritten text
        arrives via :signal:`rewrite_finished`.
        """
        if not self._enabled or not self._api_key or not self._system_prompt or not message:
            return message

        request = QNetworkRequest(QUrl(self._ENDPOINT))
        request.setTransferTimeout(self._TIMEOUT_MS)
        request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json")
        request.setRawHeader(b"Authorization", f"Bearer {self._api_key}".encode())

        payload = {
            "model": self._MODEL,
            "messages": [
                {"role": "system", "content": self._system_prompt},
                {"role": "user", "content": message},
            ],
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        reply = self._get_nam().post(request, body)
        self._pending[id(reply)] = message
        if not isinstance(reply, QNetworkReply):
            QTimer.singleShot(0, lambda r=reply: self._on_reply_finished(r))
        return None

    def _on_reply_finished(self, reply: QNetworkReply) -> None:
        original = self._pending.pop(id(reply), "")
        if not original:
            reply.deleteLater()
            return
        if reply.error() != QNetworkReply.NetworkError.NoError:
            logger.warning("PersonaRewriter: network error %s", reply.errorString())
            self.rewrite_finished.emit(original)
            reply.deleteLater()
            return
        try:
            data = reply.readAll().data().decode("utf-8")
            response = json.loads(data)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            logger.warning("PersonaRewriter: parse error %s", exc)
            self.rewrite_finished.emit(original)
            reply.deleteLater()
            return
        if response.get("base_resp", {}).get("status_code", 0) != 0:
            logger.warning("PersonaRewriter: API error %s", response.get("base_resp"))
            self.rewrite_finished.emit(original)
            reply.deleteLater()
            return
        try:
            text = response["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError):
            logger.warning("PersonaRewriter: missing content in response")
            self.rewrite_finished.emit(original)
            reply.deleteLater()
            return
        if not text:
            self.rewrite_finished.emit(original)
        else:
            self.rewrite_finished.emit(text)
        reply.deleteLater()
