"""Local wake word detection via openwakeword + sounddevice.

The listener runs an openwakeword model on a 16kHz mono mic stream in
a background QThread. When the wake word is detected, ``wake_word_detected``
is emitted. ``pause()`` / ``resume()`` let the STTManager temporarily
mute the listener while a command is being captured.

The model is loaded once in ``__init__``; the mic stream is opened
on ``start()`` and closed on ``stop()``. All exceptions inside the
audio callback are caught and logged - they must NOT terminate the
background thread.
"""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Any, Optional

from PyQt6.QtCore import QObject, QStandardPaths, pyqtSignal

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = "int16"
BLOCK_SIZE = 1280

# Built-in wake word model names supported by openwakeword out-of-the-box.
BUILTIN_WAKE_WORDS = {"hey_jarvis", "alexa", "hey_mycroft"}

# Custom (Chinese) wake word models. Each entry maps a model key to its
# download URL. On first use the ONNX file is downloaded to the app's
# cache directory and loaded from there on subsequent runs.
CUSTOM_WAKE_WORD_MODELS: dict[str, dict[str, str]] = {
    "ni_hao_xiao_zhi": {
        "label_zh": "你好小智",
        "label_en": "Ni Hao Xiao Zhi",
        "url": "https://github.com/wx528/MessageFlight/releases/download/wakeword-models/ni_hao_xiao_zhi.onnx",
    },
    "ni_hao_xiao_fei": {
        "label_zh": "你好小飞",
        "label_en": "Ni Hao Xiao Fei",
        "url": "https://github.com/wx528/MessageFlight/releases/download/wakeword-models/ni_hao_xiao_fei.onnx",
    },
    "xiao_fei_xiao_fei": {
        "label_zh": "小飞小飞",
        "label_en": "Xiao Fei Xiao Fei",
        "url": "https://github.com/wx528/MessageFlight/releases/download/wakeword-models/xiao_fei_xiao_fei.onnx",
    },
}


def _get_wake_word_cache_dir() -> Path:
    """Return the directory used to cache custom wake word ONNX models."""
    cache_root = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.CacheLocation)
    d = Path(cache_root) / "MessageFlight" / "wakewords"
    d.mkdir(parents=True, exist_ok=True)
    return d


def ensure_custom_model(model_key: str) -> str:
    """Download a custom wake word model if not already cached.

    Returns the local file path of the ONNX model.
    Raises ``WakeWordInitError`` if the download fails.
    """
    meta = CUSTOM_WAKE_WORD_MODELS.get(model_key)
    if meta is None:
        raise WakeWordInitError(f"unknown custom wake word model: {model_key!r}")

    cache_dir = _get_wake_word_cache_dir()
    local_path = cache_dir / f"{model_key}.onnx"

    if local_path.exists() and local_path.stat().st_size > 0:
        logger.info("ensure_custom_model: %s already cached at %s", model_key, local_path)
        return str(local_path)

    url = meta["url"]
    logger.info("ensure_custom_model: downloading %s from %s ...", model_key, url)
    try:
        from urllib.request import urlopen

        with urlopen(url, timeout=60) as resp:
            data = resp.read()
        tmp_path = local_path.with_suffix(".onnx.download")
        tmp_path.write_bytes(data)
        tmp_path.rename(local_path)
        logger.info("ensure_custom_model: saved %s (%d bytes)", local_path, len(data))
    except Exception as e:
        # Clean up partial download
        tmp_path = local_path.with_suffix(".onnx.download")
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        raise WakeWordInitError(
            f"failed to download custom wake word model {model_key!r}: {e}"
        ) from e

    return str(local_path)


class WakeWordInitError(RuntimeError):
    """Raised when the wake word model cannot be loaded."""


class _AudioWorker(QObject):
    """QObject that processes mic frames via the wake-word model."""

    frame_received = pyqtSignal(object, int)
    audio_frame = pyqtSignal(object)

    def __init__(self, model, threshold: float = 0.5, debounce_seconds: float = 1.0):
        super().__init__()
        self._model = model
        self._threshold = threshold
        self._debounce_seconds = debounce_seconds
        self._last_detect_at: float = 0.0
        self._paused = False

    def set_paused(self, paused: bool) -> None:
        self._paused = paused

    def process_frame(self, indata, frames: int, _time, _status) -> None:
        self.audio_frame.emit(bytes(indata))

        if self._paused:
            return
        try:
            predictions = self._model.predict(indata.flatten())
        except Exception as e:
            logger.debug("wake word predict error: %s", e)
            return

        for _label, score in predictions.items():
            if score >= self._threshold:
                now = time.monotonic()
                if now - self._last_detect_at < self._debounce_seconds:
                    return
                self._last_detect_at = now
                self.frame_received.emit(indata, frames)
                return


class OpenWakeWordListener(QObject):
    """Listen for a wake word on the default microphone.

    Signals:
        wake_word_detected: Emitted when the wake word fires.
        error_occurred(message): Emitted on mic or model errors.
        audio_frame(bytes): Emitted every ~80ms with raw int16 PCM
            (1280 samples = 2560 bytes). Continues to fire even while
            the listener is paused so downstream STT consumers can buffer
            the user's command audio.
    """

    wake_word_detected = pyqtSignal()
    error_occurred = pyqtSignal(str)
    audio_frame = pyqtSignal(object)

    def __init__(
        self,
        model_name: str = "hey_jarvis",
        sensitivity: float = 0.5,
        debounce_seconds: float = 1.0,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._model_name = model_name
        self._sensitivity = sensitivity
        self._debounce_seconds = debounce_seconds

        try:
            import os as _os

            import openwakeword  # type: ignore[import-untyped]
            from openwakeword.model import Model  # type: ignore[import-untyped]
            from openwakeword.utils import download_models  # type: ignore[import-untyped]

            # Resolve model path: built-in names are passed directly;
            # custom models are downloaded to cache on first use.
            if model_name in BUILTIN_WAKE_WORDS:
                model_path = model_name
                # Auto-download pretrained models on first use (tflite+onnx variants).
                _any_missing = any(
                    not _os.path.exists(p["model_path"])
                    and not _os.path.exists(p["model_path"].replace(".tflite", ".onnx"))
                    for p in openwakeword.MODELS.values()
                )
                if _any_missing:
                    logger.info("OpenWakeWordListener: downloading pretrained models on first use...")
                    download_models()
            elif model_name in CUSTOM_WAKE_WORD_MODELS:
                model_path = ensure_custom_model(model_name)
                logger.info("OpenWakeWordListener: using custom model %s from %s", model_name, model_path)
            else:
                # Treat as a file path (power-user override)
                model_path = model_name

            self._model = Model(
                wakeword_models=[model_path],
                inference_framework="onnx",
            )
        except Exception as e:
            logger.error("OpenWakeWordListener: failed to load model %r: %s", model_name, e)
            raise WakeWordInitError(f"failed to load model {model_name!r}: {e}") from e

        self._worker = _AudioWorker(self._model, threshold=sensitivity, debounce_seconds=debounce_seconds)
        self._worker.frame_received.connect(self._on_frame_received)
        self._worker.audio_frame.connect(self.audio_frame)

        self._stream: Optional[Any] = None
        self._is_running = False
        self._is_paused = False

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def is_paused(self) -> bool:
        return self._is_paused

    def start(self) -> None:
        if self._is_running:
            return
        self._is_paused = False
        if self._worker is not None:  # always true, but defensive
            self._worker.set_paused(False)
        try:
            import sounddevice as sd  # type: ignore[import-untyped]

            self._stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype=DTYPE,
                blocksize=BLOCK_SIZE,
                callback=self._worker.process_frame,
            )
            self._stream.start()
            self._is_running = True
            logger.info("OpenWakeWordListener: started (model=%s)", self._model_name)
        except Exception as e:
            logger.error("OpenWakeWordListener: failed to open mic: %s", e)
            self.error_occurred.emit(f"microphone unavailable: {e}")
            self._stream = None

    def pause(self) -> None:
        self._is_paused = True
        self._worker.set_paused(True)

    def resume(self) -> None:
        self._is_paused = False
        self._worker.set_paused(False)

    def stop(self) -> None:
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as e:
                logger.debug("OpenWakeWordListener: error closing stream: %s", e)
            self._stream = None
        self._is_running = False
        self._is_paused = False
        logger.info("OpenWakeWordListener: stopped")

    def _on_frame_received(self, _indata, _frames) -> None:
        logger.info("OpenWakeWordListener: wake word detected (model=%s)", self._model_name)
        self.wake_word_detected.emit()
