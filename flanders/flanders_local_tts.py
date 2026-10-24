#!/usr/bin/env python3
"""
Flanders' local voice: Fish Speech 1.5 on the local GPU.

This runs entirely offline. It loads the 1.5 model once, clones the reference
voice, and speaks any string passed at runtime.

Model layout expected under fish-speech/checkpoints/fish-speech-1.5/:
    config.json
    model.pth
    firefly-gan-vq-fsq-8x1024-21hz-generator.pth
    tokenizer.tiktoken
    special_tokens.json

Reference voice expected under references/:
    flanders_sample.wav  (converted from the public sample if needed)
    flanders_sample.txt  (exact transcript)

Usage:
    py flanders_local_tts.py "Okily dokily, captain!"
    py flanders_local_tts.py --save out.wav "Praise the Lord!"
    py flanders_local_tts.py --loop          # type lines, hear each one
    py flanders_local_tts.py --check

Programmatic use:
    from flanders_local_tts import LocalFishVoice
    voice = LocalFishVoice()
    voice.speak("Hi-diddly-ho, neighborino!")
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from contextlib import suppress
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if __package__ in (None, ""):
    sys.path.insert(0, str(ROOT))

REPO = ROOT / "fish-speech"
LLAMA_DIR = REPO / "checkpoints" / "fish-speech-1.5"
DECODER_WEIGHTS = LLAMA_DIR / "firefly-gan-vq-fsq-8x1024-21hz-generator.pth"
DECODER_CONFIG = "firefly_gan_vq"

REF_DIR = ROOT / "references"
REF_WAV = REF_DIR / "flanders_sample.wav"
REF_MP3 = REF_DIR / "flanders_sample.mp3"
REF_TXT = REF_DIR / "flanders_sample.txt"


def _require_paths() -> None:
    missing = [
        str(p)
        for p in (LLAMA_DIR / "config.json", LLAMA_DIR / "model.pth", DECODER_WEIGHTS)
        if not p.exists()
    ]
    if missing:
        raise SystemExit(
            "Missing model files:\n  " + "\n  ".join(missing) + "\n"
            "Run the weight download step first."
        )
    if not REF_WAV.exists():
        raise SystemExit(
            f"Missing reference WAV {REF_WAV}. Run scripts/prepare_reference.py first."
        )
    if not REF_TXT.exists():
        raise SystemExit(f"Missing reference transcript {REF_TXT}.")


def _play(path: Path) -> None:
    from flanders.flanders_audio import play

    play(path)


class LocalFishVoice:
    """Holds the Fish Speech engine in memory and speaks arbitrary strings."""

    def __init__(self, device: str | None = None, half: bool = False) -> None:
        _require_paths()

        import torch

        sys.path.insert(0, str(REPO))

        from fish_speech.inference_engine import TTSInferenceEngine
        from fish_speech.models.text2semantic.inference import launch_thread_safe_queue
        from fish_speech.models.vqgan.inference import load_model as load_decoder_model

        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = device
        if device.startswith("cuda"):
            self.precision = torch.float16 if half else torch.bfloat16
        else:
            self.precision = torch.float32

        print(f"Loading Fish Speech 1.5 on {device} ...", flush=True)
        self.llama_queue = launch_thread_safe_queue(
            checkpoint_path=str(LLAMA_DIR),
            device=device,
            precision=self.precision,
            compile=False,
        )
        self.decoder_model = load_decoder_model(
            config_name=DECODER_CONFIG,
            checkpoint_path=str(DECODER_WEIGHTS),
            device=device,
        )
        self.engine = TTSInferenceEngine(
            llama_queue=self.llama_queue,
            decoder_model=self.decoder_model,
            precision=self.precision,
            compile=False,
        )

        self.reference_audio = REF_WAV.read_bytes()
        self.reference_text = REF_TXT.read_text(encoding="utf-8").strip()
        print("Voice ready.", flush=True)

    def synthesize(self, text: str, out_path: str | os.PathLike[str] | None = None) -> Path:
        """Generate speech for `text` and write a WAV file."""
        import numpy as np
        import soundfile as sf
        from fish_speech.utils.schema import ServeReferenceAudio, ServeTTSRequest

        request = ServeTTSRequest(
            text=text,
            references=[ServeReferenceAudio(audio=self.reference_audio, text=self.reference_text)],
            reference_id=None,
            max_new_tokens=1024,
            chunk_length=200,
            top_p=0.7,
            repetition_penalty=1.2,
            temperature=0.7,
            format="wav",
            streaming=False,
            normalize=True,
            use_memory_cache="on",
        )

        final_audio = None
        sample_rate = 44100
        for result in self.engine.inference(request):
            if result.code == "error":
                raise RuntimeError(f"Generation failed: {result.error}")
            if result.code == "final" and isinstance(result.audio, tuple):
                sample_rate, final_audio = result.audio

        if final_audio is None:
            raise RuntimeError("No audio was generated.")

        audio = np.asarray(final_audio)
        if audio.ndim > 1:
            audio = audio.squeeze()
        audio = np.clip(audio, -1.0, 1.0)

        if out_path is None:
            handle, name = tempfile.mkstemp(prefix="flanders_", suffix=".wav")
            os.close(handle)
            path = Path(name)
        else:
            path = Path(out_path)

        path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(path), audio, sample_rate)
        return path

    def speak(
        self,
        text: str,
        keep: bool = False,
        save_path: str | os.PathLike[str] | None = None,
    ) -> Path | None:
        """Generate and play `text`. Returns the path when the audio is kept."""
        out = save_path
        if out is None and keep:
            safe = "".join(c if c.isalnum() else "_" for c in text[:40]).strip("_")
            out = ROOT / "state" / "audio" / f"{safe or 'line'}.wav"

        path = self.synthesize(text, out_path=out)
        _play(path)
        if save_path is not None or keep:
            return path
        with suppress(OSError):
            path.unlink()
        return None


def check() -> int:
    problems = []
    for path in (LLAMA_DIR / "config.json", LLAMA_DIR / "model.pth", DECODER_WEIGHTS):
        problems.append(f"{'ok  ' if path.exists() else 'MISS'} {path}")
    for path in (REF_WAV, REF_TXT):
        problems.append(f"{'ok  ' if path.exists() else 'MISS'} {path}")
    print("\n".join(problems))
    try:
        import torch

        print(f"torch: {torch.__version__} cuda={torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"gpu  : {torch.cuda.get_device_name(0)}")
    except Exception as exc:
        print(f"torch unavailable in this interpreter: {exc}")
    return 0 if all("MISS" not in line for line in problems) else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Flanders local Fish Speech voice.")
    parser.add_argument("text", nargs="*", help="Text to speak.")
    parser.add_argument("--save", metavar="PATH", help="Write WAV to this path.")
    parser.add_argument("--loop", action="store_true", help="Speak each typed line.")
    parser.add_argument("--check", action="store_true", help="Report files and GPU.")
    parser.add_argument("--device", default=None, help="cuda or cpu.")
    parser.add_argument("--half", action="store_true", help="Use fp16 on GPU.")
    args = parser.parse_args(argv)

    if args.check:
        return check()

    if args.loop:
        voice = LocalFishVoice(device=args.device, half=args.half)
        print("Type a line and press Enter. Empty line or Ctrl+C exits.")
        while True:
            try:
                line = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not line:
                break
            voice.speak(line)
        return 0

    text = " ".join(args.text).strip()
    if not text:
        parser.error("give some text to speak")

    voice = LocalFishVoice(device=args.device, half=args.half)
    if args.save:
        path = voice.synthesize(text, out_path=args.save)
        print(f"Saved {path}")
        return 0

    voice.speak(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
