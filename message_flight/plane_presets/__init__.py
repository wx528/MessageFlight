from __future__ import annotations

from typing import Type

from .base import PlanePreset
from .airplane import AirplanePreset
from .rocket import RocketPreset
from .ufo import UFOPreset
from .bird import BirdPreset

PRESETS: dict[str, Type[PlanePreset]] = {
    "airplane": AirplanePreset,
    "rocket": RocketPreset,
    "ufo": UFOPreset,
    "bird": BirdPreset,
}


def get_preset(key: str) -> PlanePreset:
    if key not in PRESETS:
        key = "airplane"
    return PRESETS[key]()


def list_presets() -> list[tuple[str, str, str]]:
    return [(k, p.name, p.icon) for k, p in PRESETS.items()]
