#!/usr/bin/env python3
r"""List output devices, or play a counting test so the captain can identify one.

Usage:
    .\.venv\Scripts\python.exe tools\audio_devices.py --list
    .\.venv\Scripts\python.exe tools\audio_devices.py --test Radio
    .\.venv\Scripts\python.exe tools\audio_devices.py --test 4
    .\.venv\Scripts\python.exe tools\audio_devices.py --sweep
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import sounddevice as sd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from flanders import flanders_audio

RATE = 44100

CANDIDATES = [
    (4, "Speakers (Realtek(R) Audio)"),
    (5, "Speakers (NVIDIA Broadcast)"),
    (6, "DELL P2715Q (NVIDIA HDMI)"),
    (22, "Headphones (Realtek 2nd output)"),
]


def tone(seconds: float = 0.35, frequency: float = 660.0, device: int | None = None) -> None:
    t = np.linspace(0, seconds, int(RATE * seconds), endpoint=False)
    audio = (0.30 * np.sin(2 * np.pi * frequency * t)).astype(np.float32)
    sd.play(audio, samplerate=RATE, device=device)
    sd.wait()


def list_devices() -> None:
    for index, name, channels in flanders_audio.list_devices():
        print(f"{index:3d}  {channels} ch  {name}")


def test(device: str) -> None:
    print(f"playing three beeps on {device}")
    target = flanders_audio.resolve_device(device)
    for _ in range(3):
        tone(device=target)
        time.sleep(0.15)


def sweep() -> None:
    for count, (index, name) in enumerate(CANDIDATES, start=1):
        print(f"\n{count} beep(s) -> device {index}: {name}", flush=True)
        for _ in range(count):
            try:
                tone(device=index)
            except Exception as exc:
                print(f"  failed: {exc}")
                break
            time.sleep(0.18)
        time.sleep(0.5)
    print("\nsweep finished")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audio device helper.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list", action="store_true")
    group.add_argument("--test", metavar="DEVICE")
    group.add_argument("--sweep", action="store_true")
    args = parser.parse_args()

    if args.list:
        list_devices()
    elif args.test:
        test(args.test)
    else:
        sweep()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
