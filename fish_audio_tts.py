#!/usr/bin/env python3
"""
Flanders voice via Fish Audio (Drama 3).

This is the "natural voice" engine for Flanders. It does not train anything:
Drama 3 clones a voice zero-shot from a stored voice model, so any string can be
spoken at runtime.

The voice model used by default is the Ned Flanders model on Fish Audio, which
the platform already serves with Drama 3:
    https://fish.audio/m/8ca8ea05a29548758a9085747db19879/

Requirements:
    A Fish Audio API key. Set FISH_API_KEY (or FISH_AUDIO_API_KEY), or put the
    key on its own line in fish_audio_key.txt next to this file.
    Create a key at https://fish.audio/app/api-keys/

Usage:
    py fish_audio_tts.py "Okily dokily, captain!"
    py fish_audio_tts.py --save out.wav "Praise the Lord!"
    py fish_audio_tts.py --voice <model-id> "Hi-diddly-ho, neighborino!"
    py fish_audio_tts.py --check

Programmatic use:
    from fish_audio_tts import speak, synthesize
    speak("Okily dokily!")            # writes a temp WAV and plays it
    path = synthesize("Praise ...")   # writes a WAV and returns its path

Design notes:
    - The request asks for WAV so Windows can play it with winsound and no extra
      dependency. MP3 is available with --format mp3.
    - On a missing key or a billing/auth error this reports the concrete problem
      and returns None instead of silently falling back.
    - play_with_fallback() is the one place that falls back to the existing
      pyttsx3 voice, so callers never have to guess which engine ran.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
KEY_FILE = HERE / "fish_audio_key.txt"
SETTINGS_FILE = HERE / "voice_settings.json"

API_URL = "https://api.fish.audio/v1/tts"
DEFAULT_VOICE_ID = "8ca8ea05a29548758a9085747db19879"
# s2.1-pro-free is the same model as S2.1-Pro at $0 under fair-use limits,
# so the hosted voice costs nothing. Ask for drama-3 only when you want it.
DEFAULT_MODEL = "s2.1-pro-free"


def _settings() -> dict:
    if not SETTINGS_FILE.exists():
        return {}
    try:
        return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _model() -> str:
    return (
        os.environ.get("FISH_AUDIO_MODEL", "").strip()
        or str(_settings().get("model") or "")
        or DEFAULT_MODEL
    )


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_text(name: str, default: str = "") -> str:
    return os.environ.get(name, "").strip() or default


def _tuned(name: str, env_name: str, default):
    """Explicit value, else environment, else voice_settings.json, else default."""
    raw = os.environ.get(env_name, "").strip()
    if raw:
        try:
            return float(raw)
        except ValueError:
            pass
    value = _settings().get(name)
    if value is not None:
        try:
            return float(value)
        except (TypeError, ValueError):
            pass
    return default


def _api_key() -> str | None:
    for name in ("FISH_API_KEY", "FISH_AUDIO_API_KEY"):
        key = os.environ.get(name, "").strip()
        if key:
            return key
    if KEY_FILE.exists():
        value = KEY_FILE.read_text(encoding="utf-8").strip()
        if value:
            return value
    return None


def _play(path: Path) -> None:
    """Play an audio file, blocking until it finishes."""
    from flanders_audio import play

    play(path)


def synthesize(
    text: str,
    voice_id: str = DEFAULT_VOICE_ID,
    model: str | None = None,
    audio_format: str = "wav",
    out_path: str | os.PathLike[str] | None = None,
    timeout: int = 120,
    speed: float | None = None,
    temperature: float | None = None,
    top_p: float | None = None,
    style: str | None = None,
    normalize_loudness: bool = True,
) -> Path | None:
    """Generate speech and save it. Returns the path, or None on failure."""
    text = (text or "").strip()
    if not text:
        print("Nothing to speak: the text is empty.")
        return None
    if model is None:
        model = _model()

    voice_id = (
        _env_text("FISH_AUDIO_VOICE_ID")
        or str(_settings().get("voice_id") or "")
        or voice_id
    )

    speed = speed if speed is not None else _tuned("speed", "FISH_AUDIO_SPEED", 1.0)
    temperature = (
        temperature
        if temperature is not None
        else _tuned("temperature", "FISH_AUDIO_TEMPERATURE", 0.75)
    )
    top_p = top_p if top_p is not None else _tuned("top_p", "FISH_AUDIO_TOP_P", 0.7)
    style = (
        style
        if style is not None
        else (_env_text("FISH_AUDIO_STYLE") or str(_settings().get("style") or ""))
    )
    if style:
        text = f"{style} {text}"

    key = _api_key()
    if not key:
        print(
            "No Fish Audio API key found. Set FISH_AUDIO_API_KEY or create "
            f"{KEY_FILE} with the key on its own line."
        )
        return None

    body = {
        "text": text,
        "reference_id": voice_id,
        "format": audio_format,
        "sample_rate": 44100,
        "normalize": True,
        "latency": "normal",
        "temperature": temperature,
        "top_p": top_p,
        "prosody": {
            "speed": speed,
            "volume": 0,
            "normalize_loudness": normalize_loudness,
        },
    }

    request = urllib.request.Request(
        API_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "model": model,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            audio = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:500]
        hints = {
            401: "the API key was rejected",
            402: "the account has no credit for this request",
            503: "Fish Audio is under high load; try again shortly",
        }
        print(f"Fish Audio error {exc.code}: {hints.get(exc.code, exc.reason)}")
        if detail:
            print(detail)
        return None
    except urllib.error.URLError as exc:
        print(f"Could not reach Fish Audio: {exc.reason}")
        return None

    if outf := out_path:
        path = Path(outf)
    else:
        suffix = f".{audio_format}"
        handle, name = tempfile.mkstemp(prefix="flanders_", suffix=suffix)
        os.close(handle)
        path = Path(name)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(audio)
    return path


def speak(
    text: str,
    voice_id: str = DEFAULT_VOICE_ID,
    model: str | None = None,
    audio_format: str = "wav",
    keep: bool = False,
    **options,
) -> bool:
    """Synthesize and play the text. True when audio was produced and played."""
    out_path = None
    if keep:
        safe = "".join(c if c.isalnum() else "_" for c in text[:40]).strip("_")
        out_path = HERE / f"flanders_{safe or 'line'}.wav"

    path = synthesize(
        text,
        voice_id=voice_id,
        model=model,
        audio_format=audio_format,
        out_path=out_path,
        **options,
    )
    if path is None:
        return False

    _play(path)
    if not keep:
        try:
            path.unlink()
        except OSError:
            pass
    return True


def play_with_fallback(text: str, **kwargs) -> str:
    """Speak with Fish Audio when possible, otherwise with the local pyttsx3 voice."""
    if _api_key():
        return "fish-audio" if speak(text, **kwargs) else "failed"

    try:
        import pyttsx3

        engine = pyttsx3.init()
        engine.setProperty("rate", 130)
        engine.setProperty("volume", 0.9)
        engine.say(text)
        engine.runAndWait()
        return "pyttsx3"
    except Exception as exc:  # noqa: BLE001 - report the concrete reason
        print(f"Local speech fallback failed: {exc}")
        return "failed"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Flanders voice through Fish Audio Drama 3.")
    parser.add_argument("text", nargs="*", help="Text to speak.")
    parser.add_argument("--voice", default=DEFAULT_VOICE_ID, help="Fish Audio voice model id.")
    parser.add_argument(
        "--model",
        default=None,
        help=f"TTS model header (default {DEFAULT_MODEL}, or FISH_AUDIO_MODEL).",
    )
    parser.add_argument("--format", default="wav", choices=["wav", "mp3", "pcm", "opus"])
    parser.add_argument("--speed", type=float, default=None, help="0.5 to 2.0, default 1.0.")
    parser.add_argument("--temperature", type=float, default=None, help="Expressiveness, 0.1 to 1.0.")
    parser.add_argument("--top-p", dest="top_p", type=float, default=None, help="Diversity, 0.1 to 1.0.")
    parser.add_argument("--style", default=None, help="Bracket style tag, e.g. \"[cheerful]\".")
    parser.add_argument("--save", metavar="PATH", help="Save to this path instead of a temp file.")
    parser.add_argument("--check", action="store_true", help="Report key and voice configuration.")
    args = parser.parse_args(argv)

    if args.check:
        key = _api_key()
        print(f"API key: {'present' if key else 'missing'}")
        print(f"Voice id: {args.voice}")
        print(f"Model: {args.model or _model()}")
        print(f"Key file: {KEY_FILE} ({'exists' if KEY_FILE.exists() else 'absent'})")
        return 0 if key else 1

    text = " ".join(args.text).strip()
    if not text:
        parser.error("give some text to speak")

    options = dict(
        speed=args.speed,
        temperature=args.temperature,
        top_p=args.top_p,
        style=args.style,
    )

    if args.save:
        path = synthesize(
            text,
            voice_id=args.voice,
            model=args.model,
            audio_format=args.format,
            out_path=args.save,
            **options,
        )
        if path is None:
            return 1
        print(f"Saved {path}")
        return 0

    return 0 if speak(text, voice_id=args.voice, model=args.model, **options) else 1


if __name__ == "__main__":
    raise SystemExit(main())
