"""Persistent application config backed by QSettings.

Stores the user's selected color scheme and exposes three preset
schemes: ``default``, ``retro`` (green), and ``cyber`` (synthwave).

The file uses ``QSettings.Format.IniFormat`` for portability and
inspectability on Windows (the default backend is the registry, which
is harder for users to find and edit by hand).
"""
from __future__ import annotations

import contextlib
import datetime
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from PyQt6.QtCore import QSettings

from message_flight.i18n import detect_system_language, normalize_language

ORG = "MessageFlight"
APP = "MessageFlight"
SETTINGS_KEY = "color_scheme"
FLIGHT_KWARG_KEY = "flight_kwargs_json"
FLIGHT_MODE_KEY = "flight_mode"
MINIMAX_SUBSCRIPTION_KEY = "minimax_subscription_key"
LANGUAGE_KEY = "language"
PLANE_PRESET_KEY = "plane_preset_key"
PLANE_PRESET_PARAMS_JSON_KEY = "plane_preset_params_json"

# Do-Not-Disturb configuration.
DND_ENABLED_KEY = "dnd_enabled"
DND_SCHEDULE_ENABLED_KEY = "dnd_schedule_enabled"
DND_SCHEDULE_START_KEY = "dnd_schedule_start"
DND_SCHEDULE_END_KEY = "dnd_schedule_end"

TTS_PROVIDER_KEY = "tts_provider"
DEFAULT_TTS_PROVIDER = "sapi"
VALID_TTS_PROVIDERS = ("sapi", "minimax")

# AI persona feature
PERSONA_ENABLED_KEY = "persona_enabled"
PERSONA_PROMPTS_JSON_KEY = "persona_prompts_json"

# Voice input (v0.4.0+)
STT_ENABLED_KEY = "stt_enabled"
STT_WAKE_WORD_KEY = "stt_wake_word"

# Gamification (v0.2.7+)
UNLOCKED_PRESETS_KEY = "unlocked_presets"
ACHIEVEMENT_PROGRESS_KEY = "achievement_progress"
DISTINCT_SOURCES_KEY = "distinct_notification_sources"
PRESETS_USED_KEY = "presets_used"
CLICKS_KEY = "clicks"
TTS_COUNT_KEY = "tts_count"

# User-facing flight paths.  ``horizontal`` is the classic left-to-right
# sweep; ``vertical_pong`` enters from the top and bounces off the top
# and bottom edges while drifting right.
VALID_FLY_PATHS: tuple[str, ...] = (
    "horizontal",
    "vertical_pong",
    "zigzag_top_down",
    "zigzag_bottom_up",
    "around",
)

THEMES: dict[str, dict[str, str]] = {
    "default": {
        "plane_color": "#FF69B4",
        "wing_color": "#FF1493",
        "accent_color": "#FFFFFF",
        "decor_color": "#FF69B4",
        "banner_color": "#FFB6C1",
        "text_color": "#FFFFFF",
        "thruster_outer_color": "#FFA500",
        "thruster_middle_color": "#FF4500",
        "thruster_inner_color": "#FFFF00",
    },
    "retro": {
        "plane_color": "#4F7942",
        "wing_color": "#2E4A2E",
        "accent_color": "#FFFFFF",
        "decor_color": "#4F7942",
        "banner_color": "#90EE90",
        "text_color": "#FFFFFF",
        "thruster_outer_color": "#FFD700",
        "thruster_middle_color": "#FF8C00",
        "thruster_inner_color": "#FFEB3B",
    },
    "cyber": {
        "plane_color": "#00FFFF",
        "wing_color": "#FF00FF",
        "accent_color": "#FFFFFF",
        "decor_color": "#00FFFF",
        "banner_color": "#0A0A2A",
        "text_color": "#00FF00",
        "thruster_outer_color": "#FF00FF",
        "thruster_middle_color": "#9D00FF",
        "thruster_inner_color": "#FFFFFF",
    },
}

DEFAULT_THEME = "default"


@dataclass
class FlightModeConfig:
    """A set of flight-behavior parameters.

    A flight mode preset lets the user switch the in-flight tuning
    knobs in one click. The ``flight_kwargs`` dict is forwarded as
    keyword arguments to :class:`FlightWidget`.
    """

    flight_kwargs: dict[str, Any]


# The 7 flight-behavior kwargs the 3 presets expose to FlightWidget.
# Any key outside this set is rejected by ``validate_flight_kwargs``.
VALID_FLIGHT_KWARG_KEYS: tuple[str, ...] = (
    "fly_bounce",
    "fly_loop_count",
    "fly_path",
    "fly_duration_ms",
    "float_duration_ms",
    "vertical_jitter",
    "notification_interval_ms",
)

# The 3 named flight modes. Each is a plain dict of flight-behavior kwargs.
# Values copied verbatim from the design spec.
FLIGHT_MODES: dict[str, dict[str, Any]] = {
    "低调": {
        "fly_bounce": False,
        "fly_loop_count": 1,
        "fly_path": "horizontal",
        "fly_duration_ms": 12000,
        "float_duration_ms": 1500,
        "vertical_jitter": 30,
        "notification_interval_ms": 8000,
    },
    "标准": {
        "fly_bounce": False,
        "fly_loop_count": -1,
        "fly_path": "horizontal",
        "fly_duration_ms": 8000,
        "float_duration_ms": 1500,
        "vertical_jitter": 100,
        "notification_interval_ms": 5000,
    },
    "胡闹": {
        "fly_bounce": True,
        "fly_loop_count": -1,
        "fly_path": "horizontal",
        "fly_duration_ms": 7000,
        "float_duration_ms": 1500,
        "vertical_jitter": 200,
        "notification_interval_ms": 2000,
    },
}

# User-facing order for the 3 mode buttons in the settings dialog.
FLIGHT_MODE_NAMES: tuple[str, ...] = ("低调", "标准", "胡闹")

DEFAULT_FLIGHT_MODE = "标准"


def validate_flight_kwargs(kwargs: dict[str, Any]) -> None:
    """Reject unknown keys or wrong-typed values in a flight_kwargs dict.

    Raises :class:`ValueError` with a clear message if a key is not one
    of :data:`VALID_FLIGHT_KWARG_KEYS` or if a value has an unsupported
    Python type. ``bool`` is accepted as a valid substitute for ``int``
    only when the value is one of the few well-known bool-typed fields
    (``fly_bounce``); otherwise ints/floats must be numeric and strings
    must be ``str``.
    """
    if not isinstance(kwargs, dict):
        raise ValueError(f"flight_kwargs must be a dict, got {type(kwargs).__name__}")
    for key, value in kwargs.items():
        if key not in VALID_FLIGHT_KWARG_KEYS:
            raise ValueError(
                f"Unknown flight_kwarg {key!r}; valid keys: {VALID_FLIGHT_KWARG_KEYS}"
            )
        if key == "fly_bounce":
            if not isinstance(value, bool):
                raise ValueError(f"fly_bounce must be bool, got {type(value).__name__}")
        elif key == "fly_path":
            if not isinstance(value, str):
                raise ValueError(f"fly_path must be str, got {type(value).__name__}")
        elif key in ("fly_loop_count", "fly_duration_ms", "float_duration_ms",
                     "vertical_jitter", "notification_interval_ms") and \
                (isinstance(value, bool) or not isinstance(value, (int, float))):
            raise ValueError(f"{key} must be int, got {type(value).__name__}")


@dataclass
class AppConfig:
    """Resolved application configuration consumed by the UI layer."""

    theme_name: str = DEFAULT_THEME
    colors: dict[str, str] = field(default_factory=dict)
    flight_mode: str = DEFAULT_FLIGHT_MODE
    flight_kwargs: dict[str, Any] = field(
        default_factory=lambda: dict(FLIGHT_MODES[DEFAULT_FLIGHT_MODE])
    )
    tts_provider: str = DEFAULT_TTS_PROVIDER
    minimax_subscription_key: str = ""
    language: str = field(default_factory=detect_system_language)
    plane_preset_key: str = "airplane"
    plane_preset_params_json: str = ""
    # Gamification (v0.2.7+)
    unlocked_presets: set[str] = field(default_factory=set)
    achievement_progress: dict[str, Any] = field(default_factory=dict)
    distinct_notification_sources: set[str] = field(default_factory=set)
    presets_used: set[str] = field(default_factory=set)
    clicks: int = 0
    tts_count: int = 0
    # Do-Not-Disturb
    dnd_enabled: bool = False
    dnd_schedule_enabled: bool = False
    dnd_schedule_start: str = "22:00"
    dnd_schedule_end: str = "08:00"
    # AI persona
    persona_enabled: bool = True
    persona_prompts_json: str = ""
    # Voice input (v0.4.0+)
    stt_enabled: bool = False
    stt_wake_word: str = "hey_jarvis"


def _parse_hhmm(text: str) -> Optional[int]:
    """Parse ``"HH:MM"`` to minutes-since-midnight. Returns ``None`` on bad input."""
    try:
        parts = str(text).strip().split(":")
        if len(parts) != 2:
            return None
        h, m = int(parts[0]), int(parts[1])
        if not (0 <= h <= 23 and 0 <= m <= 59):
            return None
        return h * 60 + m
    except (ValueError, AttributeError):
        return None


def is_dnd_active(
    cfg: AppConfig,
    now: Optional[datetime.time] = None,
) -> bool:
    """Return True if Do-Not-Disturb should suppress incoming real notifications.

    Two independent triggers:
    - ``cfg.dnd_enabled`` (manual toggle)
    - ``cfg.dnd_schedule_enabled`` plus the current time falling inside
      the configured ``[start, end)`` window. Midnight-crossing windows
      (e.g. ``22:00`` to ``08:00``) are supported: the window is treated
      as wrapping past midnight.
    """
    if cfg.dnd_enabled:
        return True
    if cfg.dnd_schedule_enabled:
        start = _parse_hhmm(cfg.dnd_schedule_start)
        end = _parse_hhmm(cfg.dnd_schedule_end)
        if start is None or end is None:
            return False
        current = now or datetime.datetime.now().time()
        current_minutes = current.hour * 60 + current.minute
        if start == end:
            return False  # zero-length window: never match
        if start < end:
            return start <= current_minutes < end
        # Wraps midnight: e.g. 22:00 → 08:00 means current_minutes >= start OR < end
        return current_minutes >= start or current_minutes < end
    return False


def _new_settings() -> QSettings:
    """Build a QSettings instance using IniFormat stored in ~/.config/messageflight."""
    import os
    from pathlib import Path
    config_dir = os.environ.get("MESSAGEFLIGHT_CONFIG_DIR")
    if config_dir is None:
        config_dir = str(Path.home() / ".config" / "messageflight")
    Path(config_dir).mkdir(parents=True, exist_ok=True)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, config_dir)
    _ensure_example_config(Path(config_dir))
    return QSettings(QSettings.Format.IniFormat, QSettings.Scope.UserScope, ORG, APP)


def _ensure_example_config(config_dir: Path) -> None:
    """Create a config.example.ini if it doesn't already exist."""
    example_path = config_dir / "config.example.ini"
    if example_path.exists():
        return
    example_content = '''; MessageFlight 配置文件示例
; 文件位置: ~/.config/messageflight/MessageFlight.ini
; 警告: 此文件仅为示例，实际配置由程序自动管理。
;       手动修改前请先退出程序。

[MessageFlight]
; 配色主题: default(默认粉) | retro(复古绿) | cyber(未来赛博)
color_scheme=default

; 9 个颜色值 (hex 格式)
plane_color=#FF69B4
wing_color=#FF1493
accent_color=#FFFFFF
decor_color=#FF69B4
banner_color=#FFB6C1
text_color=#FFFFFF
thruster_outer_color=#FFA500
thruster_middle_color=#FF4500
thruster_inner_color=#FFFF00

; 飞行模式: 低调 | 标准 | 胡闹
flight_mode=标准

; 飞行参数字典 (JSON 格式)
; fly_bounce: 是否弹跳 (true/false)
; fly_loop_count: 循环次数 (-1=无限)
; fly_path: 飞行路径 (horizontal | vertical_pong)
; fly_duration_ms: 飞行时长 (毫秒)
; float_duration_ms: 悬浮时长 (毫秒)
; vertical_jitter: 垂直抖动幅度
; notification_interval_ms: 通知间隔 (毫秒)
flight_kwargs_json={"fly_bounce": false, "fly_loop_count": -1, "fly_path": "horizontal", "fly_duration_ms": 8000, "float_duration_ms": 1500, "vertical_jitter": 100, "notification_interval_ms": 5000}

; TTS 引擎: sapi(本地语音) | minimax(在线语音)
tts_provider=sapi

; MiniMax Token Plan 订阅 Key
; 获取方式: https://platform.minimaxi.com/subscribe/token-plan
; 注意: 这是订阅 Key，不是按量计费的 API Key
minimax_subscription_key=your-subscription-key-here
'''
    with contextlib.suppress(OSError):
        example_path.write_text(example_content, encoding="utf-8")


def _parse_semicolon_set(raw: Any) -> set[str]:
    """Parse a QSettings string value like 'a;b;c' into a set of strings."""
    if raw is None or raw == "":
        return set()
    return {s for s in str(raw).split(";") if s}


def load_config(settings: QSettings | None = None) -> AppConfig:
    """Read the persisted config, falling back to defaults on any failure.

    If the INI file is missing, corrupt, or only partially populated,
    missing keys are silently replaced with the active theme's defaults
    so the app still has a fully populated color dict to hand to the
    widget.

    If ``settings`` is provided, that QSettings instance is used directly
    (useful for tests). Otherwise a fresh QSettings is built from the
    user-scope INI directory.
    """
    if settings is None:
        try:
            settings = _new_settings()
        except Exception as e:
            print(f"load_config: failed to open QSettings ({e!r}); using defaults", file=sys.stderr)
            return _default_config()

    try:
        theme_name = str(settings.value(SETTINGS_KEY, DEFAULT_THEME))
        if theme_name not in THEMES:
            theme_name = DEFAULT_THEME
        base = THEMES[theme_name]
        colors = {key: str(settings.value(key, base[key])) for key in base}

        # Flight mode + flight_kwargs (Task 06)
        flight_mode = str(settings.value(FLIGHT_MODE_KEY, DEFAULT_FLIGHT_MODE))
        if flight_mode not in FLIGHT_MODES:
            flight_mode = DEFAULT_FLIGHT_MODE
        default_kwargs = FLIGHT_MODES[flight_mode]
        raw_kwargs_json = settings.value(FLIGHT_KWARG_KEY, None)
        if raw_kwargs_json is None or str(raw_kwargs_json) == "":
            flight_kwargs: dict[str, Any] = dict(default_kwargs)
        else:
            try:
                parsed = json.loads(str(raw_kwargs_json))
                if not isinstance(parsed, dict):
                    raise ValueError("flight_kwargs_json must encode a JSON object")
                validate_flight_kwargs(parsed)
                flight_kwargs = dict(parsed)
            except (ValueError, json.JSONDecodeError) as e:
                print(
                    f"load_config: bad flight_kwargs_json ({e!r}); falling back to {flight_mode!r}",
                    file=sys.stderr,
                )
                flight_kwargs = dict(default_kwargs)
        tts_provider = str(settings.value(TTS_PROVIDER_KEY, DEFAULT_TTS_PROVIDER))
        if tts_provider not in VALID_TTS_PROVIDERS:
            tts_provider = DEFAULT_TTS_PROVIDER
        minimax_subscription_key = str(settings.value(MINIMAX_SUBSCRIPTION_KEY, ""))
        language = normalize_language(str(settings.value(LANGUAGE_KEY, detect_system_language())))
        plane_preset_key = str(settings.value(PLANE_PRESET_KEY, "airplane"))
        plane_preset_params_json = str(settings.value(PLANE_PRESET_PARAMS_JSON_KEY, ""))
        # DND fields
        dnd_enabled = _parse_bool(settings.value(DND_ENABLED_KEY, False))
        dnd_schedule_enabled = _parse_bool(settings.value(DND_SCHEDULE_ENABLED_KEY, False))
        dnd_schedule_start = str(settings.value(DND_SCHEDULE_START_KEY, "22:00"))
        dnd_schedule_end = str(settings.value(DND_SCHEDULE_END_KEY, "08:00"))
        # AI persona
        persona_enabled = _parse_bool(settings.value(PERSONA_ENABLED_KEY, True))
        persona_prompts_json = str(settings.value(PERSONA_PROMPTS_JSON_KEY, ""))
        # Voice input
        stt_enabled = _parse_bool(settings.value(STT_ENABLED_KEY, False))
        stt_wake_word = str(settings.value(STT_WAKE_WORD_KEY, "hey_jarvis"))
        # Gamification (v0.2.7+)
        unlocked_presets = _parse_semicolon_set(settings.value(UNLOCKED_PRESETS_KEY, ""))

        progress_raw = settings.value(ACHIEVEMENT_PROGRESS_KEY, "{}")
        try:
            achievement_progress_raw = json.loads(str(progress_raw)) if progress_raw else {}
            if not isinstance(achievement_progress_raw, dict):
                achievement_progress_raw = {}
        except (json.JSONDecodeError, TypeError):
            achievement_progress_raw = {}
        achievement_progress: dict[str, Any] = achievement_progress_raw

        distinct_notification_sources = _parse_semicolon_set(settings.value(DISTINCT_SOURCES_KEY, ""))
        presets_used = _parse_semicolon_set(settings.value(PRESETS_USED_KEY, ""))

        try:
            clicks = int(settings.value(CLICKS_KEY, 0))
        except (TypeError, ValueError):
            clicks = 0
        try:
            tts_count = int(settings.value(TTS_COUNT_KEY, 0))
        except (TypeError, ValueError):
            tts_count = 0
    except Exception as e:
        print(f"load_config: failed to read keys ({e!r}); using defaults", file=sys.stderr)
        return _default_config()

    return AppConfig(
        theme_name=theme_name,
        colors=colors,
        flight_mode=flight_mode,
        flight_kwargs=flight_kwargs,
        tts_provider=tts_provider,
        minimax_subscription_key=minimax_subscription_key,
        language=language,
        plane_preset_key=plane_preset_key,
        plane_preset_params_json=plane_preset_params_json,
        dnd_enabled=dnd_enabled,
        dnd_schedule_enabled=dnd_schedule_enabled,
        dnd_schedule_start=dnd_schedule_start,
        dnd_schedule_end=dnd_schedule_end,
        persona_enabled=persona_enabled,
        persona_prompts_json=persona_prompts_json,
        stt_enabled=stt_enabled,
        stt_wake_word=stt_wake_word,
        unlocked_presets=unlocked_presets,
        achievement_progress=achievement_progress,
        distinct_notification_sources=distinct_notification_sources,
        presets_used=presets_used,
        clicks=clicks,
        tts_count=tts_count,
    )


def save_config(cfg: AppConfig, settings: QSettings | None = None) -> None:
    """Persist the given config to disk. Errors are logged, not raised.

    If ``settings`` is provided, that QSettings instance is used directly
    (useful for tests). Otherwise a fresh QSettings is built from the
    user-scope INI directory.
    """
    try:
        # Validate the flight_kwargs before persisting; on failure, fall
        # back to the active mode's default kwargs so a corrupt save
        # does not poison the next load.
        try:
            validate_flight_kwargs(cfg.flight_kwargs)
            flight_kwargs_to_save = dict(cfg.flight_kwargs)
        except ValueError as e:
            print(f"save_config: invalid flight_kwargs ({e!r}); using mode defaults", file=sys.stderr)
            mode = FLIGHT_MODES.get(cfg.flight_mode, FLIGHT_MODES[DEFAULT_FLIGHT_MODE])
            flight_kwargs_to_save = dict(mode)

        if settings is None:
            settings = _new_settings()
        settings.setValue(SETTINGS_KEY, cfg.theme_name)
        for key, value in cfg.colors.items():
            settings.setValue(key, value)
        settings.setValue(FLIGHT_MODE_KEY, cfg.flight_mode)
        settings.setValue(FLIGHT_KWARG_KEY, json.dumps(flight_kwargs_to_save))
        settings.setValue(TTS_PROVIDER_KEY, cfg.tts_provider)
        settings.setValue(MINIMAX_SUBSCRIPTION_KEY, cfg.minimax_subscription_key)
        settings.setValue(LANGUAGE_KEY, normalize_language(cfg.language))
        settings.setValue(PLANE_PRESET_KEY, cfg.plane_preset_key)
        settings.setValue(PLANE_PRESET_PARAMS_JSON_KEY, cfg.plane_preset_params_json)
        settings.setValue(DND_ENABLED_KEY, cfg.dnd_enabled)
        settings.setValue(DND_SCHEDULE_ENABLED_KEY, cfg.dnd_schedule_enabled)
        settings.setValue(DND_SCHEDULE_START_KEY, cfg.dnd_schedule_start)
        settings.setValue(DND_SCHEDULE_END_KEY, cfg.dnd_schedule_end)
        settings.setValue(PERSONA_ENABLED_KEY, cfg.persona_enabled)
        settings.setValue(PERSONA_PROMPTS_JSON_KEY, cfg.persona_prompts_json)
        settings.setValue(STT_ENABLED_KEY, cfg.stt_enabled)
        settings.setValue(STT_WAKE_WORD_KEY, cfg.stt_wake_word)
        settings.setValue(UNLOCKED_PRESETS_KEY, ";".join(sorted(cfg.unlocked_presets)))
        settings.setValue(ACHIEVEMENT_PROGRESS_KEY, json.dumps(cfg.achievement_progress))
        settings.setValue(DISTINCT_SOURCES_KEY, ";".join(sorted(cfg.distinct_notification_sources)))
        settings.setValue(PRESETS_USED_KEY, ";".join(sorted(cfg.presets_used)))
        settings.setValue(CLICKS_KEY, cfg.clicks)
        settings.setValue(TTS_COUNT_KEY, cfg.tts_count)
        settings.sync()
    except Exception as e:
        print(f"save_config: failed to persist ({e!r})", file=sys.stderr)


def _parse_bool(value: Any) -> bool:
    """Coerce QSettings-returned value into a bool.

    QSettings on some platforms returns the literal string ``"true"`` /
    ``"false"`` for boolean values, so we accept both Python bools and
    the lowercased string forms.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1", "yes", "on")
    if isinstance(value, (int, float)):
        return bool(value)
    return False


def _default_config() -> AppConfig:
    """Return a fully-populated default AppConfig (used on read failure)."""
    mode = FLIGHT_MODES[DEFAULT_FLIGHT_MODE]
    return AppConfig(
        theme_name=DEFAULT_THEME,
        colors=dict(THEMES[DEFAULT_THEME]),
        flight_mode=DEFAULT_FLIGHT_MODE,
        flight_kwargs=dict(mode),
        tts_provider=DEFAULT_TTS_PROVIDER,
        minimax_subscription_key="",
        language=detect_system_language(),
        plane_preset_key="airplane",
        plane_preset_params_json="",
        dnd_enabled=False,
        dnd_schedule_enabled=False,
        dnd_schedule_start="22:00",
        dnd_schedule_end="08:00",
        persona_enabled=True,
        persona_prompts_json="",
        stt_enabled=False,
        stt_wake_word="hey_jarvis",
    )
