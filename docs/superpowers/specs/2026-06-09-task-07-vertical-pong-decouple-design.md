# Task 07: Vertical Pong Path + Decouple Colors from Flight Modes

**Date**: 2026-06-09
**Status**: Approved (brainstorming complete)
**Target release**: v0.2.0 (breaking UI change)
**Working branch**: `feat/task-07-vertical-pong-decouple`

## Problem

Two user complaints after v0.1.9:
1. **Missing flight path**: only horizontal exists; user wants a vertical bounce (ping-pong) path
2. **Coupled presets**: clicking "胡闹" changes BOTH flight params AND colors, wiping the user's carefully chosen custom color scheme

## Scope

**In scope**:
1. New `fly_path="vertical_pong"` — enters from top, bounces off top/bottom edges while drifting right
2. Decouple flight-mode presets from color themes:
   - Flight mode buttons (低调/标准/胡闹) change **only** flight params
   - Color preset buttons (默认粉/复古绿/未来赛博) change **only** colors
   - Both can be set independently in one dialog session
3. Add `re_flight_x_ratio` parameter (like existing `re_flight_y_ratio`) for vertical-pong entry x position

**Out of scope**:
- Other new paths (around, spiral, etc.)
- "Theme set" / bundled skin packs (user explicitly said "unless absolute reason" — defer to v0.2.1 if requested)
- Online TTS implementation (still stub)

## Architecture

### Modified files

**`message_flight/config.py`**
- Remove `theme_name` and `colors` from `FlightModeConfig` dataclass
- Keep only `flight_kwargs: dict[str, Any]`
- `FLIGHT_MODES` dict values become plain `dict[str, Any]` (flight_kwargs only)
- `AppConfig` unchanged (already has separate `theme_name` + `colors` + `flight_mode`)

**`message_flight/settings_dialog.py`**
- `_apply_flight_mode(mode_name)`:
  - Look up `FLIGHT_MODES[mode_name]` → gets `flight_kwargs` dict only
  - Update `self._current_flight_mode` and `self._current_flight_kwargs`
  - **Remove** the call to `_apply_preset(mode.theme_name)`
- Color preset buttons (`_apply_preset`) continue to work exactly as before
- Result: user can click "胡闹" then "复古绿" and get fast chaotic flight + green plane

**`message_flight/flight_widget.py`**
- Add `"vertical_pong"` to `_VALID_FLY_PATHS`
- Add new parameter `re_flight_x_ratio: float = 0.5` (default: enter from horizontal center)
- Extend `_setup_fly_animation`:
  ```python
  if self._fly_path == "vertical_pong":
      start_x = int(self.screen_w * 0.5) + random.randint(-100, 100)
      start_y = -self.plane.height()
      end_y = self.screen_h + 50
      self.fly_anim.setStartValue(QPoint(start_x, start_y))
      self.fly_anim.setEndValue(QPoint(start_x, end_y))
  ```
- Extend `_on_fly_finished` for vertical pong:
  - If current y is near bottom (`> screen_h - 100`): bounce up (new end_y = -plane.height())
  - If current y is near top (`< -50`): bounce down (new end_y = screen_h + 50)
  - Increment x slightly each bounce to drift right (`x += random.randint(20, 60)`)
  - Stop when x > screen_w + 100 (exits right side)
  - Respect `fly_loop_count` and `fly_bounce` (vertical bounce counts as one "loop")

**`message_flight/tray_app.py`**
- No changes needed (already forwards `cfg.flight_kwargs` + `plane_colors` separately)

### Vertical Pong behavior spec

| Event | Action |
|---|---|
| Initial | Plane starts at `x = screen_w * re_flight_x_ratio ± jitter`, `y = -plane.height()` |
| Direction | Downward (`+y`) |
| Bottom bounce | When `y > screen_h - 50`, reverse to upward (`-y`) |
| Top bounce | When `y < -50`, reverse to downward (`+y`) |
| Horizontal drift | Each bounce adds `random.randint(30, 80)` to x |
| Exit condition | When `x > screen_w + 100`, stop (or loop if `fly_loop_count > 0`) |
| `fly_loop_count` | Each full up-down cycle counts as 1 loop |
| `fly_bounce` | If True, after exiting right, re-enter from top at new x; if False, stop after exit |

### Data flow (decoupled)

```
startup:
  cfg = load_config()
  widget = FlightWidget(
      plane_colors=cfg.colors,      # ← from theme_name preset (independent)
      **cfg.flight_kwargs,           # ← from flight_mode preset (independent)
  )

user clicks "胡闹" in dialog:
  _apply_flight_mode("胡闹")
  → _current_flight_mode = "胡闹"
  → _current_flight_kwargs = FLIGHT_MODES["胡闹"]  (fast, bounce, etc.)
  → NO color fields changed

user clicks "复古绿" in dialog:
  _apply_preset("retro")
  → 9 color QLineEdits filled with green hexes
  → _current_theme_name = "retro"
  → NO flight params changed

user clicks OK:
  save_config(AppConfig(
      theme_name="retro",            # user chose green
      colors=green_hexes,
      flight_mode="胡闹",             # user chose fast
      flight_kwargs=fast_kwargs,
  ))
  widget.set_flight_kwargs(**fast_kwargs)
  widget.plane.update_colors(**green_hexes)
```

## Error handling

- `fly_path="vertical_pong"` on non-Windows: same as horizontal (works on any platform; only SAPI is Windows-only)
- `re_flight_x_ratio` outside [0,1]: clamp with `max(0.0, min(1.0, ratio))`
- Vertical pong with `fly_loop_count=1`: plane does one full up-down cycle, then exits right and stops

## Testing

- `test_config.py`: update `test_flight_modes_have_three_entries` — assert `FLIGHT_MODES[name]` is a dict (not FlightModeConfig)
- `test_settings_dialog.py`: 
  - Add `test_flight_mode_does_not_change_colors` — click "胡闹", assert color QLineEdits still show default
  - Update `test_click_flight_mode_button_updates_internal_state` — assert only flight params changed
- `test_flight_widget.py`:
  - Add `test_vertical_pong_path_is_valid` — construct with `fly_path="vertical_pong"`, assert no crash
  - Add `test_vertical_pong_bounces_off_edges` — mock plane position, call `_on_fly_finished`, assert direction flips
  - Add `test_re_flight_x_ratio_clamped` — pass 1.5, assert internal value is 1.0

**Target**: 44 old tests + 4 new = 48/48 PASS (some existing tests may need tweaking due to decoupling)

## Acceptance criteria

1. `pytest tests/ -v` → 48/48 PASS
2. Manual: Settings dialog — click "胡闹" then "复古绿" → OK → plane is green AND flies fast
3. Manual: Settings dialog — click "标准" → OK → plane keeps its current color
4. Manual: `fly_path="vertical_pong"` → plane enters from top, bounces off bottom/top, drifts right, exits
5. Manual: `fly_path="vertical_pong"` + `fly_loop_count=2` → 2 full bounces then stops
6. v0.2.0 release page has 3 assets

## Risks

- **Breaking change**: existing users who liked "胡闹=cyan" bundled behavior will see "胡闹=current color" after upgrade
  - **Mitigation**: v0.2.0 is a minor bump; document in release notes; user can manually pick cyber theme after picking 胡闹
- **Vertical pong physics**: simple QPropertyAnimation may not handle smooth bouncing; might need QSequentialAnimationGroup for complex path
  - **Mitigation**: keep it simple — single linear anim per segment, flip direction in `_on_fly_finished`, like existing horizontal bounce

## Migration note (for users)

> v0.2.0 decouples flight modes from color themes. Your previously saved "胡闹" preset will keep its flight speed but lose its cyber color; you can re-apply the cyber color by clicking "未来赛博" in the settings dialog.
