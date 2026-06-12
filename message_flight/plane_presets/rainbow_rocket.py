"""Rainbow Rocket unlockable preset."""
from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter, QPainterPath

from .base import ParamDef, PlanePreset

_RAINBOW = ["#FF0000", "#FF7F00", "#FFFF00", "#00FF00", "#0000FF", "#4B0082", "#9400D3"]


@dataclass
class RainbowRocketParameters:
    window_color: str = "#87CEEB"
    accent_color: str = "#FFFFFF"
    body_scale: float = 1.0
    text_color: str = "#FFFFFF"
    rotation: float = 0.0
    banner_attach_x: int = 0
    banner_attach_y: int = 30


class RainbowRocketPreset(PlanePreset):
    name = "彩虹航天飞机"
    icon = "🌈"
    system_prompt = (
        "你是一架彩虹航天飞机。请用活泼、欢快的语气播报收到的系统通知。"
        "每条消息后面加一个'✦'。保持短小精悍。"
    )
    tts_voice_id = "female-yujie"
    tts_speed = 1.2
    tts_pitch = 2

    def draw(self, painter: QPainter, params: RainbowRocketParameters) -> None:
        s = params.body_scale
        painter.setPen(Qt.PenStyle.NoPen)
        rocket = QPainterPath()
        rocket.moveTo(int(10 * s), int(30 * s))
        rocket.cubicTo(int(20 * s), int(10 * s), int(70 * s), int(10 * s), int(80 * s), int(30 * s))
        rocket.lineTo(int(80 * s), int(45 * s))
        rocket.lineTo(int(10 * s), int(45 * s))
        rocket.closeSubpath()
        painter.drawPath(rocket)
        for i, hex_color in enumerate(_RAINBOW):
            y0 = int(15 * s) + i * int(4 * s)
            painter.setBrush(QColor(hex_color))
            painter.drawRect(int(10 * s), y0, int(70 * s), int(4 * s))
        painter.setBrush(QColor(params.window_color))
        painter.drawEllipse(int(35 * s), int(20 * s), int(15 * s), int(15 * s))
        painter.setBrush(QColor(params.accent_color))
        painter.drawEllipse(int(38 * s), int(22 * s), int(6 * s), int(6 * s))

    def get_parameters(self) -> list[ParamDef]:
        return [
            ParamDef("window_color", "舷窗", "color", "#87CEEB"),
            ParamDef("accent_color", "高光", "color", "#FFFFFF"),
            ParamDef("body_scale", "尺寸", "float", 1.0, 0.5, 2.0, 0.1),
            ParamDef("rotation", "旋转", "float", 0.0, -45.0, 45.0, 1.0),
            ParamDef("banner_attach_x", "横幅挂载X", "int", 0, -50, 100),
            ParamDef("banner_attach_y", "横幅挂载Y", "int", 30, -50, 100),
        ]

    def get_default_params(self) -> RainbowRocketParameters:
        return RainbowRocketParameters()
