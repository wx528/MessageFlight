"""Declarative achievement definitions and trigger specs.

Each achievement is an `Achievement` dataclass with a `TriggerSpec` that
the AchievementEngine evaluates against a state snapshot. Triggers are
intentionally tiny — they answer "did the predicate fire?" with no
side effects.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Protocol, runtime_checkable


@runtime_checkable
class TriggerSpec(Protocol):
    """A predicate the engine evaluates against a state dict."""

    def evaluate(self, state: dict[str, Any]) -> bool: ...


@dataclass(frozen=True)
class CounterTrigger:
    """Fires when the integer at state['count'] reaches target."""
    target: int

    def evaluate(self, state: dict[str, Any]) -> bool:
        return int(state.get("count", 0)) >= self.target


@dataclass(frozen=True)
class DistinctSetTrigger:
    """Fires when the size of the set at state['set'] reaches target."""
    target: int

    def evaluate(self, state: dict[str, Any]) -> bool:
        return len(state.get("set", set())) >= self.target


@dataclass(frozen=True)
class TimeOfDayTrigger:
    """Fires when the hour at state['hour'] falls in [start, end).

    Start inclusive, end exclusive. Allows midnight-spanning windows
    like 22-6 by the caller constructing two triggers.
    """
    start_hour: int
    end_hour: int

    def evaluate(self, state: dict[str, Any]) -> bool:
        h = int(state.get("hour", -1))
        if h < 0:
            return False
        return self.start_hour <= h < self.end_hour


@dataclass(frozen=True)
class UsedAllPresetsTrigger:
    """Fires when state['presets_used'] is a superset of `required`."""
    required: frozenset[str]

    def __init__(self, required: set[str] | frozenset[str]):
        object.__setattr__(self, "required", frozenset(required))

    def evaluate(self, state: dict[str, Any]) -> bool:
        return self.required.issubset(state.get("presets_used", set()))


# ---------------------------------------------------------------------------
# Achievement dataclass and registry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Achievement:
    """A single achievement entry.

    `id` must be unique across the registry. `unlock_preset_key` is
    None for milestone badges that don't unlock a new preset.
    """
    id: str
    name_i18n_key: str
    description_i18n_key: str
    trigger: TriggerSpec
    unlock_preset_key: Optional[str]
    icon: str


ACHIEVEMENTS: list[Achievement] = [
    Achievement(
        id="first_flight",
        name_i18n_key="achievement.first_flight.name",
        description_i18n_key="achievement.first_flight.desc",
        trigger=CounterTrigger(target=1),
        unlock_preset_key="sleigh",
        icon="🎅",
    ),
    Achievement(
        id="centurion",
        name_i18n_key="achievement.centurion.name",
        description_i18n_key="achievement.centurion.desc",
        trigger=CounterTrigger(target=100),
        unlock_preset_key="duck",
        icon="🦆",
    ),
    Achievement(
        id="social_butterfly",
        name_i18n_key="achievement.social_butterfly.name",
        description_i18n_key="achievement.social_butterfly.desc",
        trigger=DistinctSetTrigger(target=5),
        unlock_preset_key="rainbow_rocket",
        icon="🌈",
    ),
    Achievement(
        id="night_owl",
        name_i18n_key="achievement.night_owl.name",
        description_i18n_key="achievement.night_owl.desc",
        trigger=TimeOfDayTrigger(start_hour=0, end_hour=5),
        unlock_preset_key="gold_ufo",
        icon="✨",
    ),
    Achievement(
        id="early_bird",
        name_i18n_key="achievement.early_bird.name",
        description_i18n_key="achievement.early_bird.desc",
        trigger=TimeOfDayTrigger(start_hour=5, end_hour=8),
        unlock_preset_key="pixel_bird",
        icon="🐤",
    ),
    Achievement(
        id="clicker",
        name_i18n_key="achievement.clicker.name",
        description_i18n_key="achievement.clicker.desc",
        trigger=CounterTrigger(target=10),
        unlock_preset_key=None,
        icon="🏆",
    ),
    Achievement(
        id="loud_mouth",
        name_i18n_key="achievement.loud_mouth.name",
        description_i18n_key="achievement.loud_mouth.desc",
        trigger=CounterTrigger(target=50),
        unlock_preset_key=None,
        icon="🏆",
    ),
    Achievement(
        id="try_them_all",
        name_i18n_key="achievement.try_them_all.name",
        description_i18n_key="achievement.try_them_all.desc",
        trigger=UsedAllPresetsTrigger(required={"airplane", "rocket", "ufo", "bird"}),
        unlock_preset_key=None,
        icon="🏆",
    ),
]
