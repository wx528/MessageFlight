"""QObject that tracks progression and emits unlock signals."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from PyQt6.QtCore import QObject, pyqtSignal

from message_flight.achievements import ACHIEVEMENTS
from message_flight.config import GamificationState

logger = logging.getLogger(__name__)

_PROGRESS_KEY_NOTIFICATIONS = "_notifications"
_PROGRESS_KEY_FIRED_MILESTONES = "_fired_milestones"


class AchievementEngine(QObject):
    """Tracks achievement progress and emits signals on unlocks.

    Signals:
        unlocked(achievement_id): Fires once per achievement that has
            a preset reward. state.unlocked_presets is updated first.
        milestone(achievement_id): Fires once per milestone (no preset).
    """

    unlocked = pyqtSignal(str)
    milestone = pyqtSignal(str)

    def __init__(self, state: GamificationState, parent: QObject | None = None):
        super().__init__(parent)
        self._state = state
        self._notifications: int = state.achievement_progress.get(_PROGRESS_KEY_NOTIFICATIONS, 0)
        self._fired: set[str] = set()
        fired_milestones = self._fired_milestones()
        for a in ACHIEVEMENTS:
            if a.id in fired_milestones or (
                a.unlock_preset_key and a.unlock_preset_key in state.unlocked_presets
            ):
                self._fired.add(a.id)

    def _fired_milestones(self) -> set[str]:
        return set(self._state.achievement_progress.get(_PROGRESS_KEY_FIRED_MILESTONES, []))

    def record_notification(self, source: str) -> None:
        if source:
            self._state.distinct_notification_sources.add(source)
        self._notifications += 1
        self._evaluate()

    def record_plane_click(self) -> None:
        self._state.clicks += 1
        self._evaluate()

    def record_tts_speak(self) -> None:
        self._state.tts_count += 1
        self._evaluate()

    def record_preset_used(self, key: str) -> None:
        if key:
            self._state.presets_used.add(key)
        self._evaluate()

    def check_time_based(self) -> None:
        """Re-evaluate achievements that depend on the current time."""
        self._evaluate()

    def _evaluate(self) -> None:
        state_for = self._build_state()
        for a in ACHIEVEMENTS:
            if a.id in self._fired:
                continue
            state = state_for.get(a.id)
            if state is None:
                continue
            if not a.trigger.evaluate(state):
                continue
            self._fired.add(a.id)
            if a.unlock_preset_key:
                self._state.unlocked_presets.add(a.unlock_preset_key)
                self.unlocked.emit(a.id)
                logger.info("Achievement unlocked: %s -> %s", a.id, a.unlock_preset_key)
            else:
                fired_milestones = self._fired_milestones()
                fired_milestones.add(a.id)
                self._state.achievement_progress[_PROGRESS_KEY_FIRED_MILESTONES] = sorted(fired_milestones)
                self.milestone.emit(a.id)
                logger.info("Milestone hit: %s", a.id)

        self._state.achievement_progress[_PROGRESS_KEY_NOTIFICATIONS] = self._notifications

    def _build_state(self) -> dict[str, dict[str, Any]]:
        hour = datetime.now().hour
        state_for: dict[str, dict[str, Any]] = {}
        for a in ACHIEVEMENTS:
            state = a.trigger.state_for(
                notifications=self._notifications,
                clicks=self._state.clicks,
                tts_count=self._state.tts_count,
                distinct_sources=self._state.distinct_notification_sources,
                presets_used=self._state.presets_used,
                hour=hour,
            )
            if state is not None:
                state_for[a.id] = state
        return state_for
