from __future__ import annotations

from typing import Type

from .airplane import AirplanePreset
from .base import PlanePreset
from .bird import BirdPreset
from .duck import DuckPreset
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
    if key in UNLOCKABLE_PRESETS:
        return UNLOCKABLE_PRESETS[key]()
    if key not in PRESETS:
        key = "airplane"
    return PRESETS[key]()


def list_presets() -> list[tuple[str, str, str]]:
    return [(k, p.name, p.icon) for k, p in PRESETS.items()]


UNLOCKABLE_PRESETS: dict[str, type[PlanePreset]] = {
    "duck": DuckPreset,
    "sleigh": SleighPreset,
}
