#!/usr/bin/env python3
r"""Save and verify a Fish Audio API key.

Usage:
    .\.venv\Scripts\python.exe scripts\set_fish_key.py <key> [--no-test]

The key is written to fish_audio_key.txt beside this file. The file is read by
fish_audio_tts.py, which voice_integration.py uses for the hosted Drama 3 voice.

The default test spends a fraction of a cent to prove the key, the balance, and
the Flanders voice model all work together. Use --no-test to skip it.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

KEY_FILE = ROOT / "fish_audio_key.txt"
TEST_LINE = "Okily dokily, captain! The hosted voice is working just fine."


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("--")]
    if not args:
        print(__doc__)
        return 2

    key = args[0].strip()
    if len(key) < 20 or " " in key:
        print("That does not look like an API key.")
        return 2

    KEY_FILE.write_text(key + "\n", encoding="utf-8")
    print(f"Saved key to {KEY_FILE}")

    if "--no-test" in argv:
        return 0

    from flanders import fish_audio_tts

    print("Testing with one short line ...")
    path = fish_audio_tts.synthesize(TEST_LINE)
    if path is None:
        print("The key was saved, but the test failed. Fix the problem above, then:")
        print("  py fish_audio_tts.py \"Okily dokily!\"")
        return 1

    print(f"Success. Audio written to {path}")
    fish_audio_tts._play(path)
    try:
        path.unlink()
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
