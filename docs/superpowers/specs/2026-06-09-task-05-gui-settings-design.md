# Task 05: GUI Settings Dialog Design

**Date**: 2026-06-09
**Status**: Approved (brainstorming complete)
**Target release**: v0.1.6
**Working branch**: `feat/task-05-gui-settings`

## Problem

Through v0.1.0 → v0.1.5, four refactor tasks (component decomposition, color
parameterization, flight-behavior parameterization, TTS planning) exposed
**20+ configurable parameters** in `PlaneBanner` and `FlightWidget` — but
**no UI surface** to change them. The tray menu has only 5 fixed items
(show / pause / notification status / autostart / quit).

User feedback after v0.1.5 release: "tray menu looks the same as before."

This task exposes the most impactful subset (color scheme + a demo-notification
trigger) via a real `QDialog` settings panel. Other parameters (flight
behavior, TTS) remain code-only for now.

## Scope

**In scope**:
1. New `SettingsDialog` that lets the user edit 9 plane/banner/thruster colors
2. Three preset "schemes" (default-pink, retro-green, cyber-future) as one-click
   buttons in the dialog
3. Two new tray menu items: "发送演示通知" and "设置..."
4. Persistence via `QSettings` (cross-platform: `%APPDATA%` on Windows)
5. `PlaneBanner.update_colors(...)` method to apply new colors live

**Out of scope** (deferred to future tasks):
- 11 flight-behavior parameters (`fly_bounce`, `fly_loop_count`, `fly_path`, etc.)
  — too many, low priority; exposed only via Python API for now
- TTS module
- Live preview while editing (changes apply only on OK)
- Per-user vs. per-machine config (always per-user)
- Config export/import

## Architecture

### New files

**`message_flight/config.py`**
- `AppConfig` dataclass: `theme_name: str` (one of `"default"`, `"retro"`, `"cyber"`),
  `colors: dict[str, str]` mapping 9 keys → hex strings
- Module-level constant `DEFAULT_COLORS: dict[str, str]` for the 3 schemes
- `load_config() -> AppConfig`: reads `QSettings("MessageFlight", "MessageFlight")`,
  returns `AppConfig` with defaults if missing keys
- `save_config(cfg: AppConfig) -> None`: writes to `QSettings`, calls `.sync()`

**`message_flight/settings_dialog.py`**
- `class SettingsDialog(QDialog)`:
  - Constructor takes `initial: AppConfig`
  - 9 rows: `QLabel` (color name) + `QLineEdit` (hex) + `QLabel` (color swatch)
  - 3 preset buttons in a row at top: "默认粉" / "复古绿" / "未来赛博"
  - OK / Cancel buttons (standard)
  - `get_result() -> AppConfig` returns the new config after OK
  - Live swatch updates as the user types in any `QLineEdit`
  - Preset button click fills all 9 `QLineEdit`s + updates swatches (but does
    **not** auto-apply; user must still click OK)

### Modified files

**`message_flight/plane_banner.py`**
- Add `update_colors(self, *, plane_color=None, wing_color=None, accent_color=None,
  decor_color=None, banner_color=None, text_color=None, thruster_outer_color=None,
  thruster_middle_color=None, thruster_inner_color=None) -> None`:
  - For each non-None arg, update the corresponding `_xxx_color` and call
    `self.update()` to trigger repaint
  - All keyword-only to match the `__init__` style

**`message_flight/tray_app.py`**
- In `__init__`:
  - Replace `self.widget = FlightWidget()` with:
    ```python
    cfg = load_config()
    self.plane_colors = cfg.colors
    self.widget = FlightWidget(plane=PlaneBanner(parent=None, **cfg.colors))
    ```
  - Wait — `PlaneBanner` is constructed inside `FlightWidget.__init__`, so we
    need to either:
    - **Option A**: pass `plane_colors` dict as a new keyword to `FlightWidget.__init__`
      that gets forwarded to `PlaneBanner(**colors)`, OR
    - **Option B**: After construction, call `self.widget.plane.update_colors(**cfg.colors)`
  - **Decision**: Option A is cleaner. Add `plane_colors: dict[str, str] | None = None`
    to `FlightWidget.__init__` signature. If provided, pass as `**plane_colors` to
    `PlaneBanner`. If `None`, use the existing default colors.
- New menu actions:
  - `"发送演示通知"` (after "暂停飞行" or in a new section): calls
    `self.widget.show_notification(random.choice(NOTIFICATIONS))`
  - `"设置..."` (after "发送演示通知"): opens `SettingsDialog(load_config())`,
    on accept calls `save_config(new_cfg)` + `self.widget.plane.update_colors(**new_cfg.colors)`
- New `__main__` test: ensure imports work (smoke test)

### Data flow

```
startup:
  load_config() → cfg = AppConfig(theme_name="default", colors={...})
  FlightWidget(plane_colors=cfg.colors) → PlaneBanner(**cfg.colors) → self.widget

user clicks "设置...":
  dlg = SettingsDialog(load_config())
  if dlg.exec() == QDialog.DialogCode.Accepted:
    new_cfg = dlg.get_result()
    save_config(new_cfg)
    self.widget.plane.update_colors(**new_cfg.colors)

user clicks "发送演示通知":
  text = random.choice(NOTIFICATIONS)
  self.widget.show_notification(text)
```

### Preset schemes

1. **默认粉** (`"default"` — current v0.1.5 colors):
   - plane `#FF69B4`, wing `#FF1493`, accent `#FFFFFF`, decor `#FF69B4`,
     banner `#FFB6C1`, text `#FFFFFF`,
     thruster outer `#FFA500`, middle `#FF4500`, inner `#FFFF00`

2. **复古绿** (`"retro"` — nod to early v0.1.0 aesthetic):
   - plane `#4F7942`, wing `#2E4A2E`, accent `#FFFFFF`, decor `#4F7942`,
     banner `#90EE90`, text `#FFFFFF`,
     thruster outer `#FFD700`, middle `#FF8C00`, inner `#FFEB3B`

3. **未来赛博** (`"cyber"` — synthwave):
   - plane `#00FFFF`, wing `#FF00FF`, accent `#FFFFFF`, decor `#00FFFF`,
     banner `#0A0A2A`, text `#00FF00`,
     thruster outer `#FF00FF`, middle `#9D00FF`, inner `#FFFFFF`

## Error handling

- Invalid hex in `QLineEdit`: `SettingsDialog` should validate via
  `QColor.isValid()` and show a red border + disable the OK button while invalid.
  On cancel, no state is saved.
- `QSettings.sync()` failure: log to stderr, continue (the next save will retry).
- Missing keys on first run: `load_config()` returns `AppConfig` with all
  defaults — no error.

## Testing

- `tests/test_config.py` (new, 4 tests):
  - `test_load_config_returns_defaults_when_empty`
  - `test_save_then_load_round_trip_preserves_colors`
  - `test_save_config_uses_messageflight_org_and_app`
  - `test_load_config_handles_corrupt_ini_gracefully` (inject garbage; should
    fall back to defaults, not raise)
- `tests/test_settings_dialog.py` (new, 3 tests):
  - `test_dialog_init_with_default_config_does_not_crash`
  - `test_click_preset_fills_all_nine_lineedits`
  - `test_get_result_after_ok_returns_new_config`
- `tests/test_plane_banner.py` (add 1 test):
  - `test_update_colors_replaces_all_nine_attributes`
- `tests/test_flight_widget.py` (add 1 test):
  - `test_flight_widget_accepts_plane_colors_kwarg`

**Total**: 31 → 38 tests, all must pass.

## Acceptance criteria

1. `pytest tests/ -v` → 38/38 PASS
2. v0.1.6 exe built via PyInstaller (same `.spec` as v0.1.5)
3. Manual: tray menu now has 7 items (added "发送演示通知" + "设置...")
4. Manual: clicking "发送演示通知" fires a notification that flies across
   the screen
5. Manual: opening "设置..." shows a 9-row form + 3 preset buttons
6. Manual: clicking "复古绿" fills all 9 fields with green; swatches update
7. Manual: clicking OK persists to `%APPDATA%\MessageFlight\MessageFlight.ini`;
   restarting exe shows the green plane
8. Manual: clicking Cancel does not save changes
9. Backward-compat: existing v0.1.5 users see the new menu items but the
   default colors match v0.1.5 exactly
10. v0.1.6 release page has 3 assets (exe + source.zip + source.tar.gz)
    built from this commit

## Risks & mitigations

- **Risk**: `QSettings` on Windows uses the registry by default — switching
  to `IniFormat` is important for portability and user inspection
  - **Mitigation**: explicitly set `QSettings.Format.IniFormat` in `load_config`/`save_config`
- **Risk**: `update_colors` with 9 keyword args is verbose at call site
  - **Mitigation**: callers pass `**cfg.colors` (dict spread) so the call
    site is a single line
- **Risk**: Toggling between schemes while a notification is animating
  causes a visual jump
  - **Mitigation**: accepted — the user explicitly opened the dialog, so a
    jump is expected behavior

## Out of scope (explicit deferral)

- TTS module: depends on TTS spec, kept for Task 06
- Flight-behavior UI: 11 parameters is too many for a single QDialog;
  defer to a future "Advanced settings" tab if user demand emerges
- Live preview during color editing: deferred per user preference (apply on OK)
- Hotkey to switch presets: deferred
