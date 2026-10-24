"""The single reader for ``voice_settings.json``.

Voice tuning used to be re-parsed in three modules (engine choice, hosted voice,
playback device), which meant three copies of the same fallback rules. Every
module now goes through here, so the file's shape is described once.

A missing, unreadable, or malformed file is never fatal: the defaults below are
the shipped values, so a bad edit can degrade the voice but never silence it.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SETTINGS_FILE = ROOT / "voice_settings.json"

DEFAULT_VOICE_ID = "8ca8ea05a29548758a9085747db19879"
DEFAULT_MODEL = "s2.1-pro-free"

DEFAULTS: dict[str, object] = {
    "engine": "hosted",
    "model": DEFAULT_MODEL,
    "voice_id": DEFAULT_VOICE_ID,
    "speed": 1.0,
    "temperature": 0.75,
    "top_p": 0.7,
    "style": "[warmly]",
    "audio_device": "",
}


def load(path: Path | None = None) -> dict:
    """Return the settings, with the shipped defaults filled in."""
    merged = dict(DEFAULTS)
    target = path if path is not None else SETTINGS_FILE
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return merged
    if isinstance(data, dict):
        merged.update({key: value for key, value in data.items() if value is not None})
    return merged


def text(name: str, default: str = "") -> str:
    """A settings value as a stripped string, or `default`."""
    return str(load().get(name) or default).strip()


def number(name: str, default: float) -> float:
    """A settings value as a float, or `default` when it is unusable."""
    try:
        return float(load().get(name))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
