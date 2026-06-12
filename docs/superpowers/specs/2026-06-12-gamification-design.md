# Gamification Layer Design

> **Status:** Design approved, pending spec review.
> **Branch:** `feat/gamification` (worktree `.worktrees/gamification`)

## Goal

Add a thin gamification layer on top of the existing notification flow. The plane stays the centerpiece, but now carries a "personality progression": users start with the 4 default presets, and unlocking achievements adds 5 more selectable presets to the cycle. Existing UX is untouched; achievements are unobtrusive until earned.

Targets itch.io launch as a "desktop companion / virtual pet lite" — discoverable, rewarding, low-friction.

## Non-Goals

- Mood / hunger / emotional state (deferred to v2)
- Mini-games (deferred to v2)
- Multi-device sync
- Cloud-persisted progression (local QSettings only)
- Paid / freemium content

## Catalog

### 8 Achievements

| ID | Trigger | Reward |
|---|---|---|
| `first_flight` | 1 notification received | 🎅 圣诞飞艇 (Santa Sleigh) |
| `centurion` | 100 notifications total | 🦆 小黄鸭 (Rubber Duck) |
| `social_butterfly` | 5 distinct `source` values | 🌈 彩虹航天飞机 (Rainbow Rocket) |
| `night_owl` | 1 notification between 00:00–04:59 | ✨ 黄金 UFO (Gold UFO) |
| `early_bird` | 1 notification between 05:00–07:59 | 🐤 像素小鸟 (Pixel Bird) |
| `clicker` | 10 plane clicks | 🏆 milestone badge |
| `loud_mouth` | 50 tts speak events | 🏆 milestone badge |
| `try_them_all` | used all 4 defaults at least once | 🏆 milestone badge |

5 achievements unlock 5 distinct presets (1:1). 3 are pure milestone badges (toast + Collection badge, no preset reward).

### 5 Unlockable Presets

Each is a real `PlanePreset` subclass with its own `draw()`, `get_parameters()`, `system_prompt`, `tts_voice_id`, `tts_speed`, `tts_pitch`. Visual identity:

- **圣诞飞艇** — red-and-green santa sleigh body, snowflake accent, reindeer hints
- **小黄鸭** — yellow rubber-duck silhouette, glossy highlight
- **彩虹航天飞机** — rainbow gradient fuselage
- **黄金 UFO** — gold metallic disc, tractor beam
- **像素小鸟** — 8-bit pixel-art style, nearest-neighbor scaling

## Architecture

### Components

1. **`Achievement` dataclass** (`achievements.py`)
   - Fields: `id: str`, `name_i18n_key: str`, `description_i18n_key: str`, `trigger: TriggerSpec`, `unlock_preset_key: Optional[str]`, `icon: str`.
   - `TriggerSpec` is one of: `CounterTrigger(target)`, `DistinctSetTrigger(target)`, `TimeOfDayTrigger(start_hour, end_hour)`, `UsedAllPresetsTrigger(default_keys)`.
   - Each trigger exposes `evaluate(state) -> bool` taking the engine's progress snapshot.

2. **`AchievementEngine(QObject)`** (`achievement_engine.py`)
   - Owns: `progress: dict[str, int]`, `distinct_sources: set[str]`, `presets_used: set[str]`, `clicks: int`, `tts_count: int`.
   - Signals: `unlocked(str achievement_id)`, `milestone(str achievement_id)`.
   - Public API: `record_notification(source)`, `record_plane_click()`, `record_tts_speak()`, `record_preset_used(key)`.
   - On each call, evaluates all 8 achievements in order. Idempotent: skips ones already fired in this session AND ones already unlocked in `cfg.unlocked_presets` (so reload doesn't re-fire).
   - Constructor: `(cfg: AppConfig, parent=None)`. Writes back to `cfg` on unlock; caller persists.

3. **`ACHIEVEMENTS: list[Achievement]`** (`achievements.py`)
   - Module-level list, 8 entries, evaluation order = display order.

4. **5 new `PlanePreset` subclasses** in `plane_presets/`
   - Each in its own module: `sleigh.py`, `duck.py`, `rainbow_rocket.py`, `gold_ufo.py`, `pixel_bird.py`.
   - All expose the existing `PlanePreset` interface: `draw()`, `get_parameters()`, `get_default_params()`, `name`, `icon`, `system_prompt`, `tts_voice_id`, `tts_speed`, `tts_pitch`.

5. **`plane_presets/__init__.py` changes**
   - Add `UNLOCKABLE_PRESETS: dict[str, Type[PlanePreset]]` with the 5 new entries.
   - Add `list_available_presets(unlocked: set[str]) -> list[tuple[str, str, str]]` returning defaults first, then `unlocked ∩ UNLOCKABLE_PRESETS` in unlock order.
   - Existing `get_preset(key)` and `list_presets()` unchanged.

6. **`Toast(QWidget)`** (`toast.py`)
   - Frameless, translucent, top-level popup.
   - Constructor: `(text: str, icon: str, target: QWidget, parent=None)`.
   - Behavior: positions itself above the target widget, animates fade-in (200ms), holds 3s, fades out (300ms), `deleteLater()`.
   - No mouse interaction, no focus stealing.

7. **`CollectionTab`** in `settings_dialog.py`
   - New `QWidget` tab added to the existing `QTabWidget`.
   - 3-column `QGridLayout` of `PlanePresetCard` widgets.
   - Each `PlanePresetCard` shows: icon, name (i18n), status:
     - Always-available: ✓ "已拥有" (always-available defaults)
     - Unlocked: ✓ "已解锁"
     - Locked: 🔒 + requirement text from achievement's `description_i18n_key`
   - Cards are not interactive (display-only).

8. **`tray_app.py` wiring**
   - Construct `AchievementEngine(cfg)`, store as `self.engine`.
   - Hook points:
     - `_on_real_notification(source, text)` → `self.engine.record_notification(source)` before persona rewrite.
     - `widget.plane.clicked` → also connected to `self.engine.record_plane_click()`.
     - `tts.speak` is already a method; wrap by patching or by adding a thin `_record_tts` indirection in `tray_app` so the engine gets a hook. (Avoid mutating `tts_manager` for testability.)
     - `_on_plane_clicked` and `_open_preset_editor` paths → call `self.engine.record_preset_used(new_key)` after applying.
   - `self.engine.unlocked.connect(self._on_achievement_unlocked)`:
     - Add to `cfg.unlocked_presets`.
     - `save_config(cfg)`.
     - `Toast("🎉 解锁了 圣诞飞艇", icon=achievement.icon, target=self.widget.plane).show()`.
   - `self.engine.milestone.connect(self._on_milestone_hit)`: same but with no preset, just toast + log.
   - Cycle order: `_on_plane_clicked` switched to `list_available_presets(self.cfg.unlocked_presets)`.

9. **`AppConfig` additions** (`config.py`)
   - `unlocked_presets: set[str] = field(default_factory=set)`
   - `achievement_progress: dict[str, int] = field(default_factory=dict)`
   - `distinct_notification_sources: set[str] = field(default_factory=set)`
   - `presets_used: set[str] = field(default_factory=set)`
   - `clicks: int = 0` (for `clicker` recovery across restarts)
   - `tts_count: int = 0` (for `loud_mouth` recovery across restarts)
   - Round-trip via QSettings using new keys: `UNLOCKED_PRESETS_KEY`, `ACHIEVEMENT_PROGRESS_KEY`, `DISTINCT_SOURCES_KEY`, `PRESETS_USED_KEY`, `CLICKS_KEY`, `TTS_COUNT_KEY`.
   - Sets serialize as `;`-joined strings; dicts as JSON.

10. **`i18n.py` additions**
    - 8 achievement names + 8 descriptions (zh + en)
    - 5 unlockable preset names (zh + en)
    - "已拥有" / "已解锁" / status strings

### Data flow (single notification lifecycle)

```
Windows notification
   │
   ▼
tray_app._on_real_notification(source, text)
   ├─→ engine.record_notification(source)
   │     └─→ evaluate all 8 achievements
   │           └─→ if match: engine.unlocked.emit(id)
   │                 └─→ cfg.unlocked_presets.add(...)
   │                 └─→ save_config(cfg)
   │                 └─→ Toast.show("🎉 解锁了 圣诞飞艇")
   ├─→ persona.rewrite(text) → tts.speak → engine.record_tts_speak()
   └─→ widget.enqueue_notification(...)
```

The engine is purely additive — removing it (or disabling it via a future toggle) leaves the app functional.

### Persistence model

- All progression lives in `AppConfig` and round-trips through QSettings.
- **Migration**: existing v0.2.6 users start fresh (all fields default). The 4 default presets remain always-available, so the user does NOT lose access to anything.
- **Fresh-start rationale**: predictable behavior, no surprise bulk-unlocks after upgrade, simpler spec.

### Cycle behavior

- `_on_plane_clicked` cycles through `list_available_presets(cfg.unlocked_presets)`.
- Locked presets are **not** in the cycle. They appear only in the Collection tab.
- This keeps the "click to switch" feature pure (no "locked, achieve X" friction mid-cycle).

## File Structure

### New files

```
message_flight/
├── achievements.py              # Achievement dataclass, TriggerSpec types, registry
├── achievement_engine.py        # AchievementEngine QObject
├── toast.py                     # Toast popup widget
└── plane_presets/
    ├── sleigh.py                # 圣诞飞艇
    ├── duck.py                  # 小黄鸭
    ├── rainbow_rocket.py        # 彩虹航天飞机
    ├── gold_ufo.py              # 黄金 UFO
    └── pixel_bird.py            # 像素小鸟

tests/
├── test_achievements.py
├── test_achievement_engine.py
├── test_unlockable_presets.py
├── test_toast.py
├── test_settings_dialog_collection.py
└── test_tray_app_gamification.py
```

### Modified files

```
message_flight/
├── plane_presets/__init__.py    # +UNLOCKABLE_PRESETS, +list_available_presets
├── config.py                    # +6 fields on AppConfig, +6 QSettings keys
├── tray_app.py                  # engine wiring, cycle uses available list, toast hook
├── settings_dialog.py           # +CollectionTab with PlanePresetCard grid
└── i18n.py                      # +18 new translation keys (8 names + 8 descs + 2 status)

tests/
├── test_config.py               # +6 round-trip cases
├── test_tray_app.py             # +cycle-available-only cases
└── test_plane_banner.py         # unchanged (clicked signal already covers clicker hook)
```

### Build / packaging

- No new Python deps. No new native deps.
- `MessageFlight.spec` — add `achievements`, `achievement_engine`, `toast` to `hiddenimports`.
- PyInstaller auto-discovers the 5 new preset files since they are imported from `__init__.py`.

## Test Plan

### New tests

| File | Coverage |
|---|---|
| `test_achievements.py` | Registry has exactly 8 entries. 5 have `unlock_preset_key` set. 3 have it `None`. All `name_i18n_key` / `description_i18n_key` resolve via `tr()`. No duplicate IDs. |
| `test_achievement_engine.py` | Per-trigger correctness:<br>• `CounterTrigger(1)` fires on 1st `record_notification`<br>• `CounterTrigger(100)` fires on 100th<br>• `DistinctSetTrigger(5)` fires when 5 distinct sources seen<br>• `TimeOfDayTrigger(0, 5)` fires when notification arrives at 02:30<br>• `TimeOfDayTrigger(5, 8)` fires when notification arrives at 06:00<br>• `CounterTrigger(10)` (clicks) fires on 10th `record_plane_click`<br>• `CounterTrigger(50)` (tts) fires on 50th `record_tts_speak`<br>• `UsedAllPresetsTrigger` fires when all 4 defaults seen<br>Idempotency: re-firing same achievement does NOT re-emit. Persistence: `unlocked_presets` and counters survive `save_config` / `load_config` round-trip. |
| `test_unlockable_presets.py` | All 5 new presets import. Each is a `PlanePreset` subclass. `get_default_params()` returns the expected dataclass. `draw(painter, params)` runs without raising against an offscreen `QPixmap` (offscreen `QPainter`). |
| `test_toast.py` | `Toast` can be constructed, `show()` / `hide()` / `close()` are safe with offscreen `QApplication`. `QApplication.processEvents()` doesn't crash. |
| `test_settings_dialog_collection.py` | Collection tab builds with 9 cards (4 default + 5 unlockable). Default presets show "已拥有". Locked show 🔒 + requirement text. Unlocked show ✓ "已解锁". Cards are display-only (no click handler changes state). |
| `test_tray_app_gamification.py` | `list_available_presets({})` returns 4 defaults. `list_available_presets({"sleigh"})` returns 5 (4 + sleigh). `_on_plane_clicked` cycles only within available. `engine.record_notification("WeChat")` fires `unlocked("first_flight")` on first call. Re-firing does not double-emit. `engine.unlocked` handler calls `save_config` and `Toast.show()`. |
| `test_config.py` (extend) | Round-trip each of the 6 new fields via QSettings: set, save, load, assert equal. |

### Regression

- All 184 existing tests must remain green.
- ruff: no new warnings.
- mypy: no new errors.

## Open Questions / Risks

1. **TTS hook indirection** — `tts.speak` is a method on `TTSManager`. To count speak events, the cleanest approach is to have `tray_app._on_persona_rewritten` call `self.engine.record_tts_speak()` after `self.tts.speak(...)`. Avoids mutating `tts_manager.py` and keeps the engine decoupled. If `speak` raises, we still want the count to advance — calling after is the safer semantic. Confirmed in the data flow above.

2. **Toast visual polish** — exact colors, font size, animation timing are placeholders. The first iteration is functional; a designer pass (or me iterating after seeing screenshots) can refine.

3. **Default parameter values for unlockable presets** — each new preset needs plausible default colors. I'll use thematic defaults (sleigh=red, duck=yellow, etc.) and rely on the existing preset editor for customization.

4. **i18n** — initial commit will be zh-CN + en. Other languages inherit English fallback until translated.

5. **Sound on unlock** — adding audio is out of scope for v1; the toast is the only feedback signal.

## Definition of Done

- All 8 achievements wired and test-covered.
- All 5 unlockable presets importable, drawable, selectable.
- Cycle only includes unlocked presets.
- Collection tab renders correctly with locked/unlocked states.
- Toast appears on unlock.
- Progression persists across app restarts.
- Existing 184 tests + new tests all green.
- ruff + mypy clean.
- Commit on `feat/gamification`, not merged to main yet (separate PR).
