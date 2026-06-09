"""Persistent application config backed by QSettings.

Stores the user's selected color scheme and exposes three preset
schemes: ``default``, ``retro`` (green), and ``cyber`` (synthwave).

The file uses ``QSettings.Format.IniFormat`` for portability and
inspectability on Windows (the default backend is the registry, which
is harder for users to find and edit by hand).
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from typing import Any

from PyQt6.QtCore import QSettings


ORG = "MessageFlight"
APP = "MessageFlight"
SETTINGS_KEY = "color_scheme"
FLIGHT_KWARG_KEY = "flight_kwargs_json"
FLIGHT_MODE_KEY = "flight_mode"
ONLINE_TTS_API_KEY = "online_tts_api_key"

DEFAULT_ONLINE_TTS_API_KEY = ""

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
    """Bundle a color theme + a set of flight-behavior parameters.

    A flight mode preset lets the user switch both the visual palette
    and the in-flight tuning knobs in one click. The ``flight_kwargs``
    dict is forwarded as keyword arguments to :class:`FlightWidget`.
    """

    theme_name: str
    colors: dict[str, str]
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

# The 3 named flight modes. Each bundles a color scheme + a set of
# flight-behavior kwargs. Values copied verbatim from the design spec.
FLIGHT_MODES: dict[str, FlightModeConfig] = {
    "低调": FlightModeConfig(
        theme_name="default",
        colors=dict(THEMES["default"]),
        flight_kwargs={
            "fly_bounce": False,
            "fly_loop_count": 1,
            "fly_path": "horizontal",
            "fly_duration_ms": 12000,
            "float_duration_ms": 1500,
            "vertical_jitter": 30,
            "notification_interval_ms": 8000,
        },
    ),
    "标准": FlightModeConfig(
        theme_name="default",
        colors=dict(THEMES["default"]),
        flight_kwargs={
            "fly_bounce": False,
            "fly_loop_count": -1,
            "fly_path": "horizontal",
            "fly_duration_ms": 8000,
            "float_duration_ms": 1500,
            "vertical_jitter": 100,
            "notification_interval_ms": 5000,
        },
    ),
    "胡闹": FlightModeConfig(
        theme_name="cyber",
        colors=dict(THEMES["cyber"]),
        flight_kwargs={
            "fly_bounce": True,
            "fly_loop_count": -1,
            "fly_path": "horizontal",
            "fly_duration_ms": 3000,
            "float_duration_ms": 1500,
            "vertical_jitter": 200,
            "notification_interval_ms": 2000,
        },
    ),
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
                     "vertical_jitter", "notification_interval_ms"):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{key} must be int, got {type(value).__name__}")


@dataclass
class AppConfig:
    """Resolved application configuration consumed by the UI layer."""

    theme_name: str = DEFAULT_THEME
    colors: dict[str, str] = field(default_factory=dict)
    flight_mode: str = DEFAULT_FLIGHT_MODE
    flight_kwargs: dict[str, Any] = field(
        default_factory=lambda: dict(FLIGHT_MODES[DEFAULT_FLIGHT_MODE].flight_kwargs)
    )
    online_tts_api_key: str = DEFAULT_ONLINE_TTS_API_KEY


def _new_settings() -> QSettings:
    """Build a QSettings instance using IniFormat for cross-platform storage."""
    return QSettings(QSettings.Format.IniFormat, QSettings.Scope.UserScope, ORG, APP)


def load_config() -> AppConfig:
    """Read the persisted config, falling back to defaults on any failure.

    If the INI file is missing, corrupt, or only partially populated,
    missing keys are silently replaced with the active theme's defaults
    so the app still has a fully populated color dict to hand to the
    widget.
    """
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
        default_kwargs = FLIGHT_MODES[flight_mode].flight_kwargs
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
        online_tts_api_key = str(settings.value(ONLINE_TTS_API_KEY, DEFAULT_ONLINE_TTS_API_KEY))
    except Exception as e:
        print(f"load_config: failed to read keys ({e!r}); using defaults", file=sys.stderr)
        return _default_config()
    finally:
        del settings

    return AppConfig(
        theme_name=theme_name,
        colors=colors,
        flight_mode=flight_mode,
        flight_kwargs=flight_kwargs,
        online_tts_api_key=online_tts_api_key,
    )


def save_config(cfg: AppConfig) -> None:
    """Persist the given config to disk. Errors are logged, not raised."""
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
            flight_kwargs_to_save = dict(mode.flight_kwargs)

        settings = _new_settings()
        try:
            settings.setValue(SETTINGS_KEY, cfg.theme_name)
            for key, value in cfg.colors.items():
                settings.setValue(key, value)
            settings.setValue(FLIGHT_MODE_KEY, cfg.flight_mode)
            settings.setValue(FLIGHT_KWARG_KEY, json.dumps(flight_kwargs_to_save))
            settings.setValue(ONLINE_TTS_API_KEY, cfg.online_tts_api_key)
            settings.sync()
        finally:
            del settings
    except Exception as e:
        print(f"save_config: failed to persist ({e!r})", file=sys.stderr)


def _default_config() -> AppConfig:
    """Return a fully-populated default AppConfig (used on read failure)."""
    mode = FLIGHT_MODES[DEFAULT_FLIGHT_MODE]
    return AppConfig(
        theme_name=DEFAULT_THEME,
        colors=dict(THEMES[DEFAULT_THEME]),
        flight_mode=DEFAULT_FLIGHT_MODE,
        flight_kwargs=dict(mode.flight_kwargs),
        online_tts_api_key=DEFAULT_ONLINE_TTS_API_KEY,
    )
