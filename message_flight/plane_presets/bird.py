from __future__ import annotations

import math
from dataclasses import dataclass

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter, QPainterPath

from .base import ParamDef, PlanePreset


@dataclass
class BirdParameters:
    body_size: int = 20
    wing_span: int = 40
    body_color: str = "#4169E1"
    wing_color: str = "#1E90FF"
    beak_color: str = "#FFA500"
    eye_color: str = "#000000"
    wing_flap_speed: float = 4.0


class BirdPreset(PlanePreset):
    name = "小鸟"
    icon = "🐦"

    def __init__(self):
        self._animation_time = 0.0

    def draw(self, painter: QPainter, params: BirdParameters) -> None:
        bs = params.body_size
        ws = params.wing_span
        self._animation_time += 0.016  # ~60fps assumption
        phase = (math.sin(self._animation_time * params.wing_flap_speed) + 1.0) / 2.0
        wing_offset = int(ws // 2 * phase)
        painter.save()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(params.body_color))
        painter.drawEllipse(-bs // 2, -bs // 4, bs, bs // 2)
        painter.drawEllipse(bs // 4, -bs // 3, bs // 2, bs // 2)
        painter.setBrush(QColor(params.beak_color))
        beak = QPainterPath()
        beak.moveTo(bs * 3 // 4, -bs // 8)
        beak.lineTo(bs + 4, 0)
        beak.lineTo(bs * 3 // 4, bs // 8)
        beak.closeSubpath()
        painter.drawPath(beak)
        painter.setBrush(QColor(params.eye_color))
        painter.drawEllipse(bs // 2, -bs // 6, 2, 2)
        painter.setBrush(QColor(params.wing_color))
        wing_top = QPainterPath()
        wing_top.moveTo(-bs // 4, -bs // 4)
        wing_top.lineTo(-bs // 4 - wing_offset, -wing_offset)
        wing_top.lineTo(bs // 4, -bs // 4)
        wing_top.closeSubpath()
        painter.drawPath(wing_top)
        wing_bot = QPainterPath()
        wing_bot.moveTo(-bs // 4, bs // 4)
        wing_bot.lineTo(-bs // 4 - wing_offset, wing_offset)
        wing_bot.lineTo(bs // 4, bs // 4)
        wing_bot.closeSubpath()
        painter.drawPath(wing_bot)
        painter.restore()

    def get_parameters(self) -> list[ParamDef]:
        return [
            ParamDef("body_size", "身体大小", "int", 20, 10, 40),
            ParamDef("wing_span", "翼展", "int", 40, 20, 80),
            ParamDef("body_color", "身体颜色", "color", "#4169E1"),
            ParamDef("wing_color", "翅膀颜色", "color", "#1E90FF"),
            ParamDef("beak_color", "鸟喙颜色", "color", "#FFA500"),
            ParamDef("eye_color", "眼睛颜色", "color", "#000000"),
            ParamDef("wing_flap_speed", "扇翅速度", "float", 4.0, 0.0, 10.0, 0.5),
        ]

    def get_default_params(self) -> BirdParameters:
        return BirdParameters()
