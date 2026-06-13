"""Local wake word detection via openwakeword or sherpa-onnx + sounddevice.

Two backends are supported:

- **openwakeword** (default for English wake words like "hey_jarvis"):
  Uses pre-trained ONNX models. Limited Chinese support.

- **sherpa-onnx** (recommended for Chinese wake words):
  Uses zipformer transducer models with pinyin-based keyword spotting.
  No training needed — just add keywords in a text file. Supports both
  Chinese and English in a single model (zh-en model, ~3MB).

The listener runs on a 16kHz mono mic stream. When the wake word is
detected, ``wake_word_detected`` is emitted. ``pause()`` / ``resume()``
let the STTManager temporarily mute the listener while a command is
being captured.

The model is loaded once in ``__init__``; the mic stream is opened
on ``start()`` and closed on ``stop()``. All exceptions inside the
audio callback are caught and logged — they must NOT terminate the
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
BLOCK_SIZE = 1280  # 80ms at 16kHz

# ---------------------------------------------------------------------------
# Wake word registry
# ---------------------------------------------------------------------------

# Built-in wake word model names supported by openwakeword out-of-the-box.
BUILTIN_WAKE_WORDS = {"hey_jarvis", "alexa", "hey_mycroft"}

# Sherpa-ONNX Chinese wake words. These use the zh-en zipformer model
# with pinyin-based keyword spotting — no training needed.
SHERPA_WAKE_WORDS: dict[str, dict[str, str]] = {
    "ni_hao_xiao_zhi": {
        "label_zh": "你好小智",
        "label_en": "Ni Hao Xiao Zhi",
        "pinyin": "n ǐ h ǎo x iǎo zh ì",
    },
    "ni_hao_xiao_fei": {
        "label_zh": "你好小飞",
        "label_en": "Ni Hao Xiao Fei",
        "pinyin": "n ǐ h ǎo x iǎo f ēi",
    },
    "xiao_fei_xiao_fei": {
        "label_zh": "小飞小飞",
        "label_en": "Xiao Fei Xiao Fei",
        "pinyin": "x iǎo f ēi x iǎo f ēi",
    },
    "ni_hao": {
        "label_zh": "你好",
        "label_en": "Ni Hao",
        "pinyin": "n ǐ h ǎo",
    },
    "xiao_ai_tong_xue": {
        "label_zh": "小爱同学",
        "label_en": "Xiao Ai Tong Xue",
        "pinyin": "x iǎo ài t óng x ué",
    },
}

# All available wake word keys (for UI combo box)
ALL_WAKE_WORDS = list(BUILTIN_WAKE_WORDS) + list(SHERPA_WAKE_WORDS.keys())

# ---------------------------------------------------------------------------
# Model download / cache helpers
# ---------------------------------------------------------------------------

# Sherpa-ONNX zh-en KWS model download URL
SHERPA_ZH_EN_MODEL_URL = (
    "https://github.com/k2-fsa/sherpa-onnx/releases/download/"
    "kws-models/sherpa-onnx-kws-zipformer-zh-en-3M-2025-12-20.tar.bz2"
)
SHERPA_MODEL_DIR_NAME = "sherpa-onnx-kws-zipformer-zh-en-3M-2025-12-20"


class WakeWordInitError(RuntimeError):
    """Raised when the wake word model cannot be loaded."""


def _get_wake_word_cache_dir() -> Path:
    """Return the directory used to cache wake word models."""
    cache_root = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.CacheLocation)
    d = Path(cache_root) / "MessageFlight" / "wakewords"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _ensure_sherpa_model() -> Path:
    """Download the sherpa-onnx zh-en KWS model if not already cached.

    Returns the path to the extracted model directory.
    Raises ``WakeWordInitError`` if the download fails.
    """
    cache_dir = _get_wake_word_cache_dir()
    model_dir = cache_dir / SHERPA_MODEL_DIR_NAME

    # Check if model already exists and has the required files
    required_files = ["tokens.txt", "encoder-epoch-13-avg-2-chunk-16-left-64.onnx",
                      "decoder-epoch-13-avg-2-chunk-16-left-64.onnx",
                      "joiner-epoch-13-avg-2-chunk-16-left-64.onnx"]
    if all((model_dir / f).exists() for f in required_files):
        logger.info("_ensure_sherpa_model: model already cached at %s", model_dir)
        return model_dir

    logger.info("_ensure_sherpa_model: downloading sherpa-onnx zh-en model ...")
    try:
        import tarfile
        from urllib.request import urlopen

        url = SHERPA_ZH_EN_MODEL_URL
        archive_name = url.rsplit("/", 1)[-1]
        archive_path = cache_dir / archive_name

        # Download
        with urlopen(url, timeout=120) as resp:
            data = resp.read()
        tmp_path = archive_path.with_suffix(".download")
        tmp_path.write_bytes(data)
        tmp_path.rename(archive_path)
        logger.info("_ensure_sherpa_model: downloaded %s (%d bytes)", archive_name, len(data))

        # Extract
        with tarfile.open(archive_path, "r:bz2") as tar:
            tar.extractall(path=cache_dir)
        logger.info("_ensure_sherpa_model: extracted to %s", model_dir)

        # Clean up archive
        archive_path.unlink(missing_ok=True)

    except Exception as e:
        # Clean up partial download
        tmp_path = cache_dir / (SHERPA_MODEL_DIR_NAME + ".tar.bz2.download")
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        raise WakeWordInitError(
            f"failed to download sherpa-onnx model: {e}"
        ) from e

    return model_dir


def _build_sherpa_keywords_file(wake_word_key: str, model_dir: Path) -> Path:
    """Build a keywords.txt file for sherpa-onnx from the wake word registry.

    Returns the path to the generated keywords file.
    """
    meta = SHERPA_WAKE_WORDS.get(wake_word_key)
    if meta is None:
        raise WakeWordInitError(f"unknown sherpa wake word: {wake_word_key!r}")

    cache_dir = _get_wake_word_cache_dir()
    keywords_path = cache_dir / f"keywords_{wake_word_key}.txt"
    label = meta["label_zh"]
    pinyin = meta["pinyin"]
    keywords_path.write_text(f"{pinyin} @{label}\n", encoding="utf-8")
    logger.info("_build_sherpa_keywords_file: wrote %s", keywords_path)
    return keywords_path


# ---------------------------------------------------------------------------
# OpenWakeWord backend (English)
# ---------------------------------------------------------------------------


class _OwwAudioWorker(QObject):
    """QObject that processes mic frames via the openwakeword model."""

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
    """Listen for a wake word using openwakeword (English models).

    Signals:
        wake_word_detected: Emitted when the wake word fires.
        error_occurred(message): Emitted on mic or model errors.
        audio_frame(bytes): Emitted every ~80ms with raw int16 PCM.
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

            if model_name in BUILTIN_WAKE_WORDS:
                model_path = model_name
                _any_missing = any(
                    not _os.path.exists(p["model_path"])
                    and not _os.path.exists(p["model_path"].replace(".tflite", ".onnx"))
                    for p in openwakeword.MODELS.values()
                )
                if _any_missing:
                    logger.info("OpenWakeWordListener: downloading pretrained models on first use...")
                    download_models()
            else:
                model_path = model_name

            self._model = Model(
                wakeword_models=[model_path],
                inference_framework="onnx",
            )
        except Exception as e:
            logger.error("OpenWakeWordListener: failed to load model %r: %s", model_name, e)
            raise WakeWordInitError(f"failed to load model {model_name!r}: {e}") from e

        self._worker = _OwwAudioWorker(self._model, threshold=sensitivity, debounce_seconds=debounce_seconds)
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


# ---------------------------------------------------------------------------
# Sherpa-ONNX backend (Chinese + English)
# ---------------------------------------------------------------------------


class _SherpaAudioWorker(QObject):
    """QObject that processes mic frames via the sherpa-onnx KWS model."""

    frame_received = pyqtSignal()
    audio_frame = pyqtSignal(object)

    def __init__(self, kws, stream, debounce_seconds: float = 1.0):
        super().__init__()
        self._kws = kws
        self._stream = stream
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
            import numpy as np

            samples = indata.flatten().astype(np.float32) / 32768.0
            self._kws.accept_waveform(self._stream, samples)
            result = self._kws.get_result(self._stream)
            if result:
                now = time.monotonic()
                if now - self._last_detect_at < self._debounce_seconds:
                    return
                self._last_detect_at = now
                self.frame_received.emit()
        except Exception as e:
            logger.debug("sherpa-onnx KWS predict error: %s", e)


class SherpaOnnxListener(QObject):
    """Listen for a wake word using sherpa-onnx (Chinese + English).

    Uses the zipformer transducer KWS model with pinyin-based keyword
    spotting. No training needed — keywords are defined in a text file.

    Signals:
        wake_word_detected: Emitted when the wake word fires.
        error_occurred(message): Emitted on mic or model errors.
        audio_frame(bytes): Emitted every ~80ms with raw int16 PCM.
    """

    wake_word_detected = pyqtSignal()
    error_occurred = pyqtSignal(str)
    audio_frame = pyqtSignal(object)

    def __init__(
        self,
        wake_word_key: str = "ni_hao_xiao_zhi",
        sensitivity: float = 0.5,
        debounce_seconds: float = 1.0,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._wake_word_key = wake_word_key
        self._debounce_seconds = debounce_seconds

        try:
            import sherpa_onnx  # type: ignore[import-untyped]

            # Download model if needed
            model_dir = _ensure_sherpa_model()

            # Build keywords file
            keywords_path = _build_sherpa_keywords_file(wake_word_key, model_dir)

            # Map sensitivity (0-1) to keywords_threshold.
            # sherpa-onnx threshold is typically 0.1-0.5; higher = less sensitive.
            # We invert: high sensitivity → low threshold
            threshold = max(0.1, 0.5 - sensitivity * 0.4)

            self._kws = sherpa_onnx.KeywordSpotter(
                tokens=str(model_dir / "tokens.txt"),
                encoder=str(model_dir / "encoder-epoch-13-avg-2-chunk-16-left-64.onnx"),
                decoder=str(model_dir / "decoder-epoch-13-avg-2-chunk-16-left-64.onnx"),
                joiner=str(model_dir / "joiner-epoch-13-avg-2-chunk-16-left-64.onnx"),
                keywords_file=str(keywords_path),
                keywords_threshold=threshold,
                num_threads=1,
                provider="cpu",
            )
            self._stream = self._kws.create_stream()
            logger.info(
                "SherpaOnnxListener: model loaded (keyword=%s, threshold=%.2f)",
                wake_word_key, threshold,
            )
        except Exception as e:
            logger.error("SherpaOnnxListener: failed to init: %s", e)
            raise WakeWordInitError(f"failed to init sherpa-onnx: {e}") from e

        self._worker = _SherpaAudioWorker(
            self._kws, self._stream, debounce_seconds=debounce_seconds,
        )
        self._worker.frame_received.connect(self._on_frame_received)
        self._worker.audio_frame.connect(self.audio_frame)

        self._sd_stream: Optional[Any] = None
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
        self._worker.set_paused(False)

        # Reset the sherpa stream to clear stale state
        try:
            self._kws.reset_stream(self._stream)
        except Exception:
            pass

        try:
            import sounddevice as sd  # type: ignore[import-untyped]

            self._sd_stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype=DTYPE,
                blocksize=BLOCK_SIZE,
                callback=self._worker.process_frame,
            )
            self._sd_stream.start()
            self._is_running = True
            logger.info("SherpaOnnxListener: started (keyword=%s)", self._wake_word_key)
        except Exception as e:
            logger.error("SherpaOnnxListener: failed to open mic: %s", e)
            self.error_occurred.emit(f"microphone unavailable: {e}")
            self._sd_stream = None

    def pause(self) -> None:
        self._is_paused = True
        self._worker.set_paused(True)

    def resume(self) -> None:
        self._is_paused = False
        self._worker.set_paused(False)

    def stop(self) -> None:
        if self._sd_stream is not None:
            try:
                self._sd_stream.stop()
                self._sd_stream.close()
            except Exception as e:
                logger.debug("SherpaOnnxListener: error closing stream: %s", e)
            self._sd_stream = None
        self._is_running = False
        self._is_paused = False
        logger.info("SherpaOnnxListener: stopped")

    def _on_frame_received(self) -> None:
        logger.info("SherpaOnnxListener: wake word detected (keyword=%s)", self._wake_word_key)
        self.wake_word_detected.emit()


# ---------------------------------------------------------------------------
# Factory function
# ---------------------------------------------------------------------------


def create_listener(
    wake_word_key: str = "hey_jarvis",
    sensitivity: float = 0.5,
    debounce_seconds: float = 1.0,
    parent: Optional[QObject] = None,
) -> OpenWakeWordListener | SherpaOnnxListener:
    """Create the appropriate wake word listener for the given key.

    Uses ``OpenWakeWordListener`` for built-in English wake words and
    ``SherpaOnnxListener`` for Chinese wake words (and any custom key
    that is not a built-in openwakeword model name).
    """
    if wake_word_key in BUILTIN_WAKE_WORDS:
        logger.info("create_listener: using openwakeword for %s", wake_word_key)
        return OpenWakeWordListener(
            model_name=wake_word_key,
            sensitivity=sensitivity,
            debounce_seconds=debounce_seconds,
            parent=parent,
        )
    else:
        logger.info("create_listener: using sherpa-onnx for %s", wake_word_key)
        return SherpaOnnxListener(
            wake_word_key=wake_word_key,
            sensitivity=sensitivity,
            debounce_seconds=debounce_seconds,
            parent=parent,
        )
