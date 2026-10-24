"""Download the public Flanders voice sample as a cloning reference.

The Fish Audio model page for this voice exposes one public sample together with
its exact transcript. That pair is exactly what a zero-shot clone needs, so no
manual recording is required to get started.
"""

import json
import urllib.parse
import urllib.request
from pathlib import Path

MODEL_ID = "8ca8ea05a29548758a9085747db19879"
OUT = Path(__file__).resolve().parent.parent / "references"

API = f"https://api.fish.audio/model/{MODEL_ID}"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    with urllib.request.urlopen(API, timeout=30) as response:
        model = json.load(response)

    samples = model.get("samples") or []
    if not samples:
        raise SystemExit("No public sample on this voice model.")

    sample = samples[0]
    text = sample.get("text") or model.get("default_text") or ""
    audio_url = sample.get("audio")
    if not audio_url:
        raise SystemExit("Sample has no audio URL.")
    if urllib.parse.urlsplit(audio_url).scheme != "https":
        raise SystemExit(f"Refusing a non-HTTPS sample URL: {audio_url}")

    audio_path = OUT / "flanders_sample.mp3"
    urllib.request.urlretrieve(audio_url, audio_path)  # noqa: S310 - https checked above

    text_path = OUT / "flanders_sample.txt"
    text_path.write_text(text.strip() + "\n", encoding="utf-8")

    print(f"voice    : {model.get('title')}")
    print(f"state    : {model.get('state')} / {model.get('train_mode')}")
    print(f"audio    : {audio_path} ({audio_path.stat().st_size / 1024:.0f} KB)")
    print(f"transcript: {text_path} ({len(text.split())} words)")
    print()
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
