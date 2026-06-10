from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter, QPainterPath

from .base import ParamDef, PlanePreset


@dataclass
class UFOParameters:
    disc_radius: int = 30
    dome_radius: int = 15
    beam_width: int = 20
    beam_length: int = 25
    disc_color: str = "#808080"
    dome_color: str = "#C0C0C0"
    beam_color: str = "#00FF00"
    glow_intensity: float = 0.8
    banner_color: str = "#9370DB"
    text_color: str = "#FFFFFF"
    banner_attach_x: int = -30
    banner_attach_y: int = 0


class UFOPreset(PlanePreset):
    name = "UFO"
    icon = "🛸"

    def draw(self, painter: QPainter, params: UFOParameters) -> None:
        dr = params.disc_radius
        dor = params.dome_radius
        bw = params.beam_width
        bl = params.beam_length
        painter.save()
        beam_color = QColor(params.beam_color)
        beam_color.setAlphaF(0.3 * params.glow_intensity)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(beam_color)
        beam = QPainterPath()
        beam.moveTo(-bw // 2, 0)
        beam.lineTo(bw // 2, 0)
        beam.lineTo(bw, bl)
        beam.lineTo(-bw, bl)
        beam.closeSubpath()
        painter.drawPath(beam)
        painter.setBrush(QColor(params.disc_color))
        painter.drawEllipse(-dr, -dr // 2, dr * 2, dr)
        painter.setBrush(QColor(params.dome_color))
        painter.drawEllipse(-dor // 2, -dr - dor // 2, dor, dor)
        painter.restore()

    def get_parameters(self) -> list[ParamDef]:
        return [
            ParamDef("disc_radius", "圆盘半径", "int", 30, 10, 60),
            ParamDef("dome_radius", "圆顶半径", "int", 15, 5, 30),
            ParamDef("beam_width", "光束宽度", "int", 20, 5, 40),
            ParamDef("beam_length", "光束长度", "int", 25, 5, 50),
            ParamDef("disc_color", "圆盘颜色", "color", "#808080"),
            ParamDef("dome_color", "圆顶颜色", "color", "#C0C0C0"),
            ParamDef("beam_color", "光束颜色", "color", "#00FF00"),
            ParamDef("glow_intensity", "发光强度", "float", 0.8, 0.0, 1.0, 0.1),
            ParamDef("banner_color", "横幅颜色", "color", "#9370DB"),
            ParamDef("text_color", "文字颜色", "color", "#FFFFFF"),
            ParamDef("banner_attach_x", "横幅挂载X", "int", -30, -50, 100),
            ParamDef("banner_attach_y", "横幅挂载Y", "int", 0, -50, 100),
        ]

    def get_default_params(self) -> UFOParameters:
        return UFOParameters()
