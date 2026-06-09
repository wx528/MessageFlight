"""TTS provider manager with automatic fallback."""
from __future__ import annotations

import sys

from PyQt6.QtCore import QObject, pyqtSignal

from message_flight.config import AppConfig, VALID_TTS_PROVIDERS
from message_flight.tts import MiniMaxReader, SAPIReader, TTSReader


class TTSManager(QObject):
    """Manages TTS providers and handles automatic fallback.

    Usage:
        mgr = TTSManager(config)
        mgr.speak("notification text")

    On MiniMax error, automatically falls back to SAPIReader.
    """

    provider_changed = pyqtSignal(str)
    fallback_triggered = pyqtSignal(str)

    def __init__(self, config: AppConfig, parent: QObject | None = None):
        super().__init__(parent)
        self._config = config
        self._current_provider_name = config.tts_provider
        self._providers: dict[str, TTSReader] = {}
        self._last_message = ""
        self._init_providers()

    def _init_providers(self) -> None:
        """Initialize all known providers."""
        self._providers["sapi"] = SAPIReader(
            enabled=True,
            title_template="您有新消息了。{message}",
        )
        self._providers["minimax"] = MiniMaxReader(
            api_key=self._config.minimax_api_key,
            enabled=True,
            title_template="您有新消息了。{message}",
        )
        # Connect MiniMax error signal to fallback handler
        minimax = self._providers.get("minimax")
        if isinstance(minimax, MiniMaxReader):
            minimax.error_occurred.connect(self._on_minimax_error)

    def speak(self, message: str) -> None:
        """Speak a message using the current provider."""
        self._last_message = message
        provider = self._providers.get(self._current_provider_name)
        if provider is None:
            print(f"TTSManager: unknown provider {self._current_provider_name!r}, falling back to sapi", file=sys.stderr)
            provider = self._providers.get("sapi")
        if provider is not None:
            provider.speak(message)

    def update_config(self, config: AppConfig) -> None:
        """Hot-update configuration (e.g. after settings dialog)."""
        self._config = config
        old_provider = self._current_provider_name
        self._current_provider_name = config.tts_provider

        # Update MiniMaxReader API key if changed
        minimax = self._providers.get("minimax")
        if isinstance(minimax, MiniMaxReader):
            minimax._api_key = config.minimax_api_key

        if old_provider != self._current_provider_name:
            self.provider_changed.emit(self._current_provider_name)

    def _on_minimax_error(self, error_msg: str) -> None:
        """Handle MiniMax error by falling back to SAPI."""
        print(f"TTSManager: MiniMax failed ({error_msg}), falling back to SAPI", file=sys.stderr)
        self.fallback_triggered.emit(error_msg)
        sapi = self._providers.get("sapi")
        if sapi is not None and self._last_message:
            sapi.speak(self._last_message)
