"""Tests for the persistent AppConfig (Task 05)."""
import os
import sys
import tempfile

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QSettings

from message_flight.config import (
    APP,
    DEFAULT_THEME,
    ORG,
    SETTINGS_KEY,
    THEMES,
    AppConfig,
    load_config,
    save_config,
)


@pytest.fixture
def isolated_settings(monkeypatch, tmp_path):
    """Point QSettings at a temp INI file for the duration of one test."""
    ini_dir = tmp_path / "qsettings"
    ini_dir.mkdir()
    QSettings.setPath(
        QSettings.Format.IniFormat,
        QSettings.Scope.UserScope,
        str(ini_dir),
    )
    # Clear any previously set values for our org/app combination
    settings = QSettings(QSettings.Format.IniFormat, QSettings.Scope.UserScope, ORG, APP)
    settings.clear()
    settings.sync()
    del settings
    yield str(ini_dir)
    settings = QSettings(QSettings.Format.IniFormat, QSettings.Scope.UserScope, ORG, APP)
    settings.clear()
    settings.sync()
    del settings


def test_load_config_returns_defaults_when_empty(isolated_settings):
    """On first run (no INI file), load_config returns the default theme + palette."""
    cfg = load_config()
    assert cfg.theme_name == DEFAULT_THEME
    assert cfg.colors == THEMES[DEFAULT_THEME]
    # Spot-check a few keys to catch a regression in key wiring
    assert cfg.colors["plane_color"] == "#FF69B4"
    assert cfg.colors["banner_color"] == "#FFB6C1"
    assert len(cfg.colors) == 9


def test_save_then_load_round_trip_preserves_colors(isolated_settings):
    """A custom theme + palette saved by save_config must round-trip through load_config."""
    custom = AppConfig(
        theme_name="retro",
        colors=dict(THEMES["retro"]),
    )
    # Mutate two colors to ensure they're actually persisted, not just the theme
    custom.colors["plane_color"] = "#123456"
    custom.colors["banner_color"] = "#ABCDEF"
    save_config(custom)

    loaded = load_config()
    assert loaded.theme_name == "retro"
    assert loaded.colors["plane_color"] == "#123456"
    assert loaded.colors["banner_color"] == "#ABCDEF"
    # Other keys should still come from the retro theme
    assert loaded.colors["wing_color"] == THEMES["retro"]["wing_color"]


def test_save_config_uses_messageflight_org_and_app(isolated_settings, tmp_path):
    """save_config must persist under MessageFlight/MessageFlight in the ini scope."""
    save_config(AppConfig(theme_name="cyber", colors=dict(THEMES["cyber"])))

    ini_files = list(tmp_path.glob("**/*.ini"))
    # QSettings writes to <IniFormat scope>/MessageFlight/MessageFlight.ini
    assert ini_files, f"no ini file found under {tmp_path}"
    paths = "\n".join(str(p) for p in ini_files)
    # File path includes both org ("MessageFlight" parent dir) and app ("MessageFlight.ini")
    assert "MessageFlight" in paths
    contents = "\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in ini_files)
    assert "color_scheme" in contents
    # The persisted theme name should be visible in the file
    assert "cyber" in contents
    # And the file should contain all 9 color keys
    for key in THEMES["cyber"]:
        assert key in contents, f"missing key {key} in persisted INI"


def test_load_config_returns_defaults_when_ini_is_malformed(isolated_settings, tmp_path):
    """A garbage INI file should not raise; load_config returns defaults."""
    ini_dir = tmp_path / "qsettings"
    (ini_dir / "MessageFlight").mkdir(parents=True, exist_ok=True)
    bad = ini_dir / "MessageFlight" / f"{APP}.ini"
    bad.write_text("not [a valid=ini\n[[garbage\nkey with no value\n", encoding="utf-8")

    # Must not raise
    cfg = load_config()
    # On corrupt input we fall back to defaults
    assert cfg.theme_name == DEFAULT_THEME
    assert isinstance(cfg.colors, dict)
    assert cfg.colors.get("plane_color") == THEMES[DEFAULT_THEME]["plane_color"]
