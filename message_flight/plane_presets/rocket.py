from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter, QPainterPath

from .base import ParamDef, PlanePreset


@dataclass
class RocketParameters:
    body_length: int = 60
    body_width: int = 16
    nose_length: int = 20
    fin_size: int = 12
    flame_length: int = 15
    body_color: str = "#C0C0C0"
    nose_color: str = "#FF4500"
    fin_color: str = "#8B0000"
    flame_color: str = "#FFA500"
    flame_intensity: float = 1.0
    banner_color: str = "#FF6347"
    text_color: str = "#FFFFFF"
    rotation: float = 0.0
    banner_attach_x: int = -12
    banner_attach_y: int = 0


class RocketPreset(PlanePreset):
    name = "火箭"
    icon = "🚀"
    system_prompt = (
        "你是这艘火箭的舰长。请用科幻、果断的语气播报收到的系统通知。"
        "始终称呼用户为'舰长'。将原文压缩到 30 个汉字以内。"
    )

    def draw(self, painter: QPainter, params: RocketParameters) -> None:
        bl = params.body_length
        bw = params.body_width
        nl = params.nose_length
        fs = params.fin_size
        fl = params.flame_length
        painter.save()
        # Nose cone (triangle pointing right)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(params.nose_color))
        nose = QPainterPath()
        nose.moveTo(bl, -bw // 2)
        nose.lineTo(bl + nl, 0)
        nose.lineTo(bl, bw // 2)
        nose.closeSubpath()
        painter.drawPath(nose)
        # Body
        painter.setBrush(QColor(params.body_color))
        painter.drawRect(0, -bw // 2, bl, bw)
        # Fins (two triangles at left end)
        painter.setBrush(QColor(params.fin_color))
        fin_top = QPainterPath()
        fin_top.moveTo(0, -bw // 2)
        fin_top.lineTo(-fs, -bw // 2 - fs)
        fin_top.lineTo(0, -bw // 2 + fs // 2)
        fin_top.closeSubpath()
        painter.drawPath(fin_top)
        fin_bot = QPainterPath()
        fin_bot.moveTo(0, bw // 2)
        fin_bot.lineTo(-fs, bw // 2 + fs)
        fin_bot.lineTo(0, bw // 2 - fs // 2)
        fin_bot.closeSubpath()
        painter.drawPath(fin_bot)
        # Flame
        fl_actual = int(fl * params.flame_intensity)
        if fl_actual > 0:
            painter.setBrush(QColor(params.flame_color))
            painter.drawEllipse(-fl_actual, -bw // 4, fl_actual, bw // 2)
        painter.restore()

    def get_parameters(self) -> list[ParamDef]:
        return [
            ParamDef("body_length", "机身长度", "int", 60, 30, 100),
            ParamDef("body_width", "机身宽度", "int", 16, 8, 32),
            ParamDef("nose_length", "机头长度", "int", 20, 10, 50),
            ParamDef("fin_size", "尾翼大小", "int", 12, 4, 24),
            ParamDef("flame_length", "火焰长度", "int", 15, 5, 40),
            ParamDef("body_color", "机身颜色", "color", "#C0C0C0"),
            ParamDef("nose_color", "机头颜色", "color", "#FF4500"),
            ParamDef("fin_color", "尾翼颜色", "color", "#8B0000"),
            ParamDef("flame_color", "火焰颜色", "color", "#FFA500"),
            ParamDef("flame_intensity", "火焰强度", "float", 1.0, 0.0, 2.0, 0.1),
            ParamDef("banner_color", "横幅颜色", "color", "#FF6347"),
            ParamDef("rotation", "旋转角度", "float", 0.0, -45.0, 45.0, 1.0),
            ParamDef("text_color", "文字颜色", "color", "#FFFFFF"),
            ParamDef("banner_attach_x", "横幅挂载X", "int", -12, -50, 100),
            ParamDef("banner_attach_y", "横幅挂载Y", "int", 0, -50, 100),
        ]

    def get_default_params(self) -> RocketParameters:
        return RocketParameters()
