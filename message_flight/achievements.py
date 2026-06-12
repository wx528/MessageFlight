"""Declarative achievement definitions and trigger specs.

Each achievement is an `Achievement` dataclass with a `TriggerSpec` that
the AchievementEngine evaluates against a state snapshot. Triggers are
intentionally tiny — they answer "did the predicate fire?" with no
side effects.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


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
# Achievement dataclass and registry live in Tasks 3 & 4
# ---------------------------------------------------------------------------
