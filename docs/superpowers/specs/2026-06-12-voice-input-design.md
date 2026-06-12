# 语音命令输入设计

## 目标

为 MessageFlight 增加语音命令输入能力：用户说唤醒词后，给出简短语音命令，应用将其解析为基础控制动作（暂停 / 恢复 / 切换预设 / 免打扰 / 发送演示通知）。

约束（用户在 brainstorming 中确认）：

- 唤醒词检测在本地完成，不始终上传音频
- STT（语音转文字）走云端 API，与现有 MiniMax TTS 同供应商
- 有明确的视觉指示器（托盘图标）
- 中英双语命令支持
- 范围限定为基础控制 5 个命令，最小集

## 背景

- 现有 TTS 架构：`tts.py` 提供 `TTSReader` 基类 + `SAPIReader` / `MiniMaxReader` 两个具体实现；`tts_manager.py` 提供 `TTSManager` 统一调度、错误回退
- 已有 `winsdk` / `pygame` / `QNetworkAccessManager` 异步网络模式
- 持久化通过 `QSettings` 存 INI，分 `AppConfig`（设置）+ `GamificationState`（运行时状态）
- 当前 `AppConfig` 有 `tts_provider` / `minimax_subscription_key` 等 TTS 相关字段；STT 应有对应的启用开关和配置
- STT 与 TTS 复用同一份 `minimax_subscription_key`（同一供应商、同一计费账户），不引入新 key

## 设计

### 架构

完全平行于现有 TTS 模块，新增 4 个模块 + 改 2 个模块：

```
新增：
  message_flight/
    wake_word.py          # OpenWakeWordListener（本地唤醒检测）
    stt.py                # STTReader 基类 + MiniMaxSTTReader
    voice_commands.py     # VoiceCommand 枚举 + 中英双语命令解析
    stt_manager.py        # STTManager：协调 唤醒 + STT + 命令分发

改动：
  message_flight/config.py      # 新增 stt_enabled / stt_wake_word 字段
  message_flight/tray_app.py    # 接线 + 托盘图标状态切换
  pyproject.toml                # 新增 openwakeword / sounddevice 依赖
  message_flight/i18n.py        # 新增 voice.* i18n key
  message_flight/settings_dialog.py  # 新增"语音命令"Tab
```

### 数据流

```
T0  App 启动，STTManager.start()  (仅当 cfg.stt_enabled)
    ├─ WakeWordListener.start() —— 后台线程打开 16kHz mic stream
    └─ 状态: IDLE

T1  用户说唤醒词
    ├─ openwakeword 模型命中
    └─ listener.emit(wake_word_detected)  跨线程 Qt signal

T2  STTManager 接收信号
    ├─ state: IDLE → LISTENING_FOR_COMMAND
    ├─ listener.pause()
    ├─ 清空 audio buffer，开始累积后续音频帧
    ├─ state_changed(LISTENING_FOR_COMMAND) → 托盘图标变红环
    └─ 启动 5 秒 silence 定时器

T3  用户说命令（如 "暂停"）
    ├─ 音频帧持续进入 buffer
    └─ 静音检测命中（连续 0.5s 低于能量阈值）
       OR  5 秒超时

T4  STTManager.transcribe(audio_bytes)
    ├─ state: LISTENING_FOR_COMMAND → PROCESSING
    ├─ state_changed(PROCESSING) → 托盘图标转圈
    └─ MiniMaxSTTReader.transcribe()  异步网络请求

T5  ASR 返回文字
    ├─ VoiceCommandParser.parse(text) → VoiceCommand | None
    ├─ 命中: command_recognized.emit(cmd)
    └─ 未命中: transcript_failed.emit(reason)

T6  1 秒后回 IDLE，listener.resume()
    └─ TrayApplication 接收 command → 复用现有 _toggle_pause / _on_plane_clicked 等方法
```

### 模块详细设计

#### `wake_word.py` — `OpenWakeWordListener`

```python
class OpenWakeWordListener(QObject):
    """后台线程调用 openwakeword 检测唤醒词，命中时 emit 信号。"""

    wake_word_detected = pyqtSignal()
    error_occurred = pyqtSignal(str)  # 麦克风不可用 / 模型加载失败

    def __init__(self, model_name: str = "hey_jarvis", sensitivity: float = 0.5):
        # 加载 openwakeword 模型（预训练）
        # 启动后台 QThread 持有 sd.InputStream
        ...

    def start(self): ...
    def pause(self): ...
    def resume(self): ...
    def stop(self): ...
```

- 音频参数：16kHz / mono / int16，blocksize=1280（80ms 帧）
- 每个 80ms 帧喂给 openwakeword 模型做检测
- 命中后 debounce 1 秒，避免连击
- 后台线程内捕获所有异常，仅 log + 继续监听，不让单次错误终止线程

#### `stt.py` — `STTReader` + `MiniMaxSTTReader`

```python
class STTReader:
    """抽象基类：transcribe(audio_bytes) -> str"""

    def transcribe(self, audio_bytes: bytes) -> None:
        """异步发起转录，结果通过 transcribed 信号返回。"""
        raise NotImplementedError

    _on_transcribed(self, text: str) -> None: ...


class MiniMaxSTTReader(STTReader, QObject):
    """调用 MiniMax ASR API（POST 音频，返回 JSON 文字）。"""

    transcribed = pyqtSignal(str, bytes)        # (text, original_audio)
    error_occurred = pyqtSignal(str, bytes)     # (error_msg, original_audio)

    _ENDPOINT = "https://api.minimaxi.com/v1/asr"
    _TIMEOUT_MS = 10000

    def __init__(self, api_key: str = "", ...):
        QObject.__init__(self)
        # 构造 QNetworkAccessManager
        # reply_text_map: id(reply) -> audio_bytes (用于错误回传)
        ...

    def _speak_impl(self, text): ...  # 实际 HTTP 调用
```

- 沿用 tts.py 的 `TTSReader, QObject` 双继承模式 + 显式 `__init__` 调用
- 错误信号带回 audio_bytes，让 manager 可以决定是否重试
- 仅 MiniMax 一个 STT provider；不实现本地 STT 备选（用户已确认云端单一供应商）

#### `voice_commands.py` — 命令定义 + 解析

```python
class VoiceCommand(Enum):
    PAUSE = "pause"
    RESUME = "resume"
    NEXT_PRESET = "next_preset"
    TOGGLE_DND = "toggle_dnd"
    SEND_DEMO = "send_demo"


COMMAND_PATTERNS: dict[VoiceCommand, list[str]] = {
    VoiceCommand.PAUSE:       ["暂停", "停止", "pause", "stop"],
    VoiceCommand.RESUME:      ["恢复", "继续", "resume", "continue", "start"],
    VoiceCommand.NEXT_PRESET: ["下一个", "换飞机", "next", "switch"],
    VoiceCommand.TOGGLE_DND:  ["免打扰", "勿扰", "dnd", "do not disturb"],
    VoiceCommand.SEND_DEMO:   ["演示", "测试", "demo", "test"],
}


def parse_command(text: str) -> VoiceCommand | None:
    """返回第一个匹配的 command，无匹配返回 None。
    匹配规则：关键词子串包含（不区分大小写）。"""
    lowered = text.lower()
    for cmd, keywords in COMMAND_PATTERNS.items():
        for kw in keywords:
            if kw.lower() in lowered:
                return cmd
    return None
```

#### `stt_manager.py` — `STTManager`

```python
class STTManagerState(Enum):
    IDLE = "idle"                       # 等待唤醒
    LISTENING_FOR_COMMAND = "listening" # 已唤醒，正在录命令
    PROCESSING = "processing"           # STT 请求中


class STTManager(QObject):
    """协调 WakeWordListener + STTReader + VoiceCommandParser。"""

    state_changed = pyqtSignal(str)              # STTManagerState.value
    command_recognized = pyqtSignal(str)          # VoiceCommand.value
    transcript_failed = pyqtSignal(str)          # reason（"empty" / "no_match" / "network"）
    listening_started = pyqtSignal()              # 托盘弹"我在听"提示

    def __init__(
        self,
        config: AppConfig,
        listener: Optional[OpenWakeWordListener] = None,
        stt: Optional[STTReader] = None,
        parent: Optional[QObject] = None,
    ):
        # 依赖注入：默认从 config 构造，可被测试替换

    def start(self): ...
    def stop(self): ...
    def set_enabled(self, enabled: bool): ...
    def _on_wake_word(self): ...                  # 状态机
    def _on_stt_transcribed(self, text, audio): ...
    def _on_stt_error(self, msg, audio): ...
    def _on_audio_chunk(self, chunk, indata): ... # 累积 + 静音检测
    def _on_silence_timeout(self): ...            # 5 秒硬超时
    def _schedule_return_to_idle(self): ...       # 1 秒后回 IDLE
```

- 状态机：`IDLE → LISTENING_FOR_COMMAND → PROCESSING → IDLE`（1 秒后）
- 静音检测：RMS < 阈值 连续 6 帧（约 0.5s）即认为说完
- 硬超时：5 秒后强制截断发送
- 任何错误都返回 IDLE，不让 manager 卡住
- listener / stt 通过构造函数注入（依赖倒置），方便测试

#### `config.py` 改动

```python
@dataclass
class AppConfig:
    ...
    stt_enabled: bool = False           # 默认关
    stt_wake_word: str = "hey_jarvis"   # openwakeword 预训练模型名
```

新增 QSettings key：
- `STT_ENABLED_KEY = "stt_enabled"`
- `STT_WAKE_WORD_KEY = "stt_wake_word"`

load / save 跟随现有 settings 模式（bool 用 `_parse_bool`，str 用 `str(...)`）。

#### `tray_app.py` 改动

- `__init__` 中如 `cfg.stt_enabled`，构造 `STTManager`
- 接 `command_recognized` → 路由到现有方法：
  - `PAUSE` → `self._toggle_pause(True)`
  - `RESUME` → `self._toggle_pause(False)`
  - `NEXT_PRESET` → `self._on_plane_clicked()`
  - `TOGGLE_DND` → `self.action_dnd.setChecked(not self.action_dnd.isChecked())`（触发现有 toggle）
  - `SEND_DEMO` → `self._send_demo_notification()`
- 接 `state_changed` → 更新托盘图标
- 接 `transcript_failed` → toast "没听懂 / Couldn't understand"
- 接 `listening_started` → toast "我在听 / Listening..."
- 设置对话框新增"语音命令"Tab：启用开关、唤醒词下拉

#### 托盘图标三态

- `IDLE`：原图标
- `LISTENING_FOR_COMMAND`：红色描边圆环叠加
- `PROCESSING`：旋转动画（2-3 帧 QTimer 切换）

实现：构造 3 个 `QIcon`（idle / listening / processing），`state_changed` 信号触发 `self.tray_icon.setIcon(...)`。

#### 设置对话框"语音命令"Tab

- `QCheckBox`：启用语音命令
- `QComboBox`：唤醒词下拉（"hey jarvis" / "alexa" / "hey mycroft" — openwakeword 预训练列表）
- 状态：禁用时整个 Tab 灰显（仅设置页可调）
- 切换启用 → emit 自定义信号 → TrayApplication 调 `STTManager.set_enabled(...)`

#### i18n 新增 key

```
voice.tab.title         "语音命令 / Voice Commands"
voice.enable            "启用语音命令 / Enable voice commands"
voice.wake_word         "唤醒词 / Wake word"
voice.listening         "我在听 / Listening..."
voice.not_understood    "没听懂 / Couldn't understand"
voice.network_error     "网络错误 / Network error"
voice.mic_unavailable   "无法访问麦克风 / Microphone unavailable"
voice.init_failed       "语音命令初始化失败 / Voice commands init failed"
```

中文 + 英文必备；其他 6 种语言暂留 fallback 到 zh。

### 错误处理

| 错误 | 检测点 | 处理 |
|---|---|---|
| wake word 模型加载失败 | `OpenWakeWordListener.__init__` | 捕获异常 → log + toast "语音命令初始化失败" + `stt_enabled=False` 持久化 |
| 麦克风不可用 / 权限拒绝 | `sd.InputStream` 构造 | 捕获 PortAudioError → toast "无法访问麦克风" + 禁用 STT |
| 唤醒词识别异常 | 后台线程 | log + 继续监听，不让单次错误终止线程 |
| ASR 网络错误 | `MiniMaxSTTReader` 错误信号 | toast "网络错误" + 回 IDLE |
| ASR 返回空 / 超时 | `MiniMaxSTTReader` | toast "没听清" + 回 IDLE |
| 命令不匹配 | `parse_command` 返回 None | toast "没听懂" + 回 IDLE |
| 唤醒词 1 秒内连击 | listener 内 debounce | 忽略后续命中 |
| 音频流中断 | sounddevice callback 异常 | log + 尝试重启 stream 1 次，失败则禁用 STT |

### 测试策略

**单元测试**（按模块）

| 模块 | 测试重点 | Mock 策略 |
|---|---|---|
| `voice_commands.py` | 中英双语命令解析、None 返回、大小写、关键词子串 | 纯逻辑，零 mock |
| `wake_word.py` | 唤醒命中发信号、pause/resume、debounce、模型加载失败、麦克风不可用 | mock `openwakeword.Model` 和 `sounddevice.InputStream` |
| `stt.py` | MiniMaxSTTReader 请求构造、响应解析、网络错误信号 | mock `QNetworkAccessManager` |
| `stt_manager.py` | 状态机转换、唤醒触发命令、命令分发、超时回 IDLE、错误恢复 | mock listener + stt reader（构造函数注入） |
| `config.py` | `stt_enabled` / `stt_wake_word` 持久化往返 | QSettings fixture |
| `tray_app.py` | command_recognized 路由到正确 handler、state_changed 改托盘、transcript_failed 弹 toast | patch 现有方法 |
| `settings_dialog.py` | 语音 Tab 切换启用 → emit 信号 | QApplication fixture |

**STTManager 状态机测试清单**

```
test_state_starts_idle_when_enabled
test_wake_word_transitions_to_listening_for_command
test_listening_pauses_wake_word_listener
test_processing_state_after_stt_call
test_command_match_returns_to_idle_and_resumes_listener
test_no_command_match_emits_transcript_failed
test_stt_error_returns_to_idle
test_silence_detection_triggers_stt
test_timeout_triggers_stt
test_disabled_starts_does_nothing
test_set_enabled_true_constructs_listener
test_set_enabled_false_stops_listener
test_double_wake_word_within_1s_ignored
test_command_audio_buffer_passed_to_stt
```

**VoiceCommand 解析测试清单**

```
test_parse_chinese_pause
test_parse_chinese_resume
test_parse_chinese_next_preset
test_parse_chinese_dnd
test_parse_chinese_demo
test_parse_english_pause
test_parse_english_resume
test_parse_english_each_command
test_parse_case_insensitive
test_parse_returns_none_for_nonsense
test_parse_zh_en_mixed_sentence
```

**测试隔离**

- 永不打开真实麦克风（全部 mock sounddevice）
- 永不真实调用 MiniMax ASR（全部 mock QNetworkAccessManager）
- listener / stt 通过构造函数注入到 STTManager（依赖倒置）
- pytest fixture `fake_audio_chunk` 提供 80ms 16kHz int16 静音样本

**手工测试清单**（文档化在 PR 描述中）

- 真实麦克风 + 真实 MiniMax key 端到端
- 各命令中英文
- DND 切换、暂停 / 恢复、下一预设
- 错误场景：拔麦克风、网络断开

**覆盖率目标**：新增模块 ≥ 85% 行覆盖。

### 依赖

`pyproject.toml` 新增：

```toml
dependencies = [
    ...,
    "openwakeword>=0.6.0",
    "sounddevice>=0.4.6",
]
```

注意：
- `openwakeword` 首次运行会下载预训练模型（~30MB），需在 README 提示
- `sounddevice` 在 Windows 需要 PortAudio（pip wheel 已带）
- 仅在 `stt_enabled=True` 时才 import，节省冷启动开销

### 不做的事

- 不实现本地 STT 备选（用户已确认仅 MiniMax 云端）
- 不做命令自定义（5 个固定命令）
- 不做语音反馈（命令执行后无 TTS 确认，避免噪音）
- 不做语音翻译 / 跨语言识别
- 不实现多唤醒词支持（仅 openwakeword 预训练列表中的一个）
- 不做说话人识别 / 声纹

### 风险与缓解

| 风险 | 缓解 |
|---|---|
| openwakeword 误触发 | 调高 sensitivity 阈值；debounce 1 秒；用户可手动禁用 |
| ASR 延迟影响体验 | 5 秒硬超时上限；PROCESSING 状态有托盘图标提示 |
| 麦克风权限弹窗 | Windows 10/11 默认允许；首次启动可能需用户在隐私设置中授权 |
| 模型下载失败 | `__init__` 异常捕获 + toast + 禁用功能 |
| sounddevice 平台兼容性 | 仅 Windows（与现有项目一致），README 提示 |
