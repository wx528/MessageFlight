"""Tests for the persistent AppConfig (Task 05) + FlightModeConfig (Task 06)."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QSettings

from message_flight.config import (
    APP,
    DEFAULT_THEME,
    FLIGHT_MODE_NAMES,
    FLIGHT_MODES,
    ORG,
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
    monkeypatch.setenv("MESSAGEFLIGHT_CONFIG_DIR", str(ini_dir))
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


def test_load_config_default_tts_provider(isolated_settings):
    """Default tts_provider must be 'sapi'."""
    cfg = load_config()
    assert cfg.tts_provider == "sapi"
    assert cfg.minimax_subscription_key == ""


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


def test_save_load_tts_provider_round_trip(isolated_settings):
    """Saving a config with minimax provider must round-trip."""
    cfg = load_config()
    cfg.tts_provider = "minimax"
    cfg.minimax_subscription_key = "test-key-123"
    save_config(cfg)

    loaded = load_config()
    assert loaded.tts_provider == "minimax"
    assert loaded.minimax_subscription_key == "test-key-123"


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


def test_flight_modes_have_three_entries():
    """FLIGHT_MODES must contain exactly 3 named presets: 低调 / 标准 / 胡闹."""
    assert set(FLIGHT_MODES.keys()) == {"低调", "标准", "胡闹"}
    assert len(FLIGHT_MODES) == 3
    # The user-facing order tuple must list the 3 names in display order
    assert FLIGHT_MODE_NAMES == ("低调", "标准", "胡闹")
    # Each mode must be a plain dict of flight_kwargs
    for name, mode in FLIGHT_MODES.items():
        assert isinstance(mode, dict) and len(mode) >= 1, name


def test_save_load_flight_kwargs_round_trip(isolated_settings):
    """Saving a config with custom flight_kwargs must round-trip through load_config.

    To guard against a no-op json.dumps/loads implementation, we mutate one
    value before saving and assert the *modified* value is what we read back
    (not the original preset default). We also inspect the raw QSettings
    string to confirm it is real JSON, not a Python repr().
    """
    cyber_kwargs = dict(FLIGHT_MODES["胡闹"])
    cfg = AppConfig(
        theme_name="cyber",
        colors=dict(THEMES["cyber"]),
        flight_mode="胡闹",
        flight_kwargs=dict(cyber_kwargs),
    )
    # Mutate one int and one bool to prove values are actually serialized,
    # not just round-tripped by reference
    cfg.flight_kwargs["fly_duration_ms"] = 4321
    cfg.flight_kwargs["fly_bounce"] = True
    save_config(cfg)

    loaded = load_config()
    assert loaded.flight_mode == "胡闹"
    assert loaded.flight_kwargs == cfg.flight_kwargs
    # Specifically spot-check a few key values to guard against a silent
    # type-coercion bug (e.g. bool -> int) in the JSON round-trip
    assert loaded.flight_kwargs["fly_bounce"] is True
    assert loaded.flight_kwargs["fly_loop_count"] == -1
    assert loaded.flight_kwargs["fly_duration_ms"] == 4321
    assert loaded.flight_kwargs["notification_interval_ms"] == 2000

    # Inspect the raw QSettings string to prove the value was actually
    # JSON-serialized (not Python repr'd, not no-op'd)
    raw = QSettings(
        QSettings.Format.IniFormat, QSettings.Scope.UserScope, ORG, APP
    ).value("flight_kwargs_json")
    assert isinstance(raw, str) and raw
    assert "fly_duration_ms" in raw
    assert ": 4321" in raw or ":4321" in raw, f"expected JSON, got: {raw!r}"
    # A Python repr would use single quotes; JSON uses double quotes
    assert '"fly_bounce"' in raw, f"expected JSON double-quoted key, got: {raw!r}"


def test_load_config_default_preset_key(isolated_settings):
    cfg = load_config()
    assert cfg.plane_preset_key == "airplane"
    assert cfg.plane_preset_params_json == ""


def test_save_load_preset_round_trip(isolated_settings):
    cfg = load_config()
    cfg.plane_preset_key = "ufo"
    cfg.plane_preset_params_json = '{"disc_radius": 30}'
    save_config(cfg)
    loaded = load_config()
    assert loaded.plane_preset_key == "ufo"
    assert loaded.plane_preset_params_json == '{"disc_radius": 30}'
