#!/usr/bin/env python3
r"""Bridge: speak any text through Flanders' voice.

This is the piece firstmate calls. It accepts text on the command line, from a
file, or on standard input, and picks the best available voice.

Usage:
    .\.venv\Scripts\python.exe flanders_say.py "Okily dokily, captain!"
    .\.venv\Scripts\python.exe flanders_say.py --file report.txt
    Get-Content report.txt | .\.venv\Scripts\python.exe flanders_say.py
    .\.venv\Scripts\python.exe flanders_say.py --engine local "Offline line."

Engine choices:
    auto    hosted free model first, then the local model, then the Windows voice
    hosted  Fish Audio s2.1-pro-free (sends the text to Fish Audio)
    local   Fish Speech 1.5 on this machine (offline, private, slower)
    sapi    the built-in Windows voice

Privacy:
    The hosted engine sends the text to Fish Audio. Use --engine local for
    anything that should not leave this machine.

Exit codes:
    0  spoken
    1  nothing spoken
    2  bad usage
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from voice_integration import FlandersVoice  # noqa: E402


def read_text(args: argparse.Namespace) -> str:
    if args.text:
        return " ".join(args.text).strip()
    if args.file:
        return Path(args.file).read_text(encoding="utf-8").strip()
    if not sys.stdin.isatty():
        return sys.stdin.read().strip()
    return ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Speak text through Flanders.")
    parser.add_argument("text", nargs="*", help="Text to speak.")
    parser.add_argument("--file", help="Read the text from this file.")
    parser.add_argument(
        "--engine",
        default="auto",
        choices=["auto", "hosted", "local", "sapi"],
        help="Which voice to use.",
    )
    args = parser.parse_args(argv)

    text = read_text(args)
    if not text:
        print("No text to speak.", file=sys.stderr)
        return 2

    voice = FlandersVoice(engine=args.engine)
    used = voice.speak(text)
    if used in ("failed", "nothing"):
        print(f"Speech failed on engine {voice.engine}.", file=sys.stderr)
        return 1

    print(f"spoken via {used}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
