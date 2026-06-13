"""Bilingual voice command enum + keyword parser.

Maps free-form speech (Chinese or English) to one of five control
actions. Matching is case-insensitive with word boundaries: the first
keyword that appears as a standalone word in the input wins.
"""
from __future__ import annotations

import re
from enum import Enum


class VoiceCommand(Enum):
    """The set of voice commands the app understands."""

    PAUSE = "pause"
    RESUME = "resume"
    NEXT_PRESET = "next_preset"
    TOGGLE_DND = "toggle_dnd"
    SEND_DEMO = "send_demo"
    OPEN_SETTINGS = "open_settings"
    QUIT_APP = "quit_app"


COMMAND_PATTERNS: dict[VoiceCommand, list[str]] = {
    VoiceCommand.PAUSE:          ["暂停", "停止", "pause", "stop"],
    VoiceCommand.RESUME:         ["恢复", "继续", "resume", "continue", "start"],
    VoiceCommand.NEXT_PRESET:    ["下一个", "换飞机", "next", "switch"],
    VoiceCommand.TOGGLE_DND:     ["免打扰", "勿扰", "dnd", "do not disturb"],
    VoiceCommand.SEND_DEMO:      ["演示", "测试", "demo", "test"],
    VoiceCommand.OPEN_SETTINGS:  ["设置", "打开设置", "settings", "open settings"],
    VoiceCommand.QUIT_APP:       ["退出", "关闭应用", "关闭程序", "quit", "exit", "close"],
}


def parse_command(text: str) -> VoiceCommand | None:
    """Return the first matching :class:`VoiceCommand`, or ``None``.

    Matching is case-insensitive with word boundaries. Chinese keywords
    use a simple ``in`` substring check (no word boundaries in Chinese).
    English keywords require a word boundary (``\\b``) so that e.g.
    ``"restart"`` does not match ``"start"``.
    """
    lowered = text.lower()
    for cmd, keywords in COMMAND_PATTERNS.items():
        for kw in keywords:
            kw_lower = kw.lower()
            # Chinese keywords: simple substring match (no word boundaries)
            if any("\u4e00" <= c <= "\u9fff" for c in kw):
                if kw_lower in lowered:
                    return cmd
            # English keywords: word boundary match
            elif re.search(rf"\b{re.escape(kw_lower)}\b", lowered):
                return cmd
    return None
