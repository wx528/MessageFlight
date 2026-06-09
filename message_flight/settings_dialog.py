"""Modal settings dialog for editing the 9-color plane/banner palette."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
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

from message_flight.config import AppConfig, DEFAULT_THEME, THEMES


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
    """A 9-row form for editing the plane color palette, plus 3 preset buttons.

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

        root = QVBoxLayout(self)

        # Preset row
        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("预设:"))
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
        return AppConfig(theme_name=self._current_theme_name, colors=colors)

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
