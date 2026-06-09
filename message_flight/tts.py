"""Text-to-speech notification reader.

Provides ``TTSReader`` abstract base class and two concrete implementations:
- ``SAPIReader``  – Windows SAPI via pywin32 (falls back to no-op if unavailable)
- ``OnlineTTSReader`` – stub for future online engines (MiniMax / MeloTTS, etc.)
"""
from __future__ import annotations

import sys


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
            text = self._title_template.format(message=message)
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


class OnlineTTSReader(TTSReader):
    """Stub for online TTS engines (MiniMax / MeloTTS / etc.).

    Scheduled for implementation in v0.1.9.  All calls are currently no-ops.
    """

    def __init__(self, api_key: str = "", **kwargs):
        super().__init__(**kwargs)
        print("OnlineTTSReader: 在线 TTS 引擎将于 v0.1.9 支持")
        self._enabled = False
        self._api_key = api_key

    def _speak_impl(self, text: str) -> None:
        pass
