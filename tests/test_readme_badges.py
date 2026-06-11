"""README badge coverage tests."""
from pathlib import Path

README_FILES = (
    "README.md",
    "README.zh.md",
    "README.ja.md",
    "README.ko.md",
    "README.id.md",
    "README.th.md",
    "README.vi.md",
    "README.ms.md",
)

BADGE_MARKERS = (
    "img.shields.io/badge/Python-3.8%2B",
    "img.shields.io/badge/GUI-PyQt6",
    "img.shields.io/badge/Platform-Windows%2010%2F11",
    "img.shields.io/pypi/v/messageflight",
    "img.shields.io/badge/License-MIT",
    "actions/workflows/ci.yml/badge.svg",
    "img.shields.io/badge/Languages-zh%20%7C%20en%20%7C%20ja%20%7C%20ko%20%7C%20id%20%7C%20th%20%7C%20vi%20%7C%20ms",
)


def test_all_readmes_include_project_badges():
    root = Path(__file__).resolve().parents[1]
    for readme in README_FILES:
        text = (root / readme).read_text(encoding="utf-8")
        for marker in BADGE_MARKERS:
            assert marker in text, f"{readme} missing badge marker {marker}"
