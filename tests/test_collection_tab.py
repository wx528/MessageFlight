"""Tests for CollectionTab and PlanePresetCard (Task 15)."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import sys

import pytest
from PyQt6.QtWidgets import QApplication

from message_flight.achievements import ACHIEVEMENTS


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


def _card_for_key(tab, key: str):
    from message_flight.collection_tab import PlanePresetCard

    for card in tab.findChildren(PlanePresetCard):
        if card.preset_key == key:
            return card
    raise AssertionError(f"No card found for preset {key!r}")


def test_collection_tab_shows_all_presets(qapp):
    from message_flight.collection_tab import CollectionTab, PlanePresetCard

    tab = CollectionTab(unlocked_presets=set(), achievements=ACHIEVEMENTS)

    cards = tab.findChildren(PlanePresetCard)
    assert len(cards) == 9


def test_unlocked_cards_not_locked(qapp):
    from message_flight.collection_tab import CollectionTab

    tab = CollectionTab(unlocked_presets={"duck"}, achievements=ACHIEVEMENTS)
    card = _card_for_key(tab, "duck")
    assert card.locked is False


def test_locked_card_has_lock_indicator(qapp):
    from message_flight.collection_tab import CollectionTab

    tab = CollectionTab(unlocked_presets=set(), achievements=ACHIEVEMENTS, language="en")
    card = _card_for_key(tab, "duck")
    assert card.locked is True
    assert "Locked" in card._lock_label.text()


def test_unlocked_default_cards(qapp):
    from message_flight.collection_tab import CollectionTab

    tab = CollectionTab(unlocked_presets=set(), achievements=ACHIEVEMENTS)
    for key in ("airplane", "rocket", "ufo", "bird"):
        card = _card_for_key(tab, key)
        assert card.locked is False
