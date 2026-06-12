"""Frameless toast popup and sequential ToastManager."""
from typing import List, Optional, Tuple

from PyQt6.QtCore import QObject, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)


class Toast(QWidget):
    """A frameless, non-focusable toast notification widget."""

    dismissed = pyqtSignal()

    def __init__(
        self,
        title: str = "",
        description: str = "",
        icon: str = "",
        timeout_ms: int = 4000,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._timeout_ms = timeout_ms
        self._setup_ui()
        self.set_toast(title, description, icon)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._on_timeout)

    def _setup_ui(self) -> None:
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self._container = QFrame(self)
        self._container.setStyleSheet(
            "QFrame {"
            "  background-color: rgba(40, 40, 40, 220);"
            "  border-radius: 8px;"
            "  padding: 12px;"
            "}"
            "QLabel {"
            "  color: white;"
            "  background: transparent;"
            "}"
        )

        self._icon_label = QLabel(self._container)
        icon_font = QFont()
        icon_font.setPointSize(24)
        self._icon_label.setFont(icon_font)

        self._title_label = QLabel(self._container)
        title_font = QFont()
        title_font.setBold(True)
        self._title_label.setFont(title_font)

        self._description_label = QLabel(self._container)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        text_layout.addWidget(self._title_label)
        text_layout.addWidget(self._description_label)

        main_layout = QHBoxLayout(self._container)
        main_layout.setSpacing(10)
        main_layout.addWidget(self._icon_label)
        main_layout.addLayout(text_layout)

        outer_layout = QHBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(self._container)

    def set_toast(self, title: str, description: str, icon: str) -> None:
        self._title_label.setText(title)
        self._description_label.setText(description)
        self._icon_label.setText(icon)
        self.adjustSize()

    def show_toast(self) -> None:
        self.adjustSize()
        self.show()
        self._timer.start(self._timeout_ms)

    def _on_timeout(self) -> None:
        self.hide()
        self.dismissed.emit()


class ToastManager(QObject):
    """Queues toasts and shows them one at a time near the top-right of the screen."""

    def __init__(self, margin: int = 16, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._margin = margin
        self._queue: List[Tuple[str, str, str, int]] = []
        self._current_toast: Optional[Toast] = None

    def show_toast(
        self, title: str, description: str, icon: str, timeout_ms: int = 4000
    ) -> None:
        self._queue.append((title, description, icon, timeout_ms))
        self._show_next()

    def _show_next(self) -> None:
        if self._current_toast is not None or not self._queue:
            return
        title, description, icon, timeout_ms = self._queue.pop(0)
        toast = Toast(title, description, icon, timeout_ms)
        toast.dismissed.connect(self._on_toast_finished)
        self._current_toast = toast
        self._position_toast(toast)
        toast.show_toast()

    def _position_toast(self, toast: Toast) -> None:
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        available = screen.availableGeometry()
        toast.adjustSize()
        x = available.right() - toast.width() - self._margin
        y = available.top() + self._margin
        toast.move(x, y)

    def _on_toast_finished(self) -> None:
        self._current_toast = None
        self._show_next()
