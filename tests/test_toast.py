"""Tests for Toast widget and ToastManager (Task 13)."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import sys
from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtCore import QRect
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from message_flight.toast import Toast, ToastManager


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


def test_toast_widgets_populated(qapp):
    toast = Toast(title="Achievement Unlocked!", description="First Flight", icon="✈️")
    assert toast._title_label.text() == "Achievement Unlocked!"
    assert toast._description_label.text() == "First Flight"
    assert toast._icon_label.text() == "✈️"


def test_toast_auto_dismiss(qapp):
    toast = Toast(title="T", description="D", icon="i", timeout_ms=100)
    toast.show_toast()
    assert toast.isVisible()
    QTest.qWait(250)
    assert not toast.isVisible()


def test_manager_queues_toasts(qapp):
    manager = ToastManager()
    manager.show_toast(title="First", description="First desc", icon="1", timeout_ms=100)
    first = manager._current_toast
    assert first is not None
    assert first.isVisible()

    manager.show_toast(title="Second", description="Second desc", icon="2", timeout_ms=1000)
    QTest.qWait(250)
    second = manager._current_toast
    assert second is not None
    assert second is not first
    assert second.isVisible()
    assert not first.isVisible()


def test_manager_position_is_on_screen(qapp):
    available = QRect(0, 0, 1920, 1080)
    with patch("PyQt6.QtWidgets.QApplication.primaryScreen") as mock_screen:
        fake_screen = MagicMock()
        fake_screen.availableGeometry.return_value = available
        mock_screen.return_value = fake_screen

        manager = ToastManager()
        manager.show_toast(title="Title", description="Desc", icon="✈️", timeout_ms=100)
        toast = manager._current_toast
        assert toast is not None

        geo = toast.geometry()
        assert available.contains(geo.topLeft())
        assert available.contains(geo.bottomRight())
