"""Persistent chat window for the LLM Agent.

Displays a scrollable conversation history with user messages and
agent responses (both text and tool-call results). The window can
be toggled from the tray icon menu or via the "open settings" voice
command path.

Design:
    - Frameless, semi-transparent overlay in the bottom-right corner
    - Auto-scrolls to the latest message
    - Supports text input for keyboard-based interaction
    - Closes on Escape, toggles from tray menu
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QKeyEvent, QPalette
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from message_flight.i18n import tr


class _MessageBubble(QFrame):
    """A single chat message bubble."""

    def __init__(self, text: str, is_user: bool = False, is_system: bool = False,
                 icon: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.NoFrame)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        # Icon
        icon_label = QLabel(icon or ("🤖" if not is_user else "🎤"))
        icon_label.setFixedWidth(28)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(icon_label)

        # Text
        text_label = QLabel(text)
        text_label.setWordWrap(True)
        text_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        if is_user:
            bg = QColor(60, 130, 246, 40)
            text_label.setStyleSheet("color: #93c5fd;")
        elif is_system:
            bg = QColor(234, 179, 8, 30)
            text_label.setStyleSheet("color: #fcd34d;")
        else:
            bg = QColor(74, 222, 128, 30)
            text_label.setStyleSheet("color: #86efac;")

        self.setStyleSheet(
            f"QFrame {{ background-color: rgba({bg.red()},{bg.green()},{bg.blue()},{bg.alpha()}); "
            f"border-radius: 8px; padding: 4px; }}"
        )
        layout.addWidget(text_label, 1)


class AgentChatWindow(QWidget):
    """Persistent chat window for the LLM Agent.

    Signals:
        text_submitted(text): User typed a message and pressed Enter.
    """

    text_submitted = pyqtSignal(str)

    _WINDOW_WIDTH = 420
    _WINDOW_HEIGHT = 520

    def __init__(self, language: str = "zh", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._language = language
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(self._WINDOW_WIDTH, self._WINDOW_HEIGHT)

        # Main container
        container = QWidget(self)
        container.setStyleSheet(
            "QWidget { background-color: rgba(30, 30, 46, 240); border-radius: 12px; }"
        )
        container.setGeometry(0, 0, self._WINDOW_WIDTH, self._WINDOW_HEIGHT)

        outer = QVBoxLayout(container)
        outer.setContentsMargins(0, 0, 0, 0)

        # Title bar
        title_bar = QWidget()
        title_bar.setFixedHeight(36)
        title_bar.setStyleSheet("background-color: rgba(49, 50, 68, 200); border-top-left-radius: 12px; border-top-right-radius: 12px;")
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(12, 0, 12, 0)

        title_label = QLabel(f"🤖 {tr('agent.chat_title', self._language)}")
        title_label.setStyleSheet("color: #cdd6f4; font-weight: bold; font-size: 13px;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        close_btn = QLabel("✕")
        close_btn.setStyleSheet("color: #a6adc8; font-size: 14px; padding: 4px;")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.mousePressEvent = lambda _: self.hide()  # type: ignore
        title_layout.addWidget(close_btn)

        outer.addWidget(title_bar)

        # Chat area
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }"
            "QScrollBar:vertical { width: 6px; background: transparent; }"
            "QScrollBar::handle:vertical { background: rgba(166,173,200,80); border-radius: 3px; }"
        )

        self._chat_container = QWidget()
        self._chat_container.setStyleSheet("background: transparent;")
        self._chat_layout = QVBoxLayout(self._chat_container)
        self._chat_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._chat_layout.setSpacing(4)
        self._chat_layout.addStretch()
        self._scroll.setWidget(self._chat_container)
        outer.addWidget(self._scroll, 1)

        # Input bar
        input_bar = QWidget()
        input_bar.setFixedHeight(40)
        input_bar.setStyleSheet("background-color: rgba(49, 50, 68, 200); border-bottom-left-radius: 12px; border-bottom-right-radius: 12px;")
        input_layout = QHBoxLayout(input_bar)
        input_layout.setContentsMargins(12, 4, 12, 4)

        self._input = QLineEdit()
        self._input.setPlaceholderText(tr("agent.input_placeholder", self._language))
        self._input.setStyleSheet(
            "QLineEdit { background-color: rgba(30, 30, 46, 200); color: #cdd6f4; "
            "border: 1px solid rgba(166,173,200,60); border-radius: 6px; padding: 4px 8px; }"
            "QLineEdit::placeholder { color: #6c7086; }"
        )
        self._input.returnPressed.connect(self._on_return_pressed)
        input_layout.addWidget(self._input)

        outer.addWidget(input_bar)

    def add_user_message(self, text: str) -> None:
        """Add a user message bubble."""
        self._add_bubble(text, is_user=True, icon="🎤")

    def add_agent_message(self, text: str) -> None:
        """Add an agent text response bubble."""
        self._add_bubble(text, is_user=False, icon="🤖")

    def add_system_message(self, text: str, icon: str = "⚙") -> None:
        """Add a system/tool message bubble."""
        self._add_bubble(text, is_system=True, icon=icon)

    def add_tool_result(self, server: str, tool: str, result: str, icon: str = "🔗") -> None:
        """Add a tool result bubble."""
        short = result[:200] + ("..." if len(result) > 200 else "")
        self._add_bubble(f"[{server}/{tool}] {short}", is_system=True, icon=icon)

    def clear_chat(self) -> None:
        """Remove all messages."""
        while self._chat_layout.count() > 1:
            item = self._chat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _add_bubble(self, text: str, is_user: bool = False, is_system: bool = False,
                    icon: str = "") -> None:
        bubble = _MessageBubble(text, is_user=is_user, is_system=is_system, icon=icon)
        # Insert before the stretch at the end
        self._chat_layout.insertWidget(self._chat_layout.count() - 1, bubble)
        # Auto-scroll to bottom
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(50, self._scroll_to_bottom)

    def _scroll_to_bottom(self) -> None:
        scrollbar = self._scroll.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _on_return_pressed(self) -> None:
        text = self._input.text().strip()
        if text:
            self.add_user_message(text)
            self.text_submitted.emit(text)
            self._input.clear()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
        else:
            super().keyPressEvent(event)

    def show_at_cursor(self) -> None:
        """Position the window near the bottom-right of the screen and show it."""
        screen = self.screen().availableGeometry()
        x = screen.right() - self._WINDOW_WIDTH - 16
        y = screen.bottom() - self._WINDOW_HEIGHT - 16
        self.move(x, y)
        self.show()
        self._input.setFocus()
