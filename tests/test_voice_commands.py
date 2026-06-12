"""Tests for voice command parsing."""
import pytest

from message_flight.voice_commands import (
    COMMAND_PATTERNS,
    VoiceCommand,
    parse_command,
)


@pytest.mark.parametrize(
    "text,expected",
    [
        ("暂停", VoiceCommand.PAUSE),
        ("停止", VoiceCommand.PAUSE),
        ("请暂停飞行", VoiceCommand.PAUSE),
        ("pause", VoiceCommand.PAUSE),
        ("stop the plane", VoiceCommand.PAUSE),
        ("恢复", VoiceCommand.RESUME),
        ("继续", VoiceCommand.RESUME),
        ("resume", VoiceCommand.RESUME),
        ("start", VoiceCommand.RESUME),
        ("下一个", VoiceCommand.NEXT_PRESET),
        ("换飞机", VoiceCommand.NEXT_PRESET),
        ("next", VoiceCommand.NEXT_PRESET),
        ("switch", VoiceCommand.NEXT_PRESET),
        ("免打扰", VoiceCommand.TOGGLE_DND),
        ("勿扰", VoiceCommand.TOGGLE_DND),
        ("dnd", VoiceCommand.TOGGLE_DND),
        ("do not disturb", VoiceCommand.TOGGLE_DND),
        ("演示", VoiceCommand.SEND_DEMO),
        ("测试", VoiceCommand.SEND_DEMO),
        ("demo", VoiceCommand.SEND_DEMO),
        ("test", VoiceCommand.SEND_DEMO),
        ("PAUSE", VoiceCommand.PAUSE),
        ("Pause", VoiceCommand.PAUSE),
        ("STOP please", VoiceCommand.PAUSE),
    ],
)
def test_parse_command_matches(text: str, expected: VoiceCommand) -> None:
    assert parse_command(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "",
        "天气怎么样",
        "今天吃什么",
        "hello world",
        "abcdef",
    ],
)
def test_parse_command_returns_none_for_nonsense(text: str) -> None:
    assert parse_command(text) is None


def test_parse_command_prefers_first_matching() -> None:
    """PAUSE comes before RESUME in COMMAND_PATTERNS; ambiguous input hits PAUSE first."""
    assert parse_command("pause and resume") == VoiceCommand.PAUSE


@pytest.mark.parametrize(
    "text,expected",
    [
        ("stop and switch", VoiceCommand.PAUSE),  # PAUSE before NEXT_PRESET
        ("start demo", VoiceCommand.RESUME),       # RESUME before SEND_DEMO
        ("暂停 下一个", VoiceCommand.PAUSE),        # zh: PAUSE before NEXT_PRESET
        ("next demo", VoiceCommand.NEXT_PRESET),   # NEXT_PRESET before SEND_DEMO
    ],
)
def test_parse_command_prefers_first_matching_extended(text: str, expected: VoiceCommand) -> None:
    """Each pairing: the first command in COMMAND_PATTERNS wins on ambiguous input."""
    assert parse_command(text) == expected


def test_command_patterns_has_all_voice_commands() -> None:
    assert set(COMMAND_PATTERNS.keys()) == set(VoiceCommand)
