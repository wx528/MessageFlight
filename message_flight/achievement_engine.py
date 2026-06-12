"""QObject that tracks progression and emits unlock signals."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

from PyQt6.QtCore import QObject, pyqtSignal

from message_flight.achievements import ACHIEVEMENTS
from message_flight.config import AppConfig

logger = logging.getLogger(__name__)


class AchievementEngine(QObject):
    """Tracks achievement progress and emits signals on unlocks.

    Signals:
        unlocked(achievement_id): Fires once per achievement that has
            a preset reward. cfg.unlocked_presets is updated first.
        milestone(achievement_id): Fires once per milestone (no preset).
    """

    unlocked = pyqtSignal(str)
    milestone = pyqtSignal(str)

    def __init__(self, cfg: AppConfig, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._cfg = cfg
        # Session counter for notifications (cfg.achievement_progress persists
        # across restarts, but this counter tracks notifications since process start)
        self._notifications: int = cfg.achievement_progress.get("_notifications", 0)
        # Achievements already fired this session; also skip ones already
        # unlocked in cfg (idempotent across restarts)
        self._fired: set[str] = set()
        fired_milestones = set(self._cfg.achievement_progress.get("_fired_milestones", []))
        for a in ACHIEVEMENTS:
            if a.id in fired_milestones or (
                a.unlock_preset_key and a.unlock_preset_key in cfg.unlocked_presets
            ):
                self._fired.add(a.id)

    def record_notification(self, source: str) -> None:
        if source:
            self._cfg.distinct_notification_sources.add(source)
        self._notifications += 1
        self._evaluate()

    def record_plane_click(self) -> None:
        self._cfg.clicks += 1
        self._evaluate()

    def record_tts_speak(self) -> None:
        self._cfg.tts_count += 1
        self._evaluate()

    def record_preset_used(self, key: str) -> None:
        if key:
            self._cfg.presets_used.add(key)
        self._evaluate()

    def check_time_based(self) -> None:
        """Re-evaluate achievements that depend on the current time."""
        self._evaluate()

    def _evaluate(self) -> None:
        hour = datetime.now().hour
        state_for: dict[str, dict[str, Any]] = {
            "first_flight": {"count": self._notifications},
            "centurion": {"count": self._notifications},
            "social_butterfly": {"set": self._cfg.distinct_notification_sources},
            "night_owl": {"hour": hour},
            "early_bird": {"hour": hour},
            "clicker": {"count": self._cfg.clicks},
            "loud_mouth": {"count": self._cfg.tts_count},
            "try_them_all": {"presets_used": self._cfg.presets_used},
        }
        for a in ACHIEVEMENTS:
            if a.id in self._fired:
                continue
            if not a.trigger.evaluate(state_for[a.id]):
                continue
            self._fired.add(a.id)
            if a.unlock_preset_key:
                self._cfg.unlocked_presets.add(a.unlock_preset_key)
                self.unlocked.emit(a.id)
                logger.info("Achievement unlocked: %s -> %s", a.id, a.unlock_preset_key)
            else:
                fired_milestones = set(self._cfg.achievement_progress.get("_fired_milestones", []))
                fired_milestones.add(a.id)
                self._cfg.achievement_progress["_fired_milestones"] = fired_milestones
                self.milestone.emit(a.id)
                logger.info("Milestone hit: %s", a.id)

        # Persist session notification count for restart recovery
        self._cfg.achievement_progress["_notifications"] = self._notifications
