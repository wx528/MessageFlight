"""Collection tab for browsing plane presets and their unlock status."""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QGridLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from message_flight.achievements import Achievement
from message_flight.plane_presets import PRESETS, UNLOCKABLE_PRESETS


class PlanePresetCard(QWidget):
    """A small card showing a plane preset icon, name, and lock state."""

    clicked = pyqtSignal(str)

    def __init__(
        self,
        key: str,
        name: str,
        icon: str,
        locked: bool,
        unlock_achievement_name: Optional[str] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.preset_key = key
        self.locked = locked

        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(8, 8, 8, 8)

        self._icon_label = QLabel(icon if icon else "✈️")
        self._icon_label.setStyleSheet("font-size: 32px;")
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._icon_label)

        self._name_label = QLabel(name)
        self._name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._name_label)

        self._lock_label = QLabel()
        self._lock_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._lock_label)

        if locked:
            self._lock_label.setText("🔒 Locked")
            self.setStyleSheet("background-color: #f0f0f0; color: #888888;")
            self._name_label.setEnabled(False)
            self._icon_label.setEnabled(False)
        else:
            self._lock_label.setText("")
            self.setStyleSheet("background-color: #ffffff; color: #000000;")

        if locked and unlock_achievement_name:
            self._lock_label.setToolTip(f"Unlock via: {unlock_achievement_name}")

    def mousePressEvent(self, event) -> None:  # noqa: D401
        self.clicked.emit(self.preset_key)
        super().mousePressEvent(event)


class CollectionTab(QWidget):
    """A scrollable grid of all plane presets with unlock indicators."""

    def __init__(
        self,
        unlocked_presets: set[str],
        achievements: list[Achievement],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)

        unlock_map: dict[str, str] = {
            a.unlock_preset_key: a.name_i18n_key
            for a in achievements
            if a.unlock_preset_key is not None
        }

        self._cards: list[PlanePresetCard] = []

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        container = QWidget()
        grid = QGridLayout(container)
        grid.setSpacing(12)
        grid.setContentsMargins(12, 12, 12, 12)

        col = 0
        row = 0
        max_cols = 4

        for key, cls in list(PRESETS.items()) + list(UNLOCKABLE_PRESETS.items()):
            locked = key not in unlocked_presets and key in UNLOCKABLE_PRESETS
            achievement_name = unlock_map.get(key) if locked else None
            card = PlanePresetCard(
                key=key,
                name=cls.name,
                icon=cls.icon,
                locked=locked,
                unlock_achievement_name=achievement_name,
            )
            self._cards.append(card)
            grid.addWidget(card, row, col)
            col += 1
            if col >= max_cols:
                col = 0
                row += 1

        grid.setRowStretch(row + 1, 1)
        grid.setColumnStretch(max_cols, 1)
        scroll.setWidget(container)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

    def cards(self) -> list[PlanePresetCard]:
        """Return the list of preset cards shown in the tab."""
        return list(self._cards)
