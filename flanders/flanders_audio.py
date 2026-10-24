#!/usr/bin/env python3
r"""Audio playback with an explicit device choice.

Windows sometimes routes the default output to a device nobody is listening to
(a monitor over HDMI, or a virtual device such as NVIDIA Broadcast). This module
lets Flanders speak to a chosen device.

Choose a device with:
    set FLANDERS_AUDIO_DEVICE=Headset           (matches by name)
    set FLANDERS_AUDIO_DEVICE=14                (index from tools/audio_devices.py)

When it is unset, the Windows default output is used.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
if __package__ in (None, ""):
    sys.path.insert(0, str(ROOT))

from flanders import settings  # noqa: E402


def list_devices() -> list[tuple[int, str, int]]:
    """Return (index, name, output_channels) for every device with outputs."""
    try:
        import sounddevice as sd
    except ImportError:
        return []
    rows = []
    for index, device in enumerate(sd.query_devices()):
        channels = int(device.get("max_output_channels", 0))
        if channels > 0:
            rows.append((index, device.get("name", ""), channels))
    return rows


def _configured_device() -> str:
    """Env var first, then voice_settings.json.

    The speaker runs inside the captain's session but is launched by the
    service, so it does not inherit a shell environment. The settings file is
    what survives that hand-off.
    """
    return os.environ.get("FLANDERS_AUDIO_DEVICE", "").strip() or settings.text("audio_device")


def resolve_device(device: str | int | None) -> int | None:
    """Turn a name or index into a sounddevice index, or None for the default."""
    if device is None or device == "":
        device = _configured_device()
    if device is None or device == "":
        return None

    raw = str(device).strip()
    if raw.isdigit():
        return int(raw)

    lowered = raw.lower()
    matches = [row for row in list_devices() if lowered in row[1].lower()]
    if not matches:
        print(f"No audio device matches '{raw}'; using the default.", file=sys.stderr)
        return None
    # Prefer the Windows default host (MME) when several devices match.
    return matches[0][0]


def _resample(audio: np.ndarray, src_rate: int, dst_rate: int) -> np.ndarray:
    """Linear resampling, adequate for speech playback fallback."""
    if src_rate == dst_rate or audio.size == 0:
        return audio
    frames = audio.shape[0]
    target_frames = max(1, round(frames * dst_rate / src_rate))
    src_positions = np.arange(frames, dtype=np.float64)
    dst_positions = np.linspace(0, frames - 1, target_frames)
    if audio.ndim == 1:
        return np.interp(dst_positions, src_positions, audio).astype(np.float32)
    channels = [
        np.interp(dst_positions, src_positions, audio[:, ch]) for ch in range(audio.shape[1])
    ]
    return np.stack(channels, axis=1).astype(np.float32)


def _device_rate(device: int | None) -> int | None:
    try:
        import sounddevice as sd

        info = sd.query_devices(device, kind="output")
        rate = int(info.get("default_samplerate") or 0)
        return rate or None
    except Exception:
        return None


def play(path: str | os.PathLike[str], device: str | int | None = None) -> None:
    """Play a WAV file, blocking until it finishes."""
    path = Path(path)
    target = resolve_device(device)

    try:
        import sounddevice as sd
        import soundfile as sf

        audio, rate = sf.read(str(path), dtype="float32", always_2d=True)
        try:
            sd.play(audio, samplerate=rate, device=target)
            sd.wait()
            return
        except Exception:
            native = _device_rate(target)
            if not native or native == rate:
                raise
            adjusted = _resample(audio, rate, native)
            sd.play(adjusted, samplerate=native, device=target)
            sd.wait()
            return
    except Exception as exc:
        print(f"sounddevice playback failed ({exc}); falling back to winsound", file=sys.stderr)

    if sys.platform == "win32":
        import winsound

        winsound.PlaySound(str(path), winsound.SND_FILENAME)
    else:
        print(f"Audio saved to {path}")
