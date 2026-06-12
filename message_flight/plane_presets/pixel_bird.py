"""Pixel Bird unlockable preset — 8-bit style with nearest-neighbor scaling."""
from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QImage, QPainter

from .base import ParamDef, PlanePreset

_PIXEL_MAP = [
    "  XXX  ",
    " XOOOX ",
    "XOOOOOX",
    "XOuuOOX",
    "XOOOOOX",
    "XOO OX ",
    " X   X ",
    "X     X",
]
_LEGEND = {
    " ": None,
    "X": "outline",
    "O": "body",
    "u": "belly",
}
_PIXEL_SCALE = 8
_CANVAS_OFFSET = (10, 10)


@dataclass
class PixelBirdParameters:
    body_color: str = "#FF4444"
    outline_color: str = "#000000"
    belly_color: str = "#FFE4B5"
    body_scale: float = 1.0
    text_color: str = "#000000"
    rotation: float = 0.0
    banner_attach_x: int = 0
    banner_attach_y: int = 30


class PixelBirdPreset(PlanePreset):
    name = "像素小鸟"
    icon = "🐤"
    system_prompt = (
        "你是一只像素小鸟。请用电子、复古游戏音效般的语气播报收到的系统通知。"
        "每条消息都以'♪'开头。简短有趣。"
    )
    tts_voice_id = "female-shaonv"
    tts_speed = 1.0
    tts_pitch = 4

    def draw(self, painter: QPainter, params: PixelBirdParameters) -> None:
        s = params.body_scale
        src = QImage(len(_PIXEL_MAP[0]), len(_PIXEL_MAP), QImage.Format.Format_ARGB32)
        src.fill(Qt.GlobalColor.transparent)
        palette = {
            "outline": params.outline_color,
            "body": params.body_color,
            "belly": params.belly_color,
        }
        for row, line in enumerate(_PIXEL_MAP):
            for col, ch in enumerate(line):
                key = _LEGEND.get(ch)
                if key is None:
                    continue
                src.setPixelColor(col, row, QColor(palette[key]))
        target = src.scaled(
            int(src.width() * _PIXEL_SCALE * s),
            int(src.height() * _PIXEL_SCALE * s),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )
        painter.drawImage(*_CANVAS_OFFSET, target)

    def get_parameters(self) -> list[ParamDef]:
        return [
            ParamDef("body_color", "主体", "color", "#FF4444"),
            ParamDef("outline_color", "轮廓", "color", "#000000"),
            ParamDef("belly_color", "腹部", "color", "#FFE4B5"),
            ParamDef("body_scale", "尺寸", "float", 1.0, 0.5, 2.0, 0.1),
            ParamDef("rotation", "旋转", "float", 0.0, -45.0, 45.0, 1.0),
            ParamDef("banner_attach_x", "横幅挂载X", "int", 0, -50, 100),
            ParamDef("banner_attach_y", "横幅挂载Y", "int", 30, -50, 100),
        ]

    def get_default_params(self) -> PixelBirdParameters:
        return PixelBirdParameters()
