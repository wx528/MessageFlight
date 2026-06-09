# Task 04: TTS Notification Reader Design (SAPI + Online Stub)

**Date**: 2026-06-09
**Status**: Approved (brainstorming complete)
**Target release**: v0.1.8
**Working branch**: `feat/task-04-tts`

## Problem

v0.1.7 has visual notifications (plane flying + banner) but no audio feedback.
Users may miss notifications when away from the screen. This task adds a
TTS (text-to-speech) layer that reads notification text aloud.

User request: "做大模型 TTS 如 MiniMax / MeloTTS".
Scope decision: **B — SAPI local first + online stub** (fast ship now,
online engine in v0.1.9+).

## Scope

**In scope**:
1. `message_flight/tts.py` with `TTSReader` abstract base + `SAPIReader`
   concrete implementation
2. `OnlineTTSReader` stub class (instantiates but is no-op; prints hint)
3. Tray integration: `_on_real_notification` calls `tts.speak()` before
   `show_notification()`
4. Tray menu: add greyed-out "在线 TTS (未实现)" item (sets user expectation)
5. Settings dialog: add greyed-out "在线 TTS API 密钥" field with placeholder
6. Persistence: `config.py` gains `online_tts_api_key: str` field (used by
   v0.1.9)
7. Tests: 5 in `test_tts.py` + 1 in `test_tray_app.py`

**Out of scope** (deferred to v0.1.9+):
- Actual HTTP call to MiniMax / MeloTTS / other online API
- Async audio download + playback (QMediaPlayer)
- API key encryption
- Voice selection / speed / pitch UI
- Multi-language TTS routing

## Architecture

### New file: `message_flight/tts.py`

```python
class TTSReader:
    def __init__(self, enabled: bool = True, title_template: str = "{message}")
    def speak(self, message: str) -> None
    def _speak_impl(self, text: str) -> None  # abstract

class SAPIReader(TTSReader):
    def __init__(self, **kwargs)
    def _init_sapi(self) -> None
    def _speak_impl(self, text: str) -> None

class OnlineTTSReader(TTSReader):
    def __init__(self, api_key: str = "", **kwargs)
    def _speak_impl(self, text: str) -> None  # no-op stub
```

Design decisions:
- `TTSReader.speak()` is the public API: handles `enabled` check + template
  formatting, then delegates to `_speak_impl()`
- `SAPIReader` try/except wraps both initialization and speak; any failure
  sets `_enabled = False` so the app never crashes due to TTS
- `OnlineTTSReader` is a **no-op stub** that prints a single hint on init.
  It exists so `tray_app.py` can reference the class without ImportError,
  and so the Settings dialog field has a consumer in the codebase.

### Modified files

**`message_flight/tray_app.py`**
- Import `SAPIReader` from `message_flight.tts`
- `__init__`: `self.tts = SAPIReader(enabled=True, title_template="您有新消息了。{message}")`
- `_on_real_notification`:
  ```python
  self.tts.speak(display)
  self.widget.show_notification(display)
  ```
- New menu action (after "设置..."): `action_online_tts = QAction("在线 TTS (未实现)")`
  - `setEnabled(False)`
  - Tooltip: "v0.1.9 将支持 MiniMax / MeloTTS 等在线 TTS 引擎"

**`message_flight/config.py`**
- Extend `AppConfig` with `online_tts_api_key: str = ""`
- Extend `load_config` / `save_config` to read/write `online_tts_api_key`
- Add `DEFAULT_ONLINE_TTS_API_KEY = ""` constant

**`message_flight/settings_dialog.py`**
- Add 1 row at bottom (after color rows): `QLabel("在线 TTS API 密钥:") + QLineEdit(placeholder="v0.1.9 支持")`
  - `setEnabled(False)` — greyed out
  - Pre-filled with `initial.online_tts_api_key` (empty string by default)
  - `get_result()` includes the key in returned `AppConfig`

### Data flow

```
notification received:
  tray_app._on_real_notification(text)
  → self.tts.speak(display)      # SAPIReader.speak()
    → "您有新消息了。[微信] hello"
    → SAPI.SpVoice.Speak(text)   # blocking, local
  → self.widget.show_notification(display)
  → plane flies
```

### Persistence

`online_tts_api_key` stored in QSettings under key `online_tts_api_key`.
Default empty string. v0.1.9 will use this field when OnlineTTSReader is
implemented.

## Error handling

| Scenario | Behavior |
|---|---|
| pywin32 not installed | `_init_sapi` catches ImportError; `_enabled=False`; silent |
| SAPI.Speak throws | `speak()` catches; prints to stderr; continues |
| title_template missing `{message}` | `format()` raises KeyError; caught by `speak()`; prints error; silent |
| Non-Windows platform | `sys.platform != "win32"` → `_enabled=False` |

## Testing

`tests/test_tts.py` (5 tests):
1. `test_disabled_tts_is_noop`: `enabled=False` → `_enabled=False`, `speak()` silent
2. `test_sapi_reader_downgrades_when_win32com_missing`: mock `import win32com.client` to raise → `_enabled=False`
3. `test_default_title_template`: `title_template == "{message}"`
4. `test_custom_title_template`: custom template stored
5. `test_template_format`: `_title_template.format(message="hello")` works

`tests/test_tray_app.py` (1 test):
6. `test_on_real_notification_calls_tts_speak`: mock `SAPIReader`, trigger `_on_real_notification`, assert `speak()` called with expected text

**All tests use `enabled=False` or mocking** — no actual SAPI calls in CI.

## Acceptance criteria

1. `pytest tests/ -v` → 50/50 PASS (44 old + 6 new)
2. v0.1.8 exe built via PyInstaller
3. Manual: real Windows notification triggers SAPI voice reading the text
4. Manual: `enabled=False` (simulate by editing config) → no voice, plane still flies
5. Manual: tray menu has greyed-out "在线 TTS (未实现)" item
6. Manual: Settings dialog has greyed-out "在线 TTS API 密钥" field
7. Backward-compat: existing v0.1.7 users see no behavior change if they don't have pywin32
8. TTS failure does not crash the app or block notification display
9. v0.1.8 release page has 3 assets (exe + source.zip + source.tar.gz)

## Risks & mitigations

- **Risk**: pywin32 not in pyproject.toml → PyInstaller may miss it
  - **Mitigation**: PyInstaller 6.x auto-detects `win32com.client` if installed in build env. If not, SAPIReader silently downgrades. No hard dependency added.
- **Risk**: SAPI.Speak blocks UI thread for 1-3 seconds
  - **Mitigation**: accepted for v0.1.8. v0.1.9 online TTS will use async playback anyway.
- **Risk**: OnlineTTSReader stub confuses users ("why is it greyed out?")
  - **Mitigation**: tooltip says "v0.1.9 支持"; no other UI promises.
- **Risk**: config.py grows too many fields
  - **Mitigation**: `online_tts_api_key` is the only new field; 1 key-value pair.

## Out of scope (v0.1.9+)

- Actual HTTP integration (MiniMax / MeloTTS / Azure / Google)
- Async audio file download + QMediaPlayer playback
- Voice selection (male/female/speed)
- API key encryption (store in Windows Credential Manager)
- Per-app notification TTS on/off toggle
