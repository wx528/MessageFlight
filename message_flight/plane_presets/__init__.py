from __future__ import annotations

from typing import Type

from .airplane import AirplanePreset
from .base import PlanePreset
from .bird import BirdPreset
from .rocket import RocketPreset
from .sleigh import SleighPreset
from .ufo import UFOPreset

PRESETS: dict[str, Type[PlanePreset]] = {
    "airplane": AirplanePreset,
    "rocket": RocketPreset,
    "ufo": UFOPreset,
    "bird": BirdPreset,
}


def get_preset(key: str) -> PlanePreset:
    if key in PRESETS:
        return PRESETS[key]()
    if key in UNLOCKABLE_PRESETS:
        return UNLOCKABLE_PRESETS[key]()
    raise KeyError(key)


def list_presets() -> list[tuple[str, str, str]]:
    return [(k, p.name, p.icon) for k, p in PRESETS.items()]


UNLOCKABLE_PRESETS: dict[str, type[PlanePreset]] = {
    "sleigh": SleighPreset,
}
