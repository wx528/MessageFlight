"""Rubber Duck unlockable preset."""
from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter, QPainterPath

from .base import ParamDef, PlanePreset


@dataclass
class DuckParameters:
    body_color: str = "#FFD700"
    beak_color: str = "#FF8C00"
    eye_color: str = "#000000"
    highlight_color: str = "#FFFFFF"
    body_scale: float = 1.0
    text_color: str = "#000000"
    rotation: float = 0.0
    banner_attach_x: int = 0
    banner_attach_y: int = 30


class DuckPreset(PlanePreset):
    name = "小黄鸭"
    icon = "🦆"
    system_prompt = (
        "你是一只小黄鸭。请用呆萌、好奇的语气播报收到的系统通知。"
        "每条消息都以'嘎'开头。保持轻松幽默。"
    )
    tts_voice_id = "female-shaonv"
    tts_speed = 1.1
    tts_pitch = 3

    def draw(self, painter: QPainter, params: DuckParameters) -> None:
        s = params.body_scale
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(params.body_color))
        painter.drawEllipse(int(10 * s), int(25 * s), int(60 * s), int(30 * s))
        painter.drawEllipse(int(50 * s), int(15 * s), int(30 * s), int(30 * s))
        painter.setBrush(QColor(params.beak_color))
        beak = QPainterPath()
        beak.moveTo(int(78 * s), int(28 * s))
        beak.lineTo(int(92 * s), int(30 * s))
        beak.lineTo(int(78 * s), int(33 * s))
        beak.closeSubpath()
        painter.drawPath(beak)
        painter.setBrush(QColor(params.eye_color))
        painter.drawEllipse(int(65 * s), int(22 * s), int(4 * s), int(4 * s))
        painter.setBrush(QColor(params.highlight_color))
        painter.drawEllipse(int(20 * s), int(30 * s), int(20 * s), int(8 * s))

    def get_parameters(self) -> list[ParamDef]:
        return [
            ParamDef("body_color", "鸭身", "color", "#FFD700"),
            ParamDef("beak_color", "嘴", "color", "#FF8C00"),
            ParamDef("eye_color", "眼睛", "color", "#000000"),
            ParamDef("highlight_color", "高光", "color", "#FFFFFF"),
            ParamDef("body_scale", "尺寸", "float", 1.0, 0.5, 2.0, 0.1),
            ParamDef("rotation", "旋转", "float", 0.0, -45.0, 45.0, 1.0),
            ParamDef("banner_attach_x", "横幅挂载X", "int", 0, -50, 100),
            ParamDef("banner_attach_y", "横幅挂载Y", "int", 30, -50, 100),
        ]

    def get_default_params(self) -> DuckParameters:
        return DuckParameters()
