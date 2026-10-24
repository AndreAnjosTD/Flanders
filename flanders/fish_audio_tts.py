#!/usr/bin/env python3
"""Flanders' hosted voice: Fish Audio with the public Ned Flanders model.

This engine clones the voice zero-shot from a stored model, so an arbitrary
string can be spoken at runtime. Nothing is trained here and no audio is kept
after playback unless you ask for it.

Voice model:
    https://fish.audio/m/8ca8ea05a29548758a9085747db19879/

The API key comes from the environment for one session (``FISH_API_KEY`` /
``FISH_AUDIO_API_KEY``) or from the Windows Credential Manager. It is never read
from a file, and this module never touches the Proton Pass vault: that is only
read by a deliberate, consented run of ``scripts/import_key.py``.

Usage:
    .\\.venv\\Scripts\\python.exe flanders\\fish_audio_tts.py "Okily dokily!"
    .\\.venv\\Scripts\\python.exe flanders\\fish_audio_tts.py --save out.wav "Hi!"
    .\\.venv\\Scripts\\python.exe flanders\\fish_audio_tts.py --check

Programmatic use:
    from flanders import fish_audio_tts
    fish_audio_tts.speak("Okily dokily!")
    path = fish_audio_tts.synthesize("Praise the Lord!")
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from contextlib import suppress
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if __package__ in (None, ""):
    sys.path.insert(0, str(ROOT))

from flanders import settings  # noqa: E402

API_URL = "https://api.fish.audio/v1/tts"
DEFAULT_VOICE_ID = settings.DEFAULT_VOICE_ID
DEFAULT_MODEL = settings.DEFAULT_MODEL

# s2.1-pro-free is the same model as S2.1-Pro at no charge under fair use, so
# the hosted voice costs nothing. Ask for drama-3 only when you want it.
MAX_TEXT_CHARS = 2000
MAX_AUDIO_BYTES = 32 * 1024 * 1024
DEFAULT_TIMEOUT = 120


def _model() -> str:
    return os.environ.get("FISH_AUDIO_MODEL", "").strip() or settings.text("model", DEFAULT_MODEL)


def _tuned(name: str, env_name: str, default: float) -> float:
    """Environment value first, then voice_settings.json, then the default."""
    raw = os.environ.get(env_name, "").strip()
    if raw:
        with suppress(ValueError):
            return float(raw)
    return settings.number(name, default)


def _api_key() -> str | None:
    """This session's key, else the OS credential store. Never a file."""
    from flanders import secret_store

    return secret_store.get_secret("fish_audio")


def has_api_key() -> bool:
    """True when a hosted key is available, without exposing it."""
    return bool(_api_key())


def _open(request: urllib.request.Request, timeout: int):
    """Open an HTTPS request, refusing any other scheme.

    The URL is a module constant, so this is a defence-in-depth check rather
    than a real branch: it keeps a future refactor from ever passing a
    ``file://`` or custom-scheme URL to urlopen.
    """
    scheme = urllib.parse.urlsplit(request.full_url).scheme
    if scheme != "https":
        raise ValueError(f"refusing a non-HTTPS request: {scheme or 'no scheme'}")
    return urllib.request.urlopen(request, timeout=timeout)  # noqa: S310 - scheme checked


def synthesize(
    text: str,
    voice_id: str = DEFAULT_VOICE_ID,
    model: str | None = None,
    audio_format: str = "wav",
    out_path: str | os.PathLike[str] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
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
    if len(text) > MAX_TEXT_CHARS:
        print(f"Text trimmed to the first {MAX_TEXT_CHARS} characters.")
        text = text[:MAX_TEXT_CHARS]

    if model is None:
        model = _model()

    voice_id = (
        os.environ.get("FISH_AUDIO_VOICE_ID", "").strip()
        or settings.text("voice_id", voice_id)
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
        else (os.environ.get("FISH_AUDIO_STYLE", "").strip() or settings.text("style"))
    )
    if style:
        text = f"{style} {text}"

    key = _api_key()
    if not key:
        print(
            "No Fish Audio API key found. Set FISH_API_KEY for this session, or "
            "import one into the credential store with scripts/import_key.py."
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
        with _open(request, timeout) as response:
            audio = response.read(MAX_AUDIO_BYTES + 1)
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
    except ValueError as exc:
        print(f"Fish Audio request refused: {exc}")
        return None

    if len(audio) > MAX_AUDIO_BYTES:
        print(f"Fish Audio returned more than {MAX_AUDIO_BYTES // 1048576} MB; discarded.")
        return None

    if out_path is not None:
        path = Path(out_path)
    else:
        handle, name = tempfile.mkstemp(prefix="flanders_", suffix=f".{audio_format}")
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
    save_path: str | os.PathLike[str] | None = None,
    **options,
) -> bool:
    """Synthesize and play `text`. True when audio was produced and played."""
    from flanders.flanders_audio import play

    out_path = save_path
    if out_path is None and keep:
        safe = "".join(char if char.isalnum() else "_" for char in text[:40]).strip("_")
        out_path = settings.ROOT / "state" / "audio" / f"{safe or 'line'}.wav"

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

    play(path)
    if save_path is None and not keep:
        with suppress(OSError):
            path.unlink()
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Flanders voice through Fish Audio.")
    parser.add_argument("text", nargs="*", help="Text to speak.")
    parser.add_argument("--voice", default=DEFAULT_VOICE_ID, help="Fish Audio voice model id.")
    parser.add_argument(
        "--model",
        default=None,
        help=f"TTS model header (default {DEFAULT_MODEL}, or FISH_AUDIO_MODEL).",
    )
    parser.add_argument("--format", default="wav", choices=["wav", "mp3", "pcm", "opus"])
    parser.add_argument("--speed", type=float, default=None, help="0.5 to 2.0, default 1.0.")
    parser.add_argument(
        "--temperature", type=float, default=None, help="Expressiveness, 0.1 to 1.0."
    )
    parser.add_argument(
        "--top-p", dest="top_p", type=float, default=None, help="Diversity, 0.1 to 1.0."
    )
    parser.add_argument("--style", default=None, help='Bracket style tag, e.g. "[cheerful]".')
    parser.add_argument("--save", metavar="PATH", help="Save to this path instead of a temp file.")
    parser.add_argument("--check", action="store_true", help="Report key and voice configuration.")
    args = parser.parse_args(argv)

    if args.check:
        from flanders import secret_store

        key = has_api_key()
        print(f"API key: {secret_store.describe('fish_audio')}")
        print(f"Voice id: {args.voice}")
        print(f"Model: {args.model or _model()}")
        return 0 if key else 1

    text = " ".join(args.text).strip()
    if not text:
        parser.error("give some text to speak")

    options = {
        "speed": args.speed,
        "temperature": args.temperature,
        "top_p": args.top_p,
        "style": args.style,
    }

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
