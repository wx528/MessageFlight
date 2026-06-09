"""Persistent application config backed by QSettings.

Stores the user's selected color scheme and exposes three preset
schemes: ``default``, ``retro`` (green), and ``cyber`` (synthwave).

The file uses ``QSettings.Format.IniFormat`` for portability and
inspectability on Windows (the default backend is the registry, which
is harder for users to find and edit by hand).
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field

from PyQt6.QtCore import QSettings


ORG = "MessageFlight"
APP = "MessageFlight"
SETTINGS_KEY = "color_scheme"

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
class AppConfig:
    """Resolved application configuration consumed by the UI layer."""

    theme_name: str = DEFAULT_THEME
    colors: dict[str, str] = field(default_factory=dict)


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
        return AppConfig(theme_name=DEFAULT_THEME, colors=dict(THEMES[DEFAULT_THEME]))

    try:
        theme_name = str(settings.value(SETTINGS_KEY, DEFAULT_THEME))
        if theme_name not in THEMES:
            theme_name = DEFAULT_THEME
        base = THEMES[theme_name]
        colors = {key: str(settings.value(key, base[key])) for key in base}
    except Exception as e:
        print(f"load_config: failed to read keys ({e!r}); using defaults", file=sys.stderr)
        return AppConfig(theme_name=DEFAULT_THEME, colors=dict(THEMES[DEFAULT_THEME]))
    finally:
        del settings

    return AppConfig(theme_name=theme_name, colors=colors)


def save_config(cfg: AppConfig) -> None:
    """Persist the given config to disk. Errors are logged, not raised."""
    try:
        settings = _new_settings()
        try:
            settings.setValue(SETTINGS_KEY, cfg.theme_name)
            for key, value in cfg.colors.items():
                settings.setValue(key, value)
            settings.sync()
        finally:
            del settings
    except Exception as e:
        print(f"save_config: failed to persist ({e!r})", file=sys.stderr)
