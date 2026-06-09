"""Modal settings dialog for editing the 9-color plane/banner palette and the flight mode preset."""
from __future__ import annotations

from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from message_flight.config import (
    FLIGHT_MODE_NAMES,
    FLIGHT_MODES,
    VALID_FLY_PATHS,
    AppConfig,
    DEFAULT_THEME,
    THEMES,
)


# Human-readable label + the matching key in THEMES / AppConfig.colors
_COLOR_ROWS: tuple[tuple[str, str], ...] = (
    ("飞机主体", "plane_color"),
    ("机翼", "wing_color"),
    ("眼睛/高光", "accent_color"),
    ("小圆装饰", "decor_color"),
    ("横幅背景", "banner_color"),
    ("横幅文字", "text_color"),
    ("推进器外焰", "thruster_outer_color"),
    ("推进器中焰", "thruster_middle_color"),
    ("推进器内焰", "thruster_inner_color"),
)

# (button text, theme key) — must match ``THEMES`` keys in ``config.py``.
_PRESETS: tuple[tuple[str, str], ...] = (
    ("默认粉", "default"),
    ("复古绿", "retro"),
    ("未来赛博", "cyber"),
)


class SettingsDialog(QDialog):
    """A 9-row form for editing the plane color palette, plus 3 flight-mode + 3 color preset buttons.

    The dialog does not mutate the live widget directly; the caller is
    expected to call :meth:`get_result` after the dialog is accepted
    and then forward the new colors to ``PlaneBanner.update_colors``.
    """

    def __init__(self, initial: AppConfig, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("MessageFlight 设置")
        self.setModal(True)

        self._current_theme_name = initial.theme_name or DEFAULT_THEME
        self._line_edits: dict[str, QLineEdit] = {}
        self._swatches: dict[str, QLabel] = {}
        self._current_flight_mode: str = initial.flight_mode
        # Copy so external mutations to the AppConfig don't leak in/out.
        self._current_flight_kwargs: dict = dict(initial.flight_kwargs)
        self._flight_mode_buttons: dict[str, QPushButton] = {}

        root = QVBoxLayout(self)

        # Flight-mode row (Task 06) — sits at the TOP, above the color preset row
        flight_mode_row = QHBoxLayout()
        flight_mode_row.addWidget(QLabel("飞行模式:"))
        for mode_name in FLIGHT_MODE_NAMES:
            btn = QPushButton(mode_name)
            btn.clicked.connect(
                lambda _checked=False, name=mode_name: self._apply_flight_mode(name)
            )
            self._flight_mode_buttons[mode_name] = btn
            flight_mode_row.addWidget(btn)
        flight_mode_row.addWidget(QLabel("(重启生效)"))
        flight_mode_row.addStretch(1)
        root.addLayout(flight_mode_row)

        # Fly-path row
        path_row = QHBoxLayout()
        path_row.addWidget(QLabel("飞行路径:"))
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
        preset_row.addWidget(QLabel("配色:"))
        for label, theme_key in _PRESETS:
            btn = QPushButton(label)
            btn.clicked.connect(lambda _checked=False, key=theme_key: self._apply_preset(key))
            preset_row.addWidget(btn)
        preset_row.addStretch(1)
        root.addLayout(preset_row)

        # 9 color rows
        form = QFormLayout()
        for label_text, key in _COLOR_ROWS:
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
            form.addRow(label_text, row_widget)

        root.addLayout(form)

        # TTS Provider row
        provider_row = QHBoxLayout()
        provider_row.addWidget(QLabel("TTS 引擎:"))
        self._provider_combo = QComboBox()
        for p in ("sapi", "minimax"):
            self._provider_combo.addItem(p)
        self._provider_combo.setCurrentText(initial.tts_provider)
        self._provider_combo.currentTextChanged.connect(self._on_provider_changed)
        provider_row.addWidget(self._provider_combo)
        provider_row.addStretch(1)
        root.addLayout(provider_row)

        # API Key (enabled only for minimax)
        self._api_key_label = QLabel("MiniMax 订阅 Key:")
        self._api_key_edit = QLineEdit(initial.minimax_subscription_key)
        self._api_key_edit.setPlaceholderText("Token Plan 订阅 Key")
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
        return AppConfig(
            theme_name=self._current_theme_name,
            colors=colors,
            flight_mode=self._current_flight_mode,
            flight_kwargs=dict(self._current_flight_kwargs),
            online_tts_api_key=self._api_key_edit.text(),
            tts_provider=self._provider_combo.currentText(),
            minimax_subscription_key=self._api_key_edit.text(),
        )

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
