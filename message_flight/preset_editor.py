from __future__ import annotations

import dataclasses
import json
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from message_flight.config import AppConfig
from message_flight.plane_presets import get_preset, list_presets
from message_flight.plane_presets.base import PlanePreset


class PresetPreviewWidget(QWidget):
    def __init__(self, preset: PlanePreset, params, parent=None):
        super().__init__(parent)
        self._preset = preset
        self._params = params
        self.setFixedSize(200, 150)

    def update_params(self, params) -> None:
        self._params = params
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.translate(100, 75)
        self._preset.draw(painter, self._params)
        painter.end()


class PresetEditorWindow(QDialog):
    def __init__(self, cfg: AppConfig, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("飞船编辑器")
        self.setModal(True)
        self._cfg = cfg
        self._preset_key = cfg.plane_preset_key or "airplane"
        preset_obj = get_preset(self._preset_key)
        if cfg.plane_preset_params_json:
            try:
                data = json.loads(cfg.plane_preset_params_json)
                default = preset_obj.get_default_params()
                self._params = dataclasses.replace(
                    default,
                    **{k: v for k, v in data.items() if hasattr(default, k)},
                )
            except (json.JSONDecodeError, TypeError):
                self._params = preset_obj.get_default_params()
        else:
            self._params = preset_obj.get_default_params()
        self._param_widgets: dict[str, QWidget] = {}

        root = QVBoxLayout(self)
        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("预设:"))
        self._preset_combo = QComboBox()
        for key, name, icon in list_presets():
            self._preset_combo.addItem(f"{icon} {name}", key)
        idx = next(
            (i for i in range(self._preset_combo.count())
             if self._preset_combo.itemData(i) == self._preset_key),
            0,
        )
        self._preset_combo.setCurrentIndex(idx)
        self._preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        top_row.addWidget(self._preset_combo)
        top_row.addStretch(1)
        root.addLayout(top_row)

        middle = QHBoxLayout()
        self._param_panel = QWidget()
        self._param_layout = QFormLayout(self._param_panel)
        scroll = QScrollArea()
        scroll.setWidget(self._param_panel)
        scroll.setWidgetResizable(True)
        scroll.setFixedWidth(280)
        middle.addWidget(scroll)
        self._preview = PresetPreviewWidget(preset_obj, self._params)
        middle.addWidget(self._preview)
        root.addLayout(middle)

        self._button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self._button_box.accepted.connect(self.accept)
        self._button_box.rejected.connect(self.reject)
        root.addWidget(self._button_box)

        self._build_param_panel()

    def _refresh_preview(self) -> None:
        self._preview.update_params(self._params)

    def _on_preset_changed(self, index: int) -> None:
        key = self._preset_combo.itemData(index)
        self._preset_key = key
        preset_obj = get_preset(key)
        self._params = preset_obj.get_default_params()
        self._build_param_panel()
        self._preview._preset = preset_obj
        self._refresh_preview()

    def _build_param_panel(self) -> None:
        while self._param_layout.count():
            item = self._param_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self._param_widgets.clear()
        preset_obj = get_preset(self._preset_key)
        for param_def in preset_obj.get_parameters():
            value = getattr(self._params, param_def.name)
            if param_def.type == "color":
                row_widget = QWidget()
                row_layout = QHBoxLayout(row_widget)
                row_layout.setContentsMargins(0, 0, 0, 0)
                edit = QLineEdit(str(value))
                swatch = QLabel()
                swatch.setFixedSize(24, 18)
                qc = QColor(str(value))
                swatch.setStyleSheet(
                    f"background-color: {qc.name() if qc.isValid() else '#888888'};"
                )

                def make_picker(_edit=edit, _swatch=swatch, _n=param_def.name, _label=param_def.label):
                    def open_picker():
                        current = QColor(_edit.text())
                        chosen = QColorDialog.getColor(current, self, f"选择 {_label}")
                        if chosen.isValid():
                            _edit.setText(chosen.name())
                            _swatch.setStyleSheet(
                                f"background-color: {chosen.name()};"
                            )
                            setattr(self._params, _n, chosen.name())
                            self._refresh_preview()
                    return open_picker
                picker_btn = QPushButton("…")
                picker_btn.setFixedWidth(30)
                picker_btn.clicked.connect(make_picker())
                edit.textChanged.connect(
                    lambda text, _e=edit, _s=swatch, _n=param_def.name:
                        self._on_color_text_changed(_n, text, _e, _s)
                )
                row_layout.addWidget(edit)
                row_layout.addWidget(swatch)
                row_layout.addWidget(picker_btn)
                self._param_layout.addRow(param_def.label, row_widget)
                self._param_widgets[param_def.name] = edit
            elif param_def.type == "int":
                spin = QSpinBox()
                spin.setRange(
                    int(param_def.min) if param_def.min is not None else 0,
                    int(param_def.max) if param_def.max is not None else 999,
                )
                spin.setValue(int(value))
                spin.valueChanged.connect(
                    lambda v, _n=param_def.name: self._on_int_changed(_n, v)
                )
                self._param_layout.addRow(param_def.label, spin)
                self._param_widgets[param_def.name] = spin
            elif param_def.type == "float":
                spin = QDoubleSpinBox()
                spin.setRange(
                    float(param_def.min) if param_def.min is not None else 0.0,
                    float(param_def.max) if param_def.max is not None else 999.0,
                )
                if param_def.step is not None:
                    spin.setSingleStep(float(param_def.step))
                spin.setValue(float(value))
                spin.valueChanged.connect(
                    lambda v, _n=param_def.name: self._on_float_changed(_n, v)
                )
                self._param_layout.addRow(param_def.label, spin)
                self._param_widgets[param_def.name] = spin
            elif param_def.type == "bool":
                cb = QCheckBox()
                cb.setChecked(bool(value))
                cb.toggled.connect(
                    lambda checked, _n=param_def.name: self._on_bool_changed(_n, checked)
                )
                self._param_layout.addRow(param_def.label, cb)
                self._param_widgets[param_def.name] = cb

    def _on_color_text_changed(self, name, text, edit, swatch) -> None:
        qc = QColor(text)
        if qc.isValid():
            swatch.setStyleSheet(f"background-color: {qc.name()};")
        setattr(self._params, name, text)
        self._refresh_preview()

    def _on_int_changed(self, name, value) -> None:
        setattr(self._params, name, int(value))
        self._refresh_preview()

    def _on_float_changed(self, name, value) -> None:
        setattr(self._params, name, float(value))
        self._refresh_preview()

    def _on_bool_changed(self, name, value) -> None:
        setattr(self._params, name, bool(value))
        self._refresh_preview()

    def get_result(self) -> tuple[str, str]:
        data = dataclasses.asdict(self._params)
        return (self._preset_key, json.dumps(data, ensure_ascii=False))
