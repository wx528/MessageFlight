"""Gold UFO unlockable preset."""
from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter, QPainterPath

from .base import ParamDef, PlanePreset


@dataclass
class GoldUFOParameters:
    body_color: str = "#FFD700"
    dome_color: str = "#87CEEB"
    beam_color: str = "#FFFFE0"
    accent_color: str = "#B8860B"
    body_scale: float = 1.0
    text_color: str = "#000000"
    rotation: float = 0.0
    banner_attach_x: int = 0
    banner_attach_y: int = 30


class GoldUFOPreset(PlanePreset):
    name = "黄金 UFO"
    icon = "✨"
    system_prompt = (
        "你是一艘黄金 UFO。请用神秘、平静的语气播报收到的系统通知。"
        "每条消息都以'哔——'开头。保持简短。"
    )
    tts_voice_id = "male-qn-qingse"
    tts_speed = 0.95
    tts_pitch = -1

    def draw(self, painter: QPainter, params: GoldUFOParameters) -> None:
        s = params.body_scale
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(params.beam_color))
        beam = QPainterPath()
        beam.moveTo(int(35 * s), int(45 * s))
        beam.lineTo(int(20 * s), int(70 * s))
        beam.lineTo(int(60 * s), int(70 * s))
        beam.lineTo(int(55 * s), int(45 * s))
        beam.closeSubpath()
        painter.drawPath(beam)
        painter.setBrush(QColor(params.body_color))
        painter.drawEllipse(int(15 * s), int(30 * s), int(60 * s), int(18 * s))
        painter.setBrush(QColor(params.accent_color))
        painter.drawEllipse(int(20 * s), int(42 * s), int(50 * s), int(6 * s))
        painter.setBrush(QColor(params.dome_color))
        painter.drawEllipse(int(30 * s), int(15 * s), int(30 * s), int(20 * s))
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawEllipse(int(36 * s), int(18 * s), int(8 * s), int(8 * s))

    def get_parameters(self) -> list[ParamDef]:
        return [
            ParamDef("body_color", "碟身", "color", "#FFD700"),
            ParamDef("dome_color", "顶罩", "color", "#87CEEB"),
            ParamDef("beam_color", "光束", "color", "#FFFFE0"),
            ParamDef("accent_color", "底盘", "color", "#B8860B"),
            ParamDef("body_scale", "尺寸", "float", 1.0, 0.5, 2.0, 0.1),
            ParamDef("rotation", "旋转", "float", 0.0, -45.0, 45.0, 1.0),
            ParamDef("banner_attach_x", "横幅挂载X", "int", 0, -50, 100),
            ParamDef("banner_attach_y", "横幅挂载Y", "int", 30, -50, 100),
        ]

    def get_default_params(self) -> GoldUFOParameters:
        return GoldUFOParameters()
