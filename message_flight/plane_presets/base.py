from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional

from PyQt6.QtGui import QPainter


@dataclass
class ParamDef:
    name: str
    label: str
    type: str
    default: Any
    min: Optional[Any] = None
    max: Optional[Any] = None
    step: Optional[Any] = None


class PlanePreset(ABC):
    name: str = ""
    icon: str = ""
    system_prompt: str = ""
    tts_voice_id: str = ""
    tts_speed: float = 1.0
    tts_pitch: int = 0

    @abstractmethod
    def draw(self, painter: QPainter, params: Any) -> None:
        pass

    @abstractmethod
    def get_parameters(self) -> list[ParamDef]:
        pass

    @abstractmethod
    def get_default_params(self) -> Any:
        pass
