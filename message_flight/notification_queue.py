"""FIFO notification queue with bounded capacity.

The queue drops the oldest item when capacity is exceeded so that a
notification flood (e.g. a chat app ping-spamming the listener) cannot
grow memory unbounded. Callers should treat the queue as the single
source of truth for "what to show next" so that rapid-fire notifications
do not interrupt the in-flight animation.
"""
from __future__ import annotations

from collections import deque
from typing import Optional


class NotificationQueue:
    """Bounded FIFO queue for notification display text.

    Args:
        max_size: Maximum number of items to retain. When ``len()`` would
            exceed this value after an ``enqueue``, the oldest item is
            dropped. Defaults to 20.
    """

    DEFAULT_MAX_SIZE = 20

    def __init__(self, max_size: int = DEFAULT_MAX_SIZE) -> None:
        if max_size < 1:
            raise ValueError(f"max_size must be >= 1, got {max_size}")
        self._max_size = int(max_size)
        self._items: deque[str] = deque()

    @property
    def max_size(self) -> int:
        return self._max_size

    def enqueue(self, text: str) -> Optional[str]:
        """Append *text* to the tail of the queue.

        Returns the text that was dropped from the head to make room, or
        ``None`` if the queue was not full. Callers can use the return
        value to surface a "N messages dropped" hint to the user.
        """
        dropped: Optional[str] = None
        if len(self._items) >= self._max_size:
            dropped = self._items.popleft()
        self._items.append(text)
        return dropped

    def dequeue(self) -> Optional[str]:
        """Remove and return the head item, or ``None`` if empty."""
        if not self._items:
            return None
        return self._items.popleft()

    def peek(self) -> Optional[str]:
        """Return the head item without removing it, or ``None`` if empty."""
        if not self._items:
            return None
        return self._items[0]

    def clear(self) -> None:
        """Remove all items from the queue."""
        self._items.clear()

    def is_empty(self) -> bool:
        return len(self._items) == 0

    def __len__(self) -> int:
        return len(self._items)

    def __bool__(self) -> bool:
        return bool(self._items)