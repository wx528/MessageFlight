"""Tests for the bounded FIFO NotificationQueue."""
import pytest

from message_flight.notification_queue import NotificationQueue


def test_new_queue_is_empty():
    q = NotificationQueue()
    assert q.is_empty()
    assert len(q) == 0
    assert bool(q) is False


def test_enqueue_and_dequeue_fifo():
    q = NotificationQueue()
    q.enqueue("a")
    q.enqueue("b")
    q.enqueue("c")
    assert len(q) == 3
    assert q.dequeue() == "a"
    assert q.dequeue() == "b"
    assert q.dequeue() == "c"
    assert q.dequeue() is None
    assert q.is_empty()


def test_peek_does_not_remove():
    q = NotificationQueue()
    q.enqueue("hello")
    assert q.peek() == "hello"
    assert q.peek() == "hello"
    assert len(q) == 1


def test_dequeue_empty_returns_none():
    q = NotificationQueue()
    assert q.dequeue() is None
    assert q.peek() is None


def test_max_size_drops_oldest_returns_dropped():
    q = NotificationQueue(max_size=3)
    assert q.enqueue("a") is None
    assert q.enqueue("b") is None
    assert q.enqueue("c") is None
    dropped = q.enqueue("d")
    assert dropped == "a"
    assert len(q) == 3
    assert q.dequeue() == "b"
    assert q.dequeue() == "c"
    assert q.dequeue() == "d"


def test_max_size_one_only_keeps_latest():
    q = NotificationQueue(max_size=1)
    assert q.enqueue("a") is None
    assert len(q) == 1
    assert q.enqueue("b") == "a"
    assert len(q) == 1
    assert q.dequeue() == "b"


def test_clear_empties_queue():
    q = NotificationQueue()
    q.enqueue("a")
    q.enqueue("b")
    q.clear()
    assert q.is_empty()
    assert q.dequeue() is None


def test_default_max_size_constant():
    assert NotificationQueue.DEFAULT_MAX_SIZE == 20


def test_invalid_max_size_raises():
    with pytest.raises(ValueError):
        NotificationQueue(max_size=0)
    with pytest.raises(ValueError):
        NotificationQueue(max_size=-1)


def test_bool_conversion():
    q = NotificationQueue()
    assert not q
    q.enqueue("x")
    assert q
    q.clear()
    assert not q