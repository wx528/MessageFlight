"""Bilingual voice command enum + keyword parser.

Maps free-form speech (Chinese or English) to one of five control
actions. Matching is case-insensitive substring: the first keyword
that appears in the input wins.
"""
from __future__ import annotations

from enum import Enum


class VoiceCommand(Enum):
    """The set of voice commands the app understands."""

    PAUSE = "pause"
    RESUME = "resume"
    NEXT_PRESET = "next_preset"
    TOGGLE_DND = "toggle_dnd"
    SEND_DEMO = "send_demo"


COMMAND_PATTERNS: dict[VoiceCommand, list[str]] = {
    VoiceCommand.PAUSE:       ["暂停", "停止", "pause", "stop"],
    VoiceCommand.RESUME:      ["恢复", "继续", "resume", "continue", "start"],
    VoiceCommand.NEXT_PRESET: ["下一个", "换飞机", "next", "switch"],
    VoiceCommand.TOGGLE_DND:  ["免打扰", "勿扰", "dnd", "do not disturb"],
    VoiceCommand.SEND_DEMO:   ["演示", "测试", "demo", "test"],
}


def parse_command(text: str) -> VoiceCommand | None:
    """Return the first matching :class:`VoiceCommand`, or ``None``.

    Matching is case-insensitive substring: ``text.lower()`` is scanned
    for any keyword in :data:`COMMAND_PATTERNS` (in declared order).
    """
    lowered = text.lower()
    for cmd, keywords in COMMAND_PATTERNS.items():
        for kw in keywords:
            if kw.lower() in lowered:
                return cmd
    return None
