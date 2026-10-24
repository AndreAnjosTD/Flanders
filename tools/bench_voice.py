#!/usr/bin/env python3
"""Compare bf16 and fp16 generation speed for the local voice."""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import soundfile as sf

from flanders.flanders_local_tts import LocalFishVoice

TEXT = "Okily dokily, captain! Flanders is here and in fine voice today."
OUT = ROOT / "tests" / "voice"


def run(half: bool) -> None:
    label = "fp16" if half else "bf16"
    voice = LocalFishVoice(half=half)
    for index in range(2):
        started = time.perf_counter()
        path = voice.synthesize(TEXT, out_path=OUT / f"bench_{label}_{index}.wav")
        elapsed = time.perf_counter() - started
        info = sf.info(str(path))
        audio = info.frames / info.samplerate
        print(f"{label} run {index + 1}: {elapsed:5.2f}s for {audio:4.2f}s audio, RTF {elapsed / audio:4.2f}")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    run("--half" in sys.argv)
