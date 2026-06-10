# MessageFlight Codebase Review Fixes

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix all 22 issues identified in the 2026-06-10 codebase review.

**Architecture:** Apply targeted fixes to existing files without restructuring. Each fix is self-contained and independently testable where possible.

**Tech Stack:** Python >=3.8, PyQt6, pytest, GitHub Actions

---

## Priority Order (from review recommendations)

### Task 1: Fix Python 3.8 Compatibility (Critical #15)

**File:** `message_flight/settings_dialog.py:57`

- [ ] **Step 1: Replace `|` union syntax with `Optional`**

```python
from typing import Optional

def __init__(self, initial: AppConfig, parent: Optional[QWidget] = None):
```

- [ ] **Step 2: Verify syntax works on Python 3.8**

Run: `python -c "import ast; ast.parse(open('message_flight/settings_dialog.py').read())"`
Expected: No errors

---

### Task 2: Fix PowerShell Command Injection (Bug #5)

**File:** `message_flight/autostart.py:29-36`

- [ ] **Step 1: Use `subprocess.run` with list args and `json.dumps` for escaping**

Replace the f-string PowerShell command with a Python script approach or proper argument passing:

```python
def set_auto_start(enabled: bool):
    shortcut = _shortcut_path()
    if enabled:
        target = _exe_path()
        working_dir = os.path.dirname(target)
        ps_script = (
            'import json; '
            'import sys; '
            'shortcut = sys.argv[1]; '
            'target = sys.argv[2]; '
            'working_dir = sys.argv[3]; '
            'import win32com.client; '
            'ws = win32com.client.Dispatch("WScript.Shell"); '
            's = ws.CreateShortcut(shortcut); '
            's.TargetPath = target; '
            's.WorkingDirectory = working_dir; '
            's.Save()'
        )
        subprocess.run(
            [sys.executable, "-c", ps_script, shortcut, target, working_dir],
            check=True,
            capture_output=True,
        )
    else:
        if os.path.exists(shortcut):
            os.remove(shortcut)
```

Alternative simpler fix using `json.dumps` for PowerShell string escaping:

```python
import json

def set_auto_start(enabled: bool):
    shortcut = _shortcut_path()
    if enabled:
        target = _exe_path()
        working_dir = os.path.dirname(target)
        ps_cmd = (
            f'$ws = New-Object -ComObject WScript.Shell; '
            f'$s = $ws.CreateShortcut({json.dumps(shortcut)}); '
            f'$s.TargetPath = {json.dumps(target)}; '
            f'$s.WorkingDirectory = {json.dumps(working_dir)}; '
            f'$s.Save()'
        )
        subprocess.run(["powershell", "-Command", ps_cmd], check=True, capture_output=True)
    else:
        if os.path.exists(shortcut):
            os.remove(shortcut)
```

- [ ] **Step 2: Verify the fix handles paths with spaces and quotes**

Run: `python -c "import json; print(json.dumps(r'C:\\Users\\test\"user\\app.exe'))"`
Expected: Properly escaped string

---

### Task 3: Remove Dead `online_tts_api_key` Field (Design #10)

**Files:** `message_flight/config.py`, `message_flight/settings_dialog.py`

- [ ] **Step 1: Remove dead field from AppConfig**

In `config.py`:
- Remove `ONLINE_TTS_API_KEY` constant (line 25)
- Remove `DEFAULT_ONLINE_TTS_API_KEY` (line 30)
- Remove `online_tts_api_key` field from `AppConfig` dataclass (line 180)
- Remove `online_tts_api_key` from `load_config()` (line 294)
- Remove `settings.setValue(ONLINE_TTS_API_KEY, ...)` from `save_config()` (line 341)
- Remove from `_default_config()` (line 361)

- [ ] **Step 2: Remove dead field from settings dialog**

In `settings_dialog.py`:
- Remove `online_tts_api_key=self._api_key_edit.text()` from `get_result()` (line 185)

- [ ] **Step 3: Verify no references remain**

Run: `grep -r "online_tts_api_key" message_flight/`
Expected: No matches (or only in migration code if we keep it)

---

### Task 4: Fix Fly Path Lists Out of Sync (Design #11)

**Files:** `message_flight/flight_widget.py:11`, `message_flight/config.py:38`

- [ ] **Step 1: Remove unimplemented paths from FlightWidget**

In `flight_widget.py`:
```python
_VALID_FLY_PATHS = ("horizontal", "vertical_pong")
```

Remove the `NotImplementedError` checks (lines 70-75) since those paths no longer exist.

- [ ] **Step 2: Verify both lists match**

Run: `grep "VALID_FLY_PATHS" message_flight/config.py message_flight/flight_widget.py`
Expected: Both show only `"horizontal"` and `"vertical_pong"`

---

### Task 5: Fix Duplicate Assignment (Bug #1)

**File:** `message_flight/flight_widget.py:239,243`

- [ ] **Step 1: Remove duplicate `self._fly_count = 0`**

Line 243 is a duplicate of line 239. Delete line 243.

---

### Task 6: Fix Direct Access to Private Attributes (Bug #2)

**File:** `message_flight/flight_widget.py:192,241`

- [ ] **Step 1: Add public setter to PlaneBanner**

In `plane_banner.py`, add:
```python
def set_facing_direction(self, direction: int) -> None:
    """Set the facing direction (1 = right, -1 = left) and trigger repaint."""
    self._facing_direction = direction
    self.update()
```

- [ ] **Step 2: Replace direct access with setter in FlightWidget**

In `flight_widget.py`:
Line 192: `self.plane.set_facing_direction(self._fly_direction)`
Line 241: `self.plane.set_facing_direction(1)`

Remove the separate `self.plane.update()` calls after these lines since the setter handles it.

---

### Task 7: Fix Hardcoded AirplaneParameters Import (Bug #3)

**File:** `message_flight/plane_banner.py:39-50`

- [ ] **Step 1: Use preset.get_default_params() instead of direct import**

Replace:
```python
from message_flight.plane_presets.airplane import AirplaneParameters
self._preset = get_preset("airplane")
self._params = AirplaneParameters(...)
```

With:
```python
self._preset = get_preset("airplane")
self._params = self._preset.get_default_params()
```

- [ ] **Step 2: Update color sync logic in update_colors()**

Since `_params` is now the actual preset's default params type, ensure `update_colors()` still works. The existing logic already handles this via `hasattr(self._params, params_attr)`.

---

### Task 8: Fix winsdk Iterator Usage (Bug #4)

**File:** `message_flight/notification_worker.py:80-83`

- [ ] **Step 1: Fix iterator pattern**

Replace:
```python
it = iter(texts)
while it.has_current:
    lines.append(it.current.text)
    next(it, None)
```

With:
```python
for text_element in texts:
    lines.append(text_element.text)
```

The winsdk `IIterable` should support Python's `for...in` protocol. If not, use:
```python
it = iter(texts)
while it.has_current:
    lines.append(it.current.text)
    it.move_next()
```

---

### Task 9: Fix MiniMax TTS Race Condition (Bug #6)

**File:** `message_flight/tts.py:127,159`

- [ ] **Step 1: Queue requests with unique IDs instead of single `_last_text`**

Add a request queue mechanism:
```python
import uuid
from typing import Dict

# In __init__:
self._pending_requests: Dict[str, str] = {}  # request_id -> original_text

# In _speak_impl:
request_id = str(uuid.uuid4())
self._pending_requests[request_id] = text
# Add request_id to payload or use a custom header to track
```

Actually, a simpler fix: store `_last_text` per QNetworkReply by using a dict mapping reply -> text:

```python
# In __init__:
self._reply_text_map: dict[QNetworkReply, str] = {}

# In _speak_impl:
self._last_text = text
reply = self._network.post(request, body)
self._reply_text_map[reply] = text

# In _on_reply_finished:
text = self._reply_text_map.pop(reply, self._last_text)
```

But `self._network.post()` returns `QNetworkReply`, and the slot receives it as parameter. So:

```python
# In __init__:
self._reply_text_map: dict[int, str] = {}  # id(reply) -> text

# In _speak_impl:
self._last_text = text
reply = self._network.post(request, body)
self._reply_text_map[id(reply)] = text

# In _on_reply_finished:
text = self._reply_text_map.pop(id(reply), self._last_text)
```

Then use `text` instead of `self._last_text` in all error emissions.

---

### Task 10: Fix Temp File Leak on Exit (Bug #7)

**File:** `message_flight/tts.py:120-284`

- [ ] **Step 1: Add cleanup method and connect to app aboutToQuit**

Add:
```python
def cleanup(self) -> None:
    """Remove all active temp audio files. Called on application exit."""
    for path in list(self._active_audio_files):
        self._remove_audio_file(path)
    self._active_audio_files.clear()
```

In `__init__`, connect to app exit:
```python
from PyQt6.QtWidgets import QApplication
app = QApplication.instance()
if app is not None:
    app.aboutToQuit.connect(self.cleanup)
```

---

### Task 11: Remove Unnecessary `del settings` (Bug #8)

**File:** `message_flight/config.py:305,348`

- [ ] **Step 1: Remove `del settings` from both `load_config()` and `save_config()`**

Lines 305 and 348.

---

### Task 12: Fix Dual Color State in PlaneBanner (Design #9)

**File:** `message_flight/plane_banner.py`

- [ ] **Step 1: Simplify color storage - use only `_params`**

Remove the 9 individual `_xxx_color` QColor attributes and store colors only in `_params` (which are strings). Convert to QColor only in `paintEvent()` when drawing.

This is a larger refactor. Steps:
1. Remove `self._plane_color`, `self._wing_color`, etc. from `__init__`
2. Remove `update_colors()` method or simplify it to update `_params` only
3. In `paintEvent()`, use `QColor(getattr(self._params, attr_name))` instead of `self._xxx_color`
4. Update `set_text()` to not depend on individual color attrs

Actually, a safer incremental fix: keep `update_colors()` but make it update `_params` only, and derive colors from `_params` in paint:

```python
def _get_color(self, name: str) -> QColor:
    return QColor(getattr(self._params, name, "#FFFFFF"))
```

Then replace `self._banner_color` with `self._get_color("banner_color")`, etc.

---

### Task 13: Fix Direct Access to Preview Private Attribute (Design #12)

**File:** `message_flight/preset_editor.py:120`

- [ ] **Step 1: Add setter method to PresetPreviewWidget**

In `preset_editor.py`, in `PresetPreviewWidget`:
```python
def update_preset(self, preset) -> None:
    """Replace the active preset and request a repaint."""
    self._preset = preset
    self.update()
```

- [ ] **Step 2: Replace direct access with setter**

Line 120: `self._preview.update_preset(preset_obj)`

---

### Task 14: Fix Bird Preset Wall-Clock Time (Design #14)

**File:** `message_flight/plane_presets/bird.py:31`

- [ ] **Step 1: Replace `time.time()` with a frame counter or Qt timer-based phase**

Simplest fix: add a `phase_offset` parameter that increments each frame:

```python
def __init__(self):
    self._phase = 0.0

def draw(self, painter: QPainter, params: BirdParameters) -> None:
    self._phase += 0.05  # Increment per frame
    phase = (math.sin(self._phase * params.wing_flap_speed) + 1.0) / 2.0
    ...
```

But `draw()` is stateless. Better: use a class-level counter or accept a `time_ms` parameter. The cleanest fix without changing the API too much:

Since `PlanePreset.draw()` is called from `PlaneBanner.paintEvent()`, we can pass time info through. But that changes the interface.

Simplest practical fix: make `BirdPreset` track its own animation phase:

```python
class BirdPreset(PlanePreset):
    name = "小鸟"
    icon = "🐦"
    
    def __init__(self):
        self._animation_time = 0.0
    
    def draw(self, painter: QPainter, params: BirdParameters) -> None:
        self._animation_time += 0.016  # ~60fps assumption
        phase = (math.sin(self._animation_time * params.wing_flap_speed) + 1.0) / 2.0
        ...
```

---

### Task 15: Add Type Annotations (Design #13)

**Files:** Various

- [ ] **Step 1: Add return type annotations to key `__init__` methods**

- `TrayApplication.__init__` -> `-> None`
- `FlightWidget.__init__` -> `-> None`
- `NotificationWorker.__init__` -> `-> None`
- `SettingsDialog.__init__` -> `-> None`
- `PresetEditorWindow.__init__` -> `-> None`

---

### Task 16: Fix CI - Run Tests (Testing #16)

**File:** `.github/workflows/ci.yml`

- [ ] **Step 1: Add pytest step to CI**

After the existing steps, add:
```yaml
      - name: Install test dependencies
        run: pip install pytest

      - name: Run tests
        run: pytest tests/ -v
```

---

### Task 17: Fix CI - Run on Windows (Testing #17)

**File:** `.github/workflows/ci.yml:12`

- [ ] **Step 1: Change lint job to run on Windows**

```yaml
    runs-on: windows-latest
```

And add Windows-specific dependencies:
```yaml
      - name: Install dependencies
        run: |
          pip install --pre .
          pip install pytest
```

- [ ] **Step 2: Remove py_compile/ast steps that only check one file**

Or keep them but also run pytest. The current steps only check `message_flight.py` entry point, not the package.

---

### Task 18: Add Tests for notification_worker._poll() (Testing #18)

**File:** `tests/`

- [ ] **Step 1: Create test for winsdk iterator logic**

Create `tests/test_notification_worker.py`:
```python
import pytest
from unittest.mock import MagicMock, patch

from message_flight.notification_worker import NotificationWorker


def test_poll_extracts_text_elements():
    """Test that _poll correctly extracts text from notification bindings."""
    worker = NotificationWorker()
    
    # Mock the winsdk objects
    mock_notification = MagicMock()
    mock_notification.id = 1
    mock_notification.app_info.display_info.display_name = "TestApp"
    
    mock_binding = MagicMock()
    mock_text_element = MagicMock()
    mock_text_element.text = "Test message"
    
    # Mock the iterator behavior
    mock_texts = MagicMock()
    mock_texts.__iter__ = MagicMock(return_value=iter([mock_text_element]))
    mock_binding.get_text_elements.return_value = mock_texts
    
    mock_notification.notification.visual.get_binding.return_value = mock_binding
    
    # ... more setup needed
```

Actually, since winsdk is Windows-only, this test should be conditionally skipped:
```python
@pytest.mark.skipif(sys.platform != "win32", reason="winsdk only available on Windows")
```

---

### Task 19: Add Test for _apply_preset_to_widget (Testing #19)

**File:** `tests/`

- [ ] **Step 1: Create test for preset application**

Create `tests/test_tray_app.py`:
```python
import pytest
from unittest.mock import MagicMock, patch

from message_flight.tray_app import TrayApplication


def test_apply_preset_to_widget():
    """Test that _apply_preset_to_widget correctly deserializes and applies presets."""
    with patch.object(TrayApplication, '__init__', lambda x: None):
        app = TrayApplication.__new__(TrayApplication)
        app.widget = MagicMock()
        
        # Test with airplane preset and custom params
        params_json = '{"plane_color": "#FF0000", "wing_color": "#00FF00"}'
        app._apply_preset_to_widget("airplane", params_json)
        
        # Verify apply_preset was called
        assert app.widget.plane.apply_preset.called
        args = app.widget.plane.apply_preset.call_args
        assert args[0][1].plane_color == "#FF0000"
```

---

### Task 20: Add Static Analysis Configuration (Minor #21)

**File:** `pyproject.toml`

- [ ] **Step 1: Add ruff configuration**

```toml
[tool.ruff]
target-version = "py38"
line-length = 100
select = ["E", "F", "W", "I", "N", "UP", "B", "C4", "SIM"]
ignore = ["E501"]

[tool.ruff.pydocstyle]
convention = "google"
```

- [ ] **Step 2: Add mypy configuration**

```toml
[tool.mypy]
python_version = "3.8"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false
```

---

## Summary

| Task | Issue | File(s) | Priority |
|------|-------|---------|----------|
| 1 | Python 3.8 compat | `settings_dialog.py` | Critical |
| 2 | PowerShell injection | `autostart.py` | High |
| 3 | Dead field | `config.py`, `settings_dialog.py` | Medium |
| 4 | Fly path sync | `flight_widget.py`, `config.py` | Medium |
| 5 | Duplicate assignment | `flight_widget.py` | Low |
| 6 | Private attr access | `flight_widget.py`, `plane_banner.py` | Medium |
| 7 | Hardcoded import | `plane_banner.py` | Medium |
| 8 | winsdk iterator | `notification_worker.py` | High |
| 9 | TTS race condition | `tts.py` | High |
| 10 | Temp file leak | `tts.py` | Medium |
| 11 | Unnecessary del | `config.py` | Low |
| 12 | Dual color state | `plane_banner.py` | Medium |
| 13 | Preview private attr | `preset_editor.py` | Low |
| 14 | Bird wall-clock | `plane_presets/bird.py` | Low |
| 15 | Type annotations | Multiple | Low |
| 16 | CI tests | `.github/workflows/ci.yml` | High |
| 17 | CI Windows | `.github/workflows/ci.yml` | Medium |
| 18 | Test notification_worker | `tests/` | Medium |
| 19 | Test preset apply | `tests/` | Medium |
| 20 | Static analysis | `pyproject.toml` | Low |
