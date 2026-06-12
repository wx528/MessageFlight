"""Christmas Sleigh unlockable preset."""
from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter, QPainterPath

from .base import ParamDef, PlanePreset


@dataclass
class SleighParameters:
    body_color: str = "#C8102E"
    trim_color: str = "#0B6E3F"
    runner_color: str = "#8B4513"
    accent_color: str = "#FFD700"
    snow_color: str = "#FFFFFF"
    body_scale: float = 1.0
    text_color: str = "#FFFFFF"
    rotation: float = 0.0
    banner_attach_x: int = 0
    banner_attach_y: int = 30


class SleighPreset(PlanePreset):
    name = "圣诞飞艇"
    icon = "🎅"
    system_prompt = (
        "你是圣诞老人。请用温暖、欢乐的语气播报收到的系统通知。"
        "始终称呼用户为'圣诞老人'。不要超过 40 个汉字。"
    )
    tts_voice_id = "male-qn-jingying"
    tts_speed = 0.9
    tts_pitch = 1

    def draw(self, painter: QPainter, params: SleighParameters) -> None:
        s = params.body_scale
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(params.body_color))
        body = QPainterPath()
        body.moveTo(int(10 * s), int(35 * s))
        body.cubicTo(int(10 * s), int(20 * s), int(50 * s), int(15 * s), int(80 * s), int(25 * s))
        body.lineTo(int(80 * s), int(40 * s))
        body.lineTo(int(10 * s), int(40 * s))
        body.closeSubpath()
        painter.drawPath(body)
        painter.setBrush(QColor(params.trim_color))
        painter.drawRect(int(10 * s), int(15 * s), int(70 * s), int(6 * s))
        painter.setBrush(QColor(params.accent_color))
        star_x, star_y = int(35 * s), int(8 * s)
        for i in range(5):
            painter.drawEllipse(star_x + i * 3, star_y, 3, 3)
        painter.setBrush(QColor(params.runner_color))
        painter.drawRect(int(8 * s), int(40 * s), int(78 * s), int(4 * s))
        painter.drawRect(int(8 * s), int(44 * s), int(78 * s), int(2 * s))
        painter.setBrush(QColor(params.snow_color))
        for x, y in [(20, 50), (40, 52), (60, 50), (30, 55), (55, 54)]:
            painter.drawEllipse(int(x * s), int(y * s), 3, 3)

    def get_parameters(self) -> list[ParamDef]:
        return [
            ParamDef("body_color", "主体", "color", "#C8102E"),
            ParamDef("trim_color", "绿边", "color", "#0B6E3F"),
            ParamDef("runner_color", "滑撬", "color", "#8B4513"),
            ParamDef("accent_color", "金色装饰", "color", "#FFD700"),
            ParamDef("snow_color", "雪花", "color", "#FFFFFF"),
            ParamDef("body_scale", "尺寸", "float", 1.0, 0.5, 2.0, 0.1),
            ParamDef("rotation", "旋转", "float", 0.0, -45.0, 45.0, 1.0),
            ParamDef("banner_attach_x", "横幅挂载X", "int", 0, -50, 100),
            ParamDef("banner_attach_y", "横幅挂载Y", "int", 30, -50, 100),
        ]

    def get_default_params(self) -> SleighParameters:
        return SleighParameters()
