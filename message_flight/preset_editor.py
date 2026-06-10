from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter
from PyQt6.QtWidgets import QWidget

from message_flight.plane_presets import PlanePreset


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
