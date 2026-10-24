#!/usr/bin/env python3
r"""Checks for the speakable-text pipeline.

Run:
    .\.venv\Scripts\python.exe tests\test_speech.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flanders import flanders_speech as speech

CASES: list[tuple[str, str]] = [
    # Decorations disappear.
    (":wave: hello there", "hello there"),
    (":tada: :sparkles: shipped", "shipped"),
    ("*bold* and _italic_ and ~gone~", "bold and italic and gone"),
    ("`main` branch", "main branch"),
    ("a  b   c", "a b c"),
    # Meaningful icons become words.
    (":white_check_mark: Deploy finished", "Done. Deploy finished"),
    (":warning: disk almost full", "Warning. disk almost full"),
    (":red_circle: build failed", "Blocked. build failed"),
    # Entities and Slack syntax.
    ("asked you &gt; go ahead?", "asked you: go ahead?"),
    ("see <https://example.com|the report>", "see the report"),
    ("see <https://example.com>", "see a link"),
    ("thanks <@U123|Andre>", "thanks Andre"),
    ("ping <#C1|general>", "ping general channel"),
    # Units read naturally.
    ("quiet for 1m", "quiet for 1 minute"),
    ("waiting 5m", "waiting 5 minutes"),
    ("took 3h", "took 3 hours"),
    # Lists lose their bullets.
    ("1. first thing", "first thing"),
    ("- a bullet", "a bullet"),
]

SKIP_CASES = [
    "great!",
    "ok",
    "Thanks captain!",
    "yes",
    "sounds good",
    "kk",
    "Amazing flanders!",
    "",
    "   ",
]

KEEP_CASES = [
    "The build broke on the settings page.",
    "Shall I dispatch the publish?",
    "Deploy finished to main.",
    "Review phase is waiting on you",
    # A lone tick still means something, so it is worth one word.
    ":white_check_mark:",
]


def check(condition: bool, label: str) -> bool:
    if condition:
        print(f"  ok   {label}")
        return True
    print(f"  FAIL {label}")
    return False


def main() -> int:
    passed = True

    print("cleaning:")
    for raw, expected in CASES:
        actual = speech.to_speech(raw, limit=None)
        passed &= check(actual == expected, f"{raw!r} -> {actual!r}")

    print("\nnoise filter (should be silent):")
    for raw in SKIP_CASES:
        actual = speech.speakable(raw)
        passed &= check(actual == "", f"{raw!r} -> {actual!r}")

    print("\nnoise filter (should be spoken):")
    for raw in KEEP_CASES:
        actual = speech.speakable(raw)
        passed &= check(bool(actual), f"{raw!r} -> {actual!r}")

    print("\ncommand help is dropped, the question survives:")
    raw = (
        'Captain, Review phase is waiting on you: "Shall I dispatch the publish?" '
        "(:stopwatch: 1m) Reply with `/flanders answer <number> <your answer>`. "
        "This home has no ledger yet."
    )
    actual = speech.speakable(raw)
    passed &= check("/flanders" not in actual, f"no command syntax in {actual!r}")
    passed &= check("Shall I dispatch the publish?" in actual, "question is kept")
    passed &= check("ledger" in actual, "the ordinary sentence is kept")

    print("\nlong messages are capped:")
    long_text = " ".join(["word"] * 400)
    capped = speech.speakable(long_text, limit=200)
    passed &= check(capped.endswith("And more."), "ends with And more.")
    passed &= check(len(capped) <= 220, f"length {len(capped)}")

    print("\nALL PASS" if passed else "\nFAILURES")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
