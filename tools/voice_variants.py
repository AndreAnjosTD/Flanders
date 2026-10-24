#!/usr/bin/env python3
r"""Generate the same line in a few voice settings so the captain can pick one.

Run:
    .\.venv\Scripts\python.exe voice_variants.py
"""

from __future__ import annotations

from pathlib import Path

import fish_audio_tts

OUT = Path(__file__).resolve().parent / "tests" / "voice"

LINE = (
    "Hi-diddly-ho, captain! Flanders is all tuned up and ready to lend a hand "
    "with your tasks today."
)

VARIANTS = [
    (
        "neutral",
        "steady pace, even warmth",
        dict(speed=1.0, temperature=0.7, top_p=0.7),
    ),
    (
        "brighter",
        "a touch quicker and more cheerful",
        dict(speed=1.05, temperature=0.8, top_p=0.75, style="[cheerful]"),
    ),
    (
        "measured",
        "slower and gentler, sermon-like",
        dict(speed=0.95, temperature=0.6, top_p=0.65),
    ),
    (
        "neighbourly",
        "warm and conversational",
        dict(speed=1.0, temperature=0.75, top_p=0.7, style="[warmly]"),
    ),
]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    results = []

    for slug, description, options in VARIANTS:
        print(f"\n=== {slug}: {description}")
        path = fish_audio_tts.synthesize(
            LINE, out_path=OUT / f"variant_{slug}.wav", **options
        )
        if path is None:
            print(f"{slug} failed")
            continue
        results.append((slug, path))
        fish_audio_tts._play(path)

    print("\nSaved:")
    for slug, path in results:
        print(f"  {slug:12s} {path}")
    return 0 if results else 1


if __name__ == "__main__":
    raise SystemExit(main())
