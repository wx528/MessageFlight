# Task 06: Flight Mode Presets Design

**Date**: 2026-06-09
**Status**: Approved (brainstorming complete)
**Target release**: v0.1.7
**Working branch**: `feat/task-06-flight-modes`

## Problem

Through v0.1.0 → v0.1.6, the user has been able to:
- Edit 9 colors (v0.1.6)
- Trigger demo notifications (v0.1.6)

But 11 flight-behavior parameters (`fly_bounce`, `fly_loop_count`,
`fly_path`, `fly_duration_ms`, etc.) are only accessible via the Python API
— no UI surface.

User feedback after v0.1.6: "在托盘里加一些模式，把我们之前的参数引出来".

This task adds 3 named "flight mode" presets (低调 / 标准 / 胡闹) that bundle
a color scheme + a tuned set of flight parameters into one click. Existing
v0.1.6 Settings dialog gets a new top row of 3 preset buttons; clicking a
button fills both the 9 color fields AND records the flight parameters
internally (visible on save).

## Scope

**In scope**:
1. 3 named flight modes: 低调 (calm) / 标准 (standard) / 胡闹 (chaos)
2. Each mode = 9 colors + 7 flight parameters bundled
3. New "飞行模式" row at the top of the existing `SettingsDialog`
4. Persistence: flight mode name + colors + flight params all in QSettings
5. `FlightWidget` already accepts all 7 flight kwargs as keyword-only —
   just pass them through from config

**Out of scope** (deferred):
- Per-parameter fine-tuning UI (QSpinBox/QComboBox in dialog) — too much UI
  for v0.1.7; users who want fine control can edit QSettings INI directly
- "Create custom mode" UI — YAGNI; preset switching is enough
- Hotkey switching — deferred
- Mode-aware tray icon (e.g. different icon per mode) — not requested
- Fly path "zigzag" / "around" — they still raise NotImplementedError;
  modes use only `horizontal` path

## Architecture

### Modified files

**`message_flight/config.py`**
- Add `FlightModeConfig` dataclass: `theme_name: str`, `colors: dict[str, str]`,
  `flight_kwargs: dict[str, Any]`
- Add `FLIGHT_MODES: dict[str, FlightModeConfig]` constant with 3 entries
  (see table below)
- Add `FLIGHT_MODE_NAMES: tuple[str, ...]` for the 3 mode labels in user-facing
  order: `("低调", "标准", "胡闹")`
- Extend `AppConfig` with `flight_mode: str` field (default `"标准"`)
  and `flight_kwargs: dict[str, Any]` field (default = standard mode's kwargs)
- Extend `load_config()` to read these new fields with proper defaults
- Extend `save_config()` to write them; flight_kwargs dict serialized as
  JSON string under key `flight_kwargs_json`
- Add a `validate_flight_kwargs(kwargs: dict) -> None` helper that:
  - Checks all keys are valid `FlightWidget.__init__` keyword args
  - Checks types (int / float / bool / str) match expectations
  - Raises `ValueError` with clear message on invalid

**`message_flight/settings_dialog.py`**
- Add a top row: 1 QHBoxLayout with 3 QPushButton labeled
  "低调" / "标准" / "胡闹", left of the existing 3 color preset buttons
- Add label "飞行模式:" before them
- Add `self._current_flight_mode: str` attribute (default = initial.flight_mode)
- Add `self._current_flight_kwargs: dict[str, Any]` attribute
  (default = initial.flight_kwargs)
- `_apply_preset(mode_name: str)` already exists for color; extend it to:
  - Look up `FLIGHT_MODES[mode_name]`
  - Fill 9 color QLineEdits with the mode's colors
  - Update `self._current_flight_mode = mode_name`
  - Update `self._current_flight_kwargs = mode.flight_kwargs`
  - Update the swatches (existing behavior)
- `get_result()`: return `AppConfig(theme_name=..., colors=..., flight_mode=..., flight_kwargs=...)`

**`message_flight/tray_app.py`**
- In `__init__`, after `cfg = load_config()`:
  - Add `self.widget = FlightWidget(plane_colors=cfg.colors, **cfg.flight_kwargs)`
  - This is the only change — `FlightWidget` already accepts all the kwargs
- No new menu items (the flight mode buttons live in the Settings dialog)

**`message_flight/flight_widget.py`**
- **No changes** — the existing 11 keyword-only params + 1 dict param
  already cover everything the 3 presets use

### 3 Preset Definitions

| Field | 低调 (calm) | 标准 (standard) | 胡闹 (chaos) |
|---|---|---|---|
| theme_name | `"default"` | `"default"` | `"cyber"` |
| plane_color | `#FF69B4` | `#FF69B4` | `#00FFFF` |
| wing_color | `#FF1493` | `#FF1493` | `#FF00FF` |
| accent_color | `#FFFFFF` | `#FFFFFF` | `#FFFFFF` |
| decor_color | `#FF69B4` | `#FF69B4` | `#00FFFF` |
| banner_color | `#FFB6C1` | `#FFB6C1` | `#0A0A2A` |
| text_color | `#FFFFFF` | `#FFFFFF` | `#00FF00` |
| thruster_outer_color | `#FFA500` | `#FFA500` | `#FF00FF` |
| thruster_middle_color | `#FF4500` | `#FF4500` | `#9D00FF` |
| thruster_inner_color | `#FFFF00` | `#FFFF00` | `#FFFFFF` |
| fly_bounce | False | False | True |
| fly_loop_count | 1 | -1 | -1 |
| fly_path | `"horizontal"` | `"horizontal"` | `"horizontal"` |
| fly_duration_ms | 12000 | 8000 | 3000 |
| float_duration_ms | 1500 | 1500 | 1500 |
| vertical_jitter | 30 | 100 | 200 |
| notification_interval_ms | 8000 | 5000 | 2000 |

Notes:
- 低调 uses 1 loop (fly once, don't repeat) — appropriate for "calm"
- 标准 matches v0.1.6 defaults exactly (backward-compat)
- 胡闹 uses cyber theme (high contrast) + 3-second flights (very fast) +
  200px jitter (wild vertical range) + bounce (back-and-forth)
- All 3 use `fly_path="horizontal"` (zigzag/around still raise
  NotImplementedError per Task 01)

### Data flow

```
startup:
  cfg = load_config()
  widget = FlightWidget(plane_colors=cfg.colors, **cfg.flight_kwargs)
  → PlaneBanner(**cfg.colors) + flight kwargs forwarded to widget

user clicks "设置...":
  dlg = SettingsDialog(load_config())
  if dlg.exec() == QDialog.Accepted:
    new_cfg = dlg.get_result()
    save_config(new_cfg)
    widget.plane.update_colors(**new_cfg.colors)
    → for each changed flight_kwarg: re-apply to widget

user clicks "低调" button (inside dialog):
  _apply_preset("低调")
  → 9 color QLineEdits filled with pink
  → self._current_flight_mode = "低调"
  → self._current_flight_kwargs = FLIGHT_MODES["低调"].flight_kwargs
  → swatches update
```

### QSettings serialization

`flight_kwargs` is a `dict[str, Any]`. QSettings supports strings, numbers,
bool, and lists. Dict must be serialized.

**Decision**: Use `json.dumps` → write as string under key
`flight_kwargs_json`. On read, `json.loads`. This is the simplest portable
approach; pickle is overkill and less debuggable.

Edge case: if JSON parse fails or a key is unknown, fall back to the
"标准" mode's flight_kwargs and log a warning to stderr.

## Error handling

- `validate_flight_kwargs` raises `ValueError` for unknown keys or wrong types
  — `save_config` catches and logs, falling back to standard mode
- `SettingsDialog._apply_preset` is safe to call on any preset name; the
  3 mode names are hardcoded in the dialog and shipped with the app
- If QSettings file is corrupt: existing `load_config` behavior (return
  defaults) covers the new fields too

## Testing

- `tests/test_config.py` (add 2 tests):
  - `test_flight_modes_have_three_entries`: assert `len(FLIGHT_MODES) == 3`
    and the names are exactly `{"低调", "标准", "胡闹"}`
  - `test_save_load_flight_kwargs_round_trip`: write a config with custom
    `flight_kwargs`, load, verify equality (tests the JSON serialization)
- `tests/test_settings_dialog.py` (add 1 test):
  - `test_click_flight_mode_button_updates_internal_state`: construct
    dialog, click "胡闹" button, assert `dlg._current_flight_mode == "胡闹"`
    and `dlg._current_flight_kwargs["fly_bounce"] is True`
- `tests/test_flight_widget.py` (add 1 test):
  - `test_flight_widget_accepts_all_flight_mode_kwargs`: unpack each mode's
    flight_kwargs, construct widget, assert no crash and key attributes
    (e.g. `_fly_bounce`, `_fly_loop_count`) match

**Total**: 40 → 44 tests, all must pass.

## Acceptance criteria

1. `pytest tests/ -v` → 44/44 PASS
2. v0.1.7 exe built via PyInstaller (same `.spec` as v0.1.6)
3. Manual: "设置..." dialog now has TWO rows of preset buttons at top:
   "飞行模式: [低调] [标准] [胡闹]" + "配色: [默认粉] [复古绿] [未来赛博]"
4. Manual: clicking "胡闹" fills colors with cyber + records flight params;
   clicking OK + restart exe shows cyber plane flying every 3 seconds,
   bouncing back and forth
5. Manual: clicking "低调" shows pink plane flying slowly (12s) once and
   stopping
6. Manual: clicking "标准" restores v0.1.6 behavior exactly
7. Backward-compat: existing v0.1.6 users open the dialog, the "标准" button
   is highlighted as the default mode, all behavior matches v0.1.6
8. v0.1.7 release page has 3 assets (exe + source.zip + source.tar.gz)

## Risks & mitigations

- **Risk**: JSON serialization adds complexity to QSettings
  - **Mitigation**: Single key (`flight_kwargs_json`); test round-trips
- **Risk**: User edits the INI manually and breaks the JSON
  - **Mitigation**: `load_config` catches JSON parse errors, falls back to
    standard mode, logs warning
- **Risk**: The 3 mode names are hardcoded — adding a 4th mode requires
    code change (not data-driven)
  - **Mitigation**: Acceptable for v0.1.7. If demand grows, can be moved
    to a JSON file in a later release
- **Risk**: Color preset and flight mode buttons look identical — confusion
  - **Mitigation**: Section labels ("飞行模式:" and "配色:") make it clear

## Out of scope (explicit deferral)

- Per-parameter fine-tuning UI in dialog (too much UI for one release)
- "Create custom mode" UI
- Mode-aware tray icon
- Hotkey switching
- Live preview of mode change (mode change applies on OK, like color)
