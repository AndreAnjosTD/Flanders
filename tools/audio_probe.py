#!/usr/bin/env python3
r"""Find the output device the captain can actually hear.

Plays a numbered line through each candidate speaker in turn:
    "One"   -> Jabra headset
    "Two"   -> Realtek laptop speakers
    "Three" -> DELL monitor over HDMI
    "Four"  -> Jabra headset (WASAPI)

Run:
    .\.venv\Scripts\python.exe tools\audio_probe.py            # generate + play
    .\.venv\Scripts\python.exe tools\audio_probe.py --cached   # reuse generated lines
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from flanders import flanders_audio, fish_audio_tts

CACHE = ROOT / "tests" / "voice"

TARGETS = [
    (14, "One", "Jabra headset (DirectSound)"),
    (8, "Two", "Realtek laptop speakers"),
    (16, "Three", "DELL monitor over HDMI"),
    (21, "Four", "Jabra headset (WASAPI)"),
]


def line_for(word: str, cached: bool) -> Path | None:
    path = CACHE / f"probe_{word.lower()}.wav"
    if path.exists() and (cached or path.stat().st_size > 2000):
        return path
    CACHE.mkdir(parents=True, exist_ok=True)
    print(f"  generating '{word}'...", flush=True)
    return fish_audio_tts.synthesize(word, out_path=path)


def main(argv: list[str]) -> int:
    cached = "--cached" in argv

    print("Preparing four spoken numbers...", flush=True)
    clips = []
    for index, word, label in TARGETS:
        path = line_for(word, cached)
        if path is None:
            print(f"  could not generate '{word}'; skipping {label}", flush=True)
            continue
        clips.append((index, label, path))

    if not clips:
        print("Nothing to play.", flush=True)
        return 1

    time.sleep(0.5)
    for index, label, path in clips:
        print(f"\n--- {path.stem} on device {index}: {label}", flush=True)
        try:
            flanders_audio.play(path, device=index)
        except Exception as exc:  # noqa: BLE001
            print(f"    failed: {exc}", flush=True)
        time.sleep(1.2)

    print("\nprobe finished - which number did you hear?", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
