#!/usr/bin/env python3
r"""Audible smoke test for the local Flanders voice.

Generates a few short lines, reports how long each took, and plays them.
Run from the project root with the venv interpreter:

    .\.venv\Scripts\python.exe tools\test_local_voice.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from flanders_local_tts import LocalFishVoice, _play

PHRASES = [
    "Okily dokily, captain! Flanders is here and in fine voice today.",
    "Hi-diddly-ho, neighborino! Shall we get these tasks delegated?",
    "Praise the Lord! The local voice is working just the way it ought to.",
]

OUT = ROOT / "tests" / "voice"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    voice = LocalFishVoice()

    for index, phrase in enumerate(PHRASES, start=1):
        started = time.perf_counter()
        path = voice.synthesize(phrase, out_path=OUT / f"line{index}.wav")
        generate_seconds = time.perf_counter() - started

        import soundfile as sf

        info = sf.info(str(path))
        audio_seconds = info.frames / info.samplerate
        ratio = generate_seconds / audio_seconds if audio_seconds else 0.0

        print(
            f"[{index}/{len(PHRASES)}] {audio_seconds:5.1f}s audio in "
            f"{generate_seconds:5.1f}s  (RTF {ratio:.2f})  -> {path.name}"
        )
        _play(path)

    print(f"\nFiles kept in {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
