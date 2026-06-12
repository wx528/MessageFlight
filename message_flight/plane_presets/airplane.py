from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter, QPainterPath

from .base import ParamDef, PlanePreset


@dataclass
class AirplaneParameters:
    plane_color: str = "#FF69B4"
    wing_color: str = "#FF1493"
    accent_color: str = "#FFFFFF"
    decor_color: str = "#FF69B4"
    banner_color: str = "#FFB6C1"
    thruster_outer_color: str = "#FFA500"
    thruster_middle_color: str = "#FF4500"
    thruster_inner_color: str = "#FFFF00"
    body_scale: float = 1.0
    text_color: str = "#FFFFFF"
    rotation: float = 0.0
    banner_attach_x: int = 0
    banner_attach_y: int = 30


class AirplanePreset(PlanePreset):
    name = "飞机"
    icon = "✈️"
    system_prompt = (
        "你是这架客机的机长。请用简短、专业、亲切的语气播报收到的系统通知。"
        "始终称呼用户为'机长'。把通知中的英文应用保留，并以一句中文开头。"
        "不要超过 40 个汉字。"
    )
    tts_voice_id = "male-qn-qingse"
    tts_speed = 1.0
    tts_pitch = 0

    def draw(self, painter: QPainter, params: AirplaneParameters) -> None:
        s = params.body_scale
        painter.save()
        self._draw_thruster(painter, params, s)
        self._draw_fuselage(painter, params, s)
        self._draw_wings(painter, params, s)
        painter.restore()

    def get_parameters(self) -> list[ParamDef]:
        return [
            ParamDef("plane_color", "飞机主体", "color", "#FF69B4"),
            ParamDef("wing_color", "机翼", "color", "#FF1493"),
            ParamDef("accent_color", "眼睛/高光", "color", "#FFFFFF"),
            ParamDef("decor_color", "小圆装饰", "color", "#FF69B4"),
            ParamDef("banner_color", "横幅装饰", "color", "#FFB6C1"),
            ParamDef("thruster_outer_color", "推进器外焰", "color", "#FFA500"),
            ParamDef("thruster_middle_color", "推进器中焰", "color", "#FF4500"),
            ParamDef("thruster_inner_color", "推进器内焰", "color", "#FFFF00"),
            ParamDef("body_scale", "机身缩放", "float", 1.0, 0.5, 2.0, 0.1),
            ParamDef("rotation", "旋转角度", "float", 0.0, -45.0, 45.0, 1.0),
            ParamDef("banner_attach_x", "横幅挂载X", "int", 0, -50, 100),
            ParamDef("banner_attach_y", "横幅挂载Y", "int", 30, -50, 100),
        ]

    def get_default_params(self) -> AirplaneParameters:
        return AirplaneParameters()

    @staticmethod
    def _draw_fuselage(painter, params, s):
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(params.plane_color))
        painter.drawEllipse(int(10*s), int(18*s), int(45*s), int(22*s))
        painter.drawEllipse(int(48*s), int(19*s), int(14*s), int(20*s))
        painter.setBrush(QColor(params.accent_color))
        painter.drawEllipse(int(52*s), int(24*s), int(6*s), int(6*s))
        painter.drawEllipse(int(38*s), int(24*s), int(5*s), int(5*s))
        painter.setBrush(QColor(params.decor_color))
        painter.drawEllipse(int(60*s), int(26*s), int(4*s), int(6*s))
        painter.setBrush(QColor(params.banner_color))
        painter.drawEllipse(int(56*s), int(22*s), int(12*s), int(3*s))
        painter.drawEllipse(int(56*s), int(33*s), int(12*s), int(3*s))

    @staticmethod
    def _draw_wings(painter, params, s):
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(params.wing_color))
        wing_path = QPainterPath()
        wing_path.moveTo(int(25*s), int(25*s))
        wing_path.lineTo(int(15*s), int(8*s))
        wing_path.lineTo(int(35*s), int(8*s))
        wing_path.lineTo(int(40*s), int(25*s))
        wing_path.closeSubpath()
        painter.drawPath(wing_path)
        tail_path = QPainterPath()
        tail_path.moveTo(int(12*s), int(28*s))
        tail_path.lineTo(int(2*s), int(18*s))
        tail_path.lineTo(int(12*s), int(22*s))
        tail_path.closeSubpath()
        painter.drawPath(tail_path)

    @staticmethod
    def _draw_thruster(painter, params, s, intensity=1.0):
        painter.setPen(Qt.PenStyle.NoPen)
        outer_w = int(14 * intensity * s)
        painter.setBrush(QColor(params.thruster_outer_color))
        painter.drawEllipse(int(5*s), int(25*s), outer_w, int(10*s))
        mid_w = int(10 * intensity * s)
        painter.setBrush(QColor(params.thruster_middle_color))
        painter.drawEllipse(int(5*s), int(26*s), mid_w, int(7*s))
        inner_w = int(5 * intensity * s)
        painter.setBrush(QColor(params.thruster_inner_color))
        painter.drawEllipse(int(5*s), int(27*s), inner_w, int(4*s))
