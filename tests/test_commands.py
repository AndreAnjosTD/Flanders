#!/usr/bin/env python3
r"""Checks that only a real /flanders command produces a reply.

Run:
    .\.venv\Scripts\python.exe tests\test_commands.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flanders import voice_integration as voice


class FakeVoice:
    """Records what the dispatcher asked for, without speaking."""

    def __init__(self) -> None:
        self.calls = []

    def process_command(self, args: list[str]) -> str:
        self.calls.append(list(args))
        return "REPLY"


# Ordinary words: spoken aloud, but never answered or sent anywhere.
SPOKEN = [
    "hello there",
    "just some ordinary text",
    "please take a look at the login bug",
]

# Input that must do nothing at all.
SILENT = [
    "/bot do something",
    "/flandersx nope",
    "/unknown command",
    "   ",
    "",
]

# A real command, with or without a valid flag, must reach the handler.
DISPATCHED = [
    ("/flanders bogus", ["bogus"]),
    ("/flanders help", ["help"]),
    ("/flanders status", ["status"]),
    ("/flander modes", ["modes"]),
    ("/flanders", []),
    ("/FLANDERS status", ["status"]),
    ("  /flanders delegate ship it  ", ["delegate", "ship", "it"]),
]

QUIT_LINES = ["/quit", "exit", "q", "QUIT"]


def check(condition: bool, label: str) -> bool:
    print(f"  {'ok  ' if condition else 'FAIL'} {label}")
    return condition


def main() -> int:
    passed = True

    print("ordinary words are spoken, never answered:")
    for line in SPOKEN:
        fake = FakeVoice()
        result = voice.handle_line(fake, line)
        ok = isinstance(result, voice.ReadAloud) and result.text == line and not fake.calls
        passed &= check(ok, f"{line!r} -> {result!r}")

    print("\nunrelated slash commands stay completely inert:")
    for line in SILENT:
        fake = FakeVoice()
        result = voice.handle_line(fake, line)
        passed &= check(
            result is None and not fake.calls,
            f"{line!r} -> result={result!r} calls={fake.calls}",
        )

    print("\nreal commands reach the handler:")
    for line, expected_args in DISPATCHED:
        fake = FakeVoice()
        result = voice.handle_line(fake, line)
        ok = result == "REPLY" and fake.calls == [expected_args]
        passed &= check(ok, f"{line!r} -> {fake.calls}")

    print("\nquit is recognised:")
    for line in QUIT_LINES:
        fake = FakeVoice()
        result = voice.handle_line(fake, line)
        passed &= check(result is voice.QUIT, f"{line!r} -> quit")

    print("\nALL PASS" if passed else "\nFAILURES")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
