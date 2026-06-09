"""TTS provider manager with automatic fallback."""
from __future__ import annotations

import logging
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal

from message_flight.config import AppConfig, VALID_TTS_PROVIDERS
from message_flight.tts import MiniMaxReader, SAPIReader, TTSReader

logger = logging.getLogger(__name__)


class TTSManager(QObject):
    """Manages TTS providers and handles automatic fallback.

    Usage:
        mgr = TTSManager(config)
        mgr.speak("notification text")

    On MiniMax error, automatically falls back to SAPIReader.
    """

    provider_changed = pyqtSignal(str)
    fallback_triggered = pyqtSignal(str)

    def __init__(self, config: AppConfig, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._config = config
        self._current_provider_name = config.tts_provider
        logger.info("TTSManager: initialized with provider=%s", self._current_provider_name)
        self._providers: dict[str, TTSReader] = {}
        self._last_message = ""
        self._init_providers()

    def _init_providers(self) -> None:
        """Initialize all known providers."""
        self._providers["sapi"] = SAPIReader(
            enabled=True,
            title_template="您有新消息了。{message}",
        )
        key_preview = self._config.minimax_subscription_key[:8] + "..." if self._config.minimax_subscription_key else "(empty)"
        logger.info("TTSManager._init_providers: creating MiniMaxReader with key=%s", key_preview)
        self._providers["minimax"] = MiniMaxReader(
            api_key=self._config.minimax_subscription_key,
            enabled=True,
            title_template="您有新消息了。{message}",
        )
        # Connect MiniMax error signal to fallback handler
        minimax = self._providers.get("minimax")
        if isinstance(minimax, MiniMaxReader):
            minimax.error_occurred.connect(self._on_minimax_error)

    def speak(self, message: str) -> None:
        """Speak a message using the current provider."""
        logger.info("TTSManager.speak: provider=%s message=%r", self._current_provider_name, message[:50])
        self._last_message = message
        provider = self._providers.get(self._current_provider_name)
        if provider is None:
            logger.warning("TTSManager.speak: unknown provider %r, falling back to sapi", self._current_provider_name)
            provider = self._providers.get("sapi")
        if provider is not None:
            provider.speak(message)

    def update_config(self, config: AppConfig) -> None:
        """Hot-update configuration (e.g. after settings dialog)."""
        logger.info("TTSManager.update_config: provider=%s -> %s", self._current_provider_name, config.tts_provider)
        self._config = config
        old_provider = self._current_provider_name
        self._current_provider_name = config.tts_provider

        # Update MiniMaxReader API key if changed
        minimax = self._providers.get("minimax")
        if isinstance(minimax, MiniMaxReader):
            old_key = minimax._api_key[:8] + "..." if minimax._api_key else "(empty)"
            new_key = config.minimax_subscription_key[:8] + "..." if config.minimax_subscription_key else "(empty)"
            logger.info("TTSManager.update_config: updating MiniMax key %s -> %s", old_key, new_key)
            minimax._api_key = config.minimax_subscription_key

        if old_provider != self._current_provider_name:
            self.provider_changed.emit(self._current_provider_name)

    def _on_minimax_error(self, error_msg: str, original_text: str) -> None:
        """Handle MiniMax error by falling back to SAPI.

        Args:
            error_msg: Human-readable error description.
            original_text: The text that was supposed to be spoken;
                passed explicitly to avoid race conditions with
                rapid successive speak() calls.
        """
        logger.error("TTSManager: MiniMax failed (%s), falling back to SAPI", error_msg)
        self.fallback_triggered.emit(error_msg)
        sapi = self._providers.get("sapi")
        if sapi is not None and original_text:
            logger.info("TTSManager: falling back to SAPI for message=%r", original_text[:50])
            sapi.speak(original_text)
