from __future__ import annotations

import dataclasses
import json
from typing import Optional, cast

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
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
from message_flight.i18n import tr
from message_flight.plane_presets import get_preset, list_presets
from message_flight.plane_presets.base import PlanePreset


class PresetPreviewWidget(QWidget):
    _CENTER_X = 100
    _CENTER_Y = 75
    _GRAB_RADIUS = 10

    def __init__(self, preset: PlanePreset, params, on_mount_changed=None, parent=None):
        super().__init__(parent)
        self._preset = preset
        self._params = params
        self._on_mount_changed = on_mount_changed
        self._dragging = False
        self.setFixedSize(200, 150)
        self.setCursor(Qt.CursorShape.CrossCursor)

    def update_preset(self, preset) -> None:
        """Replace the active preset and request a repaint."""
        self._preset = preset
        self.update()

    def update_params(self, params) -> None:
        self._params = params
        self.update()

    def _get_mount(self) -> tuple[int, int]:
        return (
            getattr(self._params, "banner_attach_x", 0),
            getattr(self._params, "banner_attach_y", 0),
        )

    def _set_mount(self, mx: int, my: int) -> None:
        if hasattr(self._params, "banner_attach_x"):
            self._params.banner_attach_x = int(mx)
        if hasattr(self._params, "banner_attach_y"):
            self._params.banner_attach_y = int(my)
        if self._on_mount_changed is not None:
            self._on_mount_changed(mx, my)
        self.update()

    # ------------------------------------------------------------------
    # 鼠标事件
    # ------------------------------------------------------------------
    def mousePressEvent(self, event):
        mx, my = self._world_to_mount(event.pos())
        cur_mx, cur_my = self._get_mount()
        dist = ((mx - cur_mx) ** 2 + (my - cur_my) ** 2) ** 0.5
        if dist < self._GRAB_RADIUS:
            self._dragging = True
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        else:
            self._set_mount(mx, my)

    def mouseMoveEvent(self, event):
        if self._dragging:
            mx, my = self._world_to_mount(event.pos())
            self._set_mount(mx, my)

    def mouseReleaseEvent(self, event):
        if self._dragging:
            self._dragging = False
            self.setCursor(Qt.CursorShape.CrossCursor)

    def _world_to_mount(self, pos) -> tuple[int, int]:
        return int(pos.x() - self._CENTER_X), int(pos.y() - self._CENTER_Y)

    # ------------------------------------------------------------------
    # 绘制
    # ------------------------------------------------------------------
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#f5f5f5"))

        # 轻微网格线
        pen = QPen(QColor("#e0e0e0"))
        pen.setWidth(1)
        painter.setPen(pen)
        for x in range(0, 201, 20):
            painter.drawLine(x, 0, x, 150)
        for y in range(0, 151, 20):
            painter.drawLine(0, y, 200, y)

        # 飞船原点（中心点）
        painter.setPen(QPen(QColor("#888888"), 1))
        painter.drawEllipse(self._CENTER_X - 2, self._CENTER_Y - 2, 4, 4)

        # 绘制飞船（translate 到中心）
        painter.translate(self._CENTER_X, self._CENTER_Y)
        self._preset.draw(painter, self._params)
        painter.translate(-self._CENTER_X, -self._CENTER_Y)

        # 挂载点
        mx, my = self._get_mount()
        wx = self._CENTER_X + mx
        wy = self._CENTER_Y + my

        # 虚线连接
        dash = QPen(QColor("#FF5722"), 1, Qt.PenStyle.DotLine)
        painter.setPen(dash)
        painter.drawLine(self._CENTER_X, self._CENTER_Y, wx, wy)

        # 挂载点手柄
        painter.setPen(QPen(QColor("#D32F2F"), 2))
        painter.setBrush(QColor("#FF5252"))
        painter.drawEllipse(wx - 5, wy - 5, 10, 10)

        # 坐标标签
        painter.setPen(QColor("#333333"))
        font = QFont("Microsoft YaHei", 8)
        painter.setFont(font)
        label = f"({mx}, {my})"
        painter.drawText(wx + 8, wy + 4, label)

        painter.end()


class PresetEditorWindow(QDialog):
    def __init__(self, cfg: AppConfig, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._language = cfg.language
        self.setWindowTitle(tr("preset_editor.title", self._language))
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
        top_row.addWidget(QLabel(tr("preset_editor.preset", self._language)))
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

        # 预览 + 拖拽回调
        self._preview = PresetPreviewWidget(
            preset_obj, self._params,
            on_mount_changed=self._on_preview_mount_changed,
        )
        middle.addWidget(self._preview)
        root.addLayout(middle)

        self._button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self._button_box.accepted.connect(self.accept)
        self._button_box.rejected.connect(self.reject)
        root.addWidget(self._button_box)

        self._build_param_panel()

    def _on_preview_mount_changed(self, mx: int, my: int) -> None:
        """预览拖拽时同步更新参数面板中的 SpinBox。"""
        for name in ("banner_attach_x", "banner_attach_y"):
            spin = self._param_widgets.get(name)
            if spin is not None:
                value = mx if name == "banner_attach_x" else my
                spin_box = cast(QSpinBox, spin)
                spin_box.blockSignals(True)
                spin_box.setValue(value)
                spin_box.blockSignals(False)

    def _refresh_preview(self) -> None:
        self._preview.update_params(self._params)

    def _on_preset_changed(self, index: int) -> None:
        key = self._preset_combo.itemData(index)
        self._preset_key = key
        preset_obj = get_preset(key)
        self._params = preset_obj.get_default_params()
        self._build_param_panel()
        self._preview.update_preset(preset_obj)
        self._refresh_preview()

    def _build_param_panel(self) -> None:
        while self._param_layout.count():
            item = self._param_layout.takeAt(0)
            if item is None:
                continue
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
                        chosen = QColorDialog.getColor(
                            current,
                            self,
                            tr("preset_editor.choose_color", self._language, label=_label),
                        )
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
                double_spin = QDoubleSpinBox()
                double_spin.setRange(
                    float(param_def.min) if param_def.min is not None else 0.0,
                    float(param_def.max) if param_def.max is not None else 999.0,
                )
                if param_def.step is not None:
                    double_spin.setSingleStep(float(param_def.step))
                double_spin.setValue(float(value))
                double_spin.valueChanged.connect(
                    lambda v, _n=param_def.name: self._on_float_changed(_n, v)
                )
                self._param_layout.addRow(param_def.label, double_spin)
                self._param_widgets[param_def.name] = double_spin
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
