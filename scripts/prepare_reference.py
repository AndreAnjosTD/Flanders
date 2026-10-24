#!/usr/bin/env python3
"""Prepare the Flanders reference clip as 44.1 kHz mono WAV.

Fish Speech compares the reference clip against audio decoded at 44.1 kHz, so a
single mono WAV avoids a resampling surprise at load time.

Tries soundfile/libsndfile first, then falls back to a bundled ffmpeg binary
(imageio-ffmpeg) for formats libsndfile cannot read.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
REF_DIR = HERE / "references"
SRC = REF_DIR / "flanders_sample.mp3"
DST = REF_DIR / "flanders_sample.wav"
SR = 44100


def with_soundfile() -> bool:
    try:
        import numpy as np
        import soundfile as sf
    except ImportError:
        return False

    try:
        audio, sample_rate = sf.read(str(SRC), dtype="float32", always_2d=True)
    except Exception as exc:  # noqa: BLE001
        print(f"soundfile could not read the sample: {exc}")
        return False

    audio = audio.mean(axis=1)
    if sample_rate != SR:
        try:
            import librosa

            audio = librosa.resample(audio, orig_sr=sample_rate, target_sr=SR)
        except ImportError:
            print("librosa missing; cannot resample.")
            return False

    sf.write(str(DST), np.clip(audio, -1.0, 1.0), SR)
    return True


def with_ffmpeg() -> bool:
    try:
        import imageio_ffmpeg
    except ImportError:
        return False

    exe = imageio_ffmpeg.get_ffmpeg_exe()
    command = [
        exe,
        "-y",
        "-i",
        str(SRC),
        "-ac",
        "1",
        "-ar",
        str(SR),
        "-c:a",
        "pcm_s16le",
        str(DST),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stderr[-800:])
        return False
    return True


def duration_seconds() -> float | None:
    try:
        import soundfile as sf

        info = sf.info(str(DST))
        return info.frames / info.samplerate
    except Exception:  # noqa: BLE001
        return None


def main() -> int:
    REF_DIR.mkdir(parents=True, exist_ok=True)
    if not SRC.exists():
        print(f"Missing source sample: {SRC}")
        return 1

    if DST.exists():
        seconds = duration_seconds()
        print(f"Already prepared: {DST} ({seconds:.1f}s)" if seconds else f"Already prepared: {DST}")
        return 0

    ok = with_soundfile() or with_ffmpeg()
    if not ok:
        print("Could not convert the sample. Install imageio-ffmpeg and try again.")
        return 1

    seconds = duration_seconds()
    print(f"Wrote {DST}" + (f" ({seconds:.1f}s)" if seconds else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
