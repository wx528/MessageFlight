"""Modal settings dialog for editing the 9-color plane/banner palette and the flight mode preset."""
from __future__ import annotations

import dataclasses
import json
from typing import Optional

from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSlider,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from message_flight.achievements import ACHIEVEMENTS
from message_flight.collection_tab import CollectionTab
from message_flight.config import (
    DEFAULT_THEME,
    FLIGHT_MODE_NAMES,
    FLIGHT_MODES,
    THEMES,
    VALID_FLY_PATHS,
    AppConfig,
)
from message_flight.i18n import LANGUAGES, language_name, tr
from message_flight.plane_presets import list_presets

_COLOR_KEYS: tuple[str, ...] = (
    "plane_color",
    "wing_color",
    "accent_color",
    "decor_color",
    "banner_color",
    "text_color",
    "thruster_outer_color",
    "thruster_middle_color",
    "thruster_inner_color",
)

_PRESET_KEYS: tuple[str, ...] = ("default", "retro", "cyber")


class SettingsDialog(QDialog):
    """A 9-row form for editing the plane color palette, plus 3 flight-mode + 3 color preset buttons.

    The dialog does not mutate the live widget directly; the caller is
    expected to call :meth:`get_result` after the dialog is accepted
    and then forward the new colors to ``PlaneBanner.update_colors``.
    """

    def __init__(
        self,
        initial: AppConfig,
        unlocked_presets: Optional[set[str]] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._config = initial
        self._language = initial.language
        self.setWindowTitle(tr("settings.title", self._language))
        self.setModal(True)

        self._current_theme_name = initial.theme_name or DEFAULT_THEME
        self._line_edits: dict[str, QLineEdit] = {}
        self._swatches: dict[str, QLabel] = {}
        self._current_flight_mode: str = initial.flight_mode
        # Copy so external mutations to the AppConfig don't leak in/out.
        self._current_flight_kwargs: dict = dict(initial.flight_kwargs)
        self._flight_mode_buttons: dict[str, QPushButton] = {}

        root = QVBoxLayout(self)

        self.tabs = QTabWidget(self)
        root.addWidget(self.tabs)

        general_tab = QWidget()
        general_layout = QVBoxLayout(general_tab)
        self.tabs.addTab(general_tab, tr("settings.title", self._language))

        self._collection_tab = CollectionTab(
            unlocked_presets if unlocked_presets is not None else set(),
            ACHIEVEMENTS,
            language=self._language,
        )
        self.tabs.addTab(
            self._collection_tab,
            tr("settings.tab.collection", self._language),
        )

        root = general_layout

        language_row = QHBoxLayout()
        language_row.addWidget(QLabel(tr("settings.language", self._language)))
        self._language_combo = QComboBox()
        for language in LANGUAGES:
            self._language_combo.addItem(language_name(language), language)
        current_language_index = self._language_combo.findData(self._language)
        self._language_combo.setCurrentIndex(max(0, current_language_index))
        language_row.addWidget(self._language_combo)
        language_row.addStretch(1)
        root.addLayout(language_row)

        # Flight-mode row (Task 06) — sits at the TOP, above the color preset row
        flight_mode_row = QHBoxLayout()
        flight_mode_row.addWidget(QLabel(tr("settings.flight_mode", self._language)))
        for mode_name in FLIGHT_MODE_NAMES:
            btn = QPushButton(mode_name)
            btn.clicked.connect(
                lambda _checked=False, name=mode_name: self._apply_flight_mode(name)
            )
            self._flight_mode_buttons[mode_name] = btn
            flight_mode_row.addWidget(btn)
        flight_mode_row.addStretch(1)
        root.addLayout(flight_mode_row)

        # Fly-path row
        path_row = QHBoxLayout()
        path_row.addWidget(QLabel(tr("settings.fly_path", self._language)))
        self._path_combo = QComboBox()
        for p in VALID_FLY_PATHS:
            self._path_combo.addItem(p)
        current_path = self._current_flight_kwargs.get("fly_path", "horizontal")
        self._path_combo.setCurrentText(current_path)
        self._path_combo.currentTextChanged.connect(self._on_path_changed)
        path_row.addWidget(self._path_combo)
        path_row.addStretch(1)
        root.addLayout(path_row)

        # Preset row
        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel(tr("settings.color_scheme", self._language)))
        for theme_key in _PRESET_KEYS:
            btn = QPushButton(tr(f"settings.preset.{theme_key}", self._language))
            btn.clicked.connect(lambda _checked=False, key=theme_key: self._apply_preset(key))
            preset_row.addWidget(btn)
        preset_row.addStretch(1)
        root.addLayout(preset_row)

        # Persona section (AI rewriter toggle + per-preset prompt)
        persona_box = QVBoxLayout()
        self._persona_enabled_checkbox = QCheckBox(tr("settings.persona.enable", self._language))
        self._persona_enabled_checkbox.setChecked(initial.persona_enabled)
        persona_box.addWidget(self._persona_enabled_checkbox)

        preset_picker_row = QHBoxLayout()
        preset_picker_row.addWidget(QLabel(tr("settings.persona.preset", self._language)))
        self._persona_preset_combo = QComboBox()
        for key, name, _icon in list_presets():
            self._persona_preset_combo.addItem(f"{name} ({key})", key)
        self._persona_preset_combo.setCurrentText(initial.plane_preset_key)
        self._persona_preset_combo.currentIndexChanged.connect(self._on_persona_preset_changed)
        preset_picker_row.addWidget(self._persona_preset_combo)

        reset_btn = QPushButton(tr("settings.persona.reset", self._language))
        reset_btn.clicked.connect(self._on_reset_persona_prompt)
        preset_picker_row.addWidget(reset_btn)
        preset_picker_row.addStretch(1)
        persona_box.addLayout(preset_picker_row)

        self._persona_prompt_edit = QPlainTextEdit()
        self._persona_prompt_edit.setPlaceholderText(tr("settings.persona.prompt_placeholder", self._language))
        self._persona_prompt_edit.setFixedHeight(120)
        persona_box.addWidget(self._persona_prompt_edit)

        self._persona_prompts: dict[str, str] = self._parse_persona_prompts(initial.persona_prompts_json)
        self._active_persona_key: Optional[str] = None
        self._on_persona_preset_changed()
        root.addLayout(persona_box)

        # 9 color rows
        form = QFormLayout()
        for key in _COLOR_KEYS:
            edit = QLineEdit(self)
            swatch = QLabel(self)
            swatch.setFixedSize(28, 18)
            swatch.setFrameShape(QLabel.Shape.StyledPanel)

            current = initial.colors.get(key, THEMES[self._current_theme_name].get(key, "#FFFFFF"))
            edit.setText(current)
            self._line_edits[key] = edit
            self._swatches[key] = swatch
            edit.textChanged.connect(lambda text, k=key: self._on_text_changed(k, text))

            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.addWidget(edit)
            row_layout.addWidget(swatch)
            form.addRow(tr(f"settings.color.{key}", self._language), row_widget)

        root.addLayout(form)

        # TTS Provider row
        provider_row = QHBoxLayout()
        provider_row.addWidget(QLabel(tr("settings.tts_engine", self._language)))
        self._provider_combo = QComboBox()
        for p in ("sapi", "minimax"):
            self._provider_combo.addItem(p)
        self._provider_combo.setCurrentText(initial.tts_provider)
        self._provider_combo.currentTextChanged.connect(self._on_provider_changed)
        provider_row.addWidget(self._provider_combo)
        provider_row.addStretch(1)
        root.addLayout(provider_row)

        # API Key (enabled only for minimax)
        self._api_key_label = QLabel(tr("settings.minimax_key", self._language))
        self._api_key_edit = QLineEdit(initial.minimax_subscription_key)
        self._api_key_edit.setPlaceholderText(tr("settings.minimax_key_placeholder", self._language))
        form.addRow(self._api_key_label, self._api_key_edit)
        self._update_api_key_enabled(initial.tts_provider)

        # OK / Cancel
        self._button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        self._button_box.accepted.connect(self.accept)
        self._button_box.rejected.connect(self.reject)
        root.addWidget(self._button_box)

        # Voice commands tab (v0.4.0+)
        self._voice_enabled_checkbox = QCheckBox(tr("voice.enable", self._language))
        self._voice_enabled_checkbox.setChecked(initial.stt_enabled)
        self._voice_wake_word_combo = QComboBox()
        from message_flight.wake_word import ALL_WAKE_WORDS
        for wake_word_key in ALL_WAKE_WORDS:
            self._voice_wake_word_combo.addItem(
                tr(f"voice.wake_word.{wake_word_key}", self._language),
                wake_word_key,
            )
        current_index = self._voice_wake_word_combo.findData(initial.stt_wake_word)
        self._voice_wake_word_combo.setCurrentIndex(max(0, current_index))

        # Sensitivity slider (0.0 – 1.0, default 0.5)
        self._sensitivity_slider = QSlider()
        from PyQt6.QtCore import Qt
        self._sensitivity_slider.setOrientation(Qt.Orientation.Horizontal)
        self._sensitivity_slider.setRange(0, 100)
        self._sensitivity_slider.setValue(int(initial.stt_sensitivity * 100))
        self._sensitivity_label = QLabel(f"{initial.stt_sensitivity:.0%}")
        self._sensitivity_slider.valueChanged.connect(
            lambda v: self._sensitivity_label.setText(f"{v / 100:.0%}")
        )
        sensitivity_row = QHBoxLayout()
        sensitivity_row.addWidget(self._sensitivity_slider)
        sensitivity_row.addWidget(self._sensitivity_label)

        # Custom wake word pinyin input
        self._custom_pinyin_edit = QLineEdit()
        self._custom_pinyin_edit.setPlaceholderText(
            tr("voice.custom_pinyin_placeholder", self._language)
        )
        self._custom_pinyin_edit.setText(initial.stt_custom_pinyin)

        voice_tab = QWidget()
        voice_layout = QVBoxLayout(voice_tab)
        form = QFormLayout()
        form.addRow(self._voice_enabled_checkbox)
        form.addRow(tr("voice.wake_word", self._language), self._voice_wake_word_combo)
        form.addRow(tr("voice.sensitivity", self._language), sensitivity_row)
        form.addRow(tr("voice.custom_pinyin", self._language), self._custom_pinyin_edit)

        # Agent toggle
        self._agent_enabled_check = QCheckBox()
        self._agent_enabled_check.setChecked(initial.agent_enabled)
        form.addRow(tr("agent.enabled", self._language), self._agent_enabled_check)

        voice_layout.addLayout(form)
        voice_layout.addWidget(QLabel(tr("voice.sensitivity_hint", self._language)))
        voice_layout.addWidget(QLabel(tr("voice.custom_pinyin_hint", self._language)))
        voice_layout.addWidget(QLabel(tr("agent.enabled_hint", self._language)))
        voice_layout.addWidget(QLabel(tr("voice.wake_word_hint", self._language)))
        voice_layout.addWidget(QLabel(tr("voice.disabled_hint", self._language)))

        # Command list
        voice_layout.addSpacing(8)
        voice_layout.addWidget(QLabel(f"<b>{tr('voice.commands_title', self._language)}</b>"))
        for cmd_key in ("pause", "resume", "next_preset", "toggle_dnd", "send_demo", "open_settings", "quit_app"):
            voice_layout.addWidget(QLabel(tr(f"voice.cmd_example.{cmd_key}", self._language)))

        voice_layout.addStretch(1)
        self.tabs.addTab(voice_tab, tr("voice.tab.title", self._language))

        # Initial render
        self._refresh_all_swatches()
        self._refresh_ok_enabled()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_result(self) -> AppConfig:
        """Return the current dialog state as an :class:`AppConfig`.

        Safe to call only after the dialog has been accepted (or while
        it is still open and the user is editing). The returned colors
        are normalized via :meth:`QColor.name` so the values match the
        ``PlaneBanner.update_colors`` contract.
        """
        colors: dict[str, str] = {}
        for key in self._line_edits:
            text = self._line_edits[key].text().strip()
            qc = QColor(text)
            colors[key] = qc.name() if qc.isValid() else text
        result = dataclasses.replace(self._config)
        result.theme_name = self._current_theme_name
        result.colors = colors
        result.flight_mode = self._current_flight_mode
        result.flight_kwargs = dict(self._current_flight_kwargs)
        result.tts_provider = self._provider_combo.currentText()
        result.minimax_subscription_key = self._api_key_edit.text()
        result.language = self._language_combo.currentData()
        result.stt_enabled = self._voice_enabled_checkbox.isChecked()
        result.stt_wake_word = self._voice_wake_word_combo.currentData() or "hey_jarvis"
        result.stt_sensitivity = self._sensitivity_slider.value() / 100.0
        result.stt_custom_pinyin = self._custom_pinyin_edit.text().strip()
        result.agent_enabled = self._agent_enabled_check.isChecked()
        return result

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _on_text_changed(self, key: str, text: str) -> None:
        """Live-validate a single field; update its swatch + OK button."""
        swatch = self._swatches[key]
        qc = QColor(text)
        if qc.isValid():
            swatch.setStyleSheet(f"background-color: {qc.name()};")
        else:
            swatch.setStyleSheet("background-color: #888888;")
        self._refresh_ok_enabled()

    def _refresh_all_swatches(self) -> None:
        for key, edit in self._line_edits.items():
            self._on_text_changed(key, edit.text())

    def _refresh_ok_enabled(self) -> None:
        all_valid = all(
            QColor(edit.text()).isValid() for edit in self._line_edits.values()
        )
        ok_btn = self._button_box.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn is not None:
            ok_btn.setEnabled(all_valid)

    def _apply_preset(self, theme_key: str) -> None:
        """Fill all 9 QLineEdits with a preset and refresh swatches."""
        if theme_key not in THEMES:
            return
        self._current_theme_name = theme_key
        for key, value in THEMES[theme_key].items():
            if key in self._line_edits:
                self._line_edits[key].setText(value)
        # _on_text_changed is fired automatically by setText, but the OK
        # button state must be re-evaluated once at the end.
        self._refresh_ok_enabled()

    def _on_path_changed(self, text: str) -> None:
        """Update the fly_path inside the current flight kwargs."""
        self._current_flight_kwargs["fly_path"] = text

    def _on_provider_changed(self, text: str) -> None:
        """Enable/disable API Key input based on provider selection."""
        self._update_api_key_enabled(text)

    def _update_api_key_enabled(self, provider: str) -> None:
        """API Key is only needed for minimax."""
        is_minimax = provider == "minimax"
        self._api_key_label.setEnabled(is_minimax)
        self._api_key_edit.setEnabled(is_minimax)

    def _apply_flight_mode(self, mode_name: str) -> None:
        """Switch to a named flight mode preset (flight params only).

        Looks up the preset in :data:`FLIGHT_MODES` and records the
        mode's flight kwargs in :attr:`_current_flight_kwargs` so a
        subsequent call to :meth:`get_result` returns a complete
        :class:`AppConfig`.  Color fields are NOT touched.

        The live :class:`FlightWidget` is NOT updated here — the new
        flight kwargs take effect on the next application restart (a
        "重启生效" label next to the mode row makes this clear to the
        user).
        """
        if mode_name not in FLIGHT_MODES:
            return
        self._current_flight_mode = mode_name
        self._current_flight_kwargs = dict(FLIGHT_MODES[mode_name])

    @staticmethod
    def _parse_persona_prompts(raw: str) -> dict[str, str]:
        if not raw:
            return {}
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        if not isinstance(data, dict):
            return {}
        return {str(k): str(v) for k, v in data.items()}

    def _on_persona_preset_changed(self) -> None:
        from message_flight.plane_presets import get_preset
        new_key = self._persona_preset_combo.currentData()
        if not new_key:
            return
        # Save the in-progress edit under the OLD key before switching
        old_key = getattr(self, "_active_persona_key", None)
        if old_key and old_key != new_key:
            current_text = self._persona_prompt_edit.toPlainText()
            default_text = get_preset(old_key).system_prompt
            if current_text == default_text:
                self._persona_prompts.pop(old_key, None)
            else:
                self._persona_prompts[old_key] = current_text
        self._active_persona_key = new_key
        existing = self._persona_prompts.get(new_key, "")
        self._persona_prompt_edit.setPlainText(existing or get_preset(new_key).system_prompt)

    def _on_reset_persona_prompt(self) -> None:
        from message_flight.plane_presets import get_preset
        current_key = self._persona_preset_combo.currentData() or "airplane"
        self._persona_prompts.pop(current_key, None)
        self._persona_prompt_edit.setPlainText(get_preset(current_key).system_prompt)

    def get_persona_result(self) -> tuple[bool, str]:
        from message_flight.plane_presets import get_preset
        current_key = self._persona_preset_combo.currentData() or "airplane"
        edited = self._persona_prompt_edit.toPlainText()
        default = get_preset(current_key).system_prompt
        if edited == default:
            self._persona_prompts.pop(current_key, None)
        elif edited:
            self._persona_prompts[current_key] = edited
        return self._persona_enabled_checkbox.isChecked(), json.dumps(self._persona_prompts, ensure_ascii=False)
