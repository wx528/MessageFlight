"""Declarative achievement definitions and trigger specs.

Each achievement is an `Achievement` dataclass with a `TriggerSpec` that
the AchievementEngine evaluates against a state snapshot. Triggers are
intentionally tiny — they answer "did the predicate fire?" with no
side effects.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class TriggerSpec(Protocol):
    """A predicate the engine evaluates against a state dict."""

    def evaluate(self, state: dict[str, Any]) -> bool: ...
    def state_for(self, **kwargs: Any) -> dict[str, Any] | None: ...


@dataclass(frozen=True)
class CounterTrigger:
    """Fires when the integer at state['count'] reaches target."""
    target: int
    _state_key: str = field(repr=False, default="count")

    def evaluate(self, state: dict[str, Any]) -> bool:
        return int(state.get(self._state_key, 0)) >= self.target

    def state_for(self, **kwargs: Any) -> dict[str, Any] | None:
        value = kwargs.get("notifications")
        if value is None:
            return None
        return {self._state_key: value}


@dataclass(frozen=True)
class ClicksTrigger:
    """Fires when the integer at state['count'] reaches target."""
    target: int
    _state_key: str = field(repr=False, default="count")

    def evaluate(self, state: dict[str, Any]) -> bool:
        return int(state.get(self._state_key, 0)) >= self.target

    def state_for(self, **kwargs: Any) -> dict[str, Any] | None:
        value = kwargs.get("clicks")
        if value is None:
            return None
        return {self._state_key: value}


@dataclass(frozen=True)
class TTSTrigger:
    """Fires when the integer at state['count'] reaches target."""
    target: int
    _state_key: str = field(repr=False, default="count")

    def evaluate(self, state: dict[str, Any]) -> bool:
        return int(state.get(self._state_key, 0)) >= self.target

    def state_for(self, **kwargs: Any) -> dict[str, Any] | None:
        value = kwargs.get("tts_count")
        if value is None:
            return None
        return {self._state_key: value}


@dataclass(frozen=True)
class DistinctSetTrigger:
    """Fires when the size of the set at state['set'] reaches target."""
    target: int

    def evaluate(self, state: dict[str, Any]) -> bool:
        return len(state.get("set", set())) >= self.target

    def state_for(self, **kwargs: Any) -> dict[str, Any] | None:
        value = kwargs.get("distinct_sources")
        if value is None:
            return None
        return {"set": value}


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

    def state_for(self, **kwargs: Any) -> dict[str, Any] | None:
        value = kwargs.get("hour")
        if value is None:
            return None
        return {"hour": value}


@dataclass(frozen=True)
class UsedAllPresetsTrigger:
    """Fires when state['presets_used'] is a superset of `required`."""
    required: frozenset[str] = field(default_factory=frozenset)

    def evaluate(self, state: dict[str, Any]) -> bool:
        return self.required.issubset(state.get("presets_used", set()))

    def state_for(self, **kwargs: Any) -> dict[str, Any] | None:
        value = kwargs.get("presets_used")
        if value is None:
            return None
        return {"presets_used": value}



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
    unlock_preset_key: str | None
    icon: str


TARGET_FIRST_NOTIFICATION = 1
TARGET_CENTURION = 100
TARGET_SOCIAL_BUTTERFLY = 5
TARGET_CLICKER = 10
TARGET_LOUD_MOUTH = 50

NIGHT_OWL_START = 0
NIGHT_OWL_END = 5
EARLY_BIRD_START = 5
EARLY_BIRD_END = 8

DEFAULT_PRESET_KEYS = frozenset({"airplane", "rocket", "ufo", "bird"})


ACHIEVEMENTS: list[Achievement] = [
    Achievement(
        id="first_flight",
        name_i18n_key="achievement.first_flight.name",
        description_i18n_key="achievement.first_flight.desc",
        trigger=CounterTrigger(target=TARGET_FIRST_NOTIFICATION),
        unlock_preset_key="sleigh",
        icon="🎅",
    ),
    Achievement(
        id="centurion",
        name_i18n_key="achievement.centurion.name",
        description_i18n_key="achievement.centurion.desc",
        trigger=CounterTrigger(target=TARGET_CENTURION),
        unlock_preset_key="duck",
        icon="🦆",
    ),
    Achievement(
        id="social_butterfly",
        name_i18n_key="achievement.social_butterfly.name",
        description_i18n_key="achievement.social_butterfly.desc",
        trigger=DistinctSetTrigger(target=TARGET_SOCIAL_BUTTERFLY),
        unlock_preset_key="rainbow_rocket",
        icon="🌈",
    ),
    Achievement(
        id="night_owl",
        name_i18n_key="achievement.night_owl.name",
        description_i18n_key="achievement.night_owl.desc",
        trigger=TimeOfDayTrigger(start_hour=NIGHT_OWL_START, end_hour=NIGHT_OWL_END),
        unlock_preset_key="gold_ufo",
        icon="✨",
    ),
    Achievement(
        id="early_bird",
        name_i18n_key="achievement.early_bird.name",
        description_i18n_key="achievement.early_bird.desc",
        trigger=TimeOfDayTrigger(start_hour=EARLY_BIRD_START, end_hour=EARLY_BIRD_END),
        unlock_preset_key="pixel_bird",
        icon="🐤",
    ),
    Achievement(
        id="clicker",
        name_i18n_key="achievement.clicker.name",
        description_i18n_key="achievement.clicker.desc",
        trigger=ClicksTrigger(target=TARGET_CLICKER),
        unlock_preset_key=None,
        icon="🏆",
    ),
    Achievement(
        id="loud_mouth",
        name_i18n_key="achievement.loud_mouth.name",
        description_i18n_key="achievement.loud_mouth.desc",
        trigger=TTSTrigger(target=TARGET_LOUD_MOUTH),
        unlock_preset_key=None,
        icon="🏆",
    ),
    Achievement(
        id="try_them_all",
        name_i18n_key="achievement.try_them_all.name",
        description_i18n_key="achievement.try_them_all.desc",
        trigger=UsedAllPresetsTrigger(required=DEFAULT_PRESET_KEYS),
        unlock_preset_key=None,
        icon="🏆",
    ),
]
