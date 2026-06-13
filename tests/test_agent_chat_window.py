"""Tests for the Agent Chat Window."""
from __future__ import annotations

import pytest

from PyQt6.QtWidgets import QWidget

from message_flight.agent_chat_window import AgentChatWindow, _MessageBubble


@pytest.fixture
def chat_window(qtbot):
    w = AgentChatWindow(language="zh")
    qtbot.addWidget(w)
    return w


class TestAgentChatWindowInit:
    def test_creates_without_crash(self, chat_window):
        assert chat_window is not None
        assert not chat_window.isVisible()

    def test_has_input_field(self, chat_window):
        assert chat_window._input is not None


class TestAddMessages:
    def test_add_user_message(self, chat_window):
        chat_window.add_user_message("hello")
        # Should have 2 items in layout: bubble + stretch
        assert chat_window._chat_layout.count() == 2

    def test_add_agent_message(self, chat_window):
        chat_window.add_agent_message("hi there")
        assert chat_window._chat_layout.count() == 2

    def test_add_system_message(self, chat_window):
        chat_window.add_system_message("calling tool...", icon="🔗")
        assert chat_window._chat_layout.count() == 2

    def test_add_tool_result(self, chat_window):
        chat_window.add_tool_result("obsidian", "search", '{"files": []}')
        assert chat_window._chat_layout.count() == 2

    def test_multiple_messages(self, chat_window):
        chat_window.add_user_message("hello")
        chat_window.add_agent_message("hi")
        chat_window.add_system_message("tool call")
        # 3 bubbles + 1 stretch = 4
        assert chat_window._chat_layout.count() == 4


class TestClearChat:
    def test_clear_removes_messages(self, chat_window):
        chat_window.add_user_message("hello")
        chat_window.add_agent_message("hi")
        chat_window.clear_chat()
        # Only stretch remains
        assert chat_window._chat_layout.count() == 1


class TestTextSubmitted:
    def test_enter_emits_signal(self, chat_window, qtbot):
        chat_window._input.setText("test message")
        with qtbot.waitSignal(chat_window.text_submitted, timeout=1000) as blocker:
            chat_window._input.returnPressed.emit()
        assert blocker.args == ["test message"]

    def test_enter_clears_input(self, chat_window, qtbot):
        chat_window._input.setText("test")
        chat_window._input.returnPressed.emit()
        assert chat_window._input.text() == ""

    def test_empty_input_not_submitted(self, chat_window, qtbot):
        chat_window._input.setText("   ")
        emitted = []
        chat_window.text_submitted.connect(lambda t: emitted.append(t))
        chat_window._input.returnPressed.emit()
        assert emitted == []


class TestShowAtCursor:
    def test_show_positions_window(self, chat_window):
        chat_window.show_at_cursor()
        assert chat_window.isVisible()
        chat_window.hide()


class TestMessageBubble:
    def test_user_bubble(self, qtbot):
        parent = QWidget()
        qtbot.addWidget(parent)
        bubble = _MessageBubble("test", is_user=True, parent=parent)
        assert bubble is not None

    def test_system_bubble(self, qtbot):
        parent = QWidget()
        qtbot.addWidget(parent)
        bubble = _MessageBubble("test", is_system=True, parent=parent)
        assert bubble is not None
