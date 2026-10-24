#!/usr/bin/env python3
"""Flanders' voice selection and the ``/flanders`` command tree.

Speaks through the best engine available, in this order:

1. ``hosted`` — Fish Audio with the Ned Flanders model (needs a key, fast)
2. ``local``  — Fish Speech 1.5 on this machine (offline, cloned, slower)
3. ``sapi``   — the built-in Windows voice (last resort)

`voice_settings.json` picks the preference (``online`` by default) and an
explicit ``--engine`` overrides it for one run. Every engine takes an arbitrary
string at runtime, so nothing is ever generated per phrase.

Commands:
    /flanders delegate <task>   classify a task and speak the guidance
    /flanders help              the command guide
    /flanders modes             delivery modes and merge posture
    /flanders status            the task on the desk
    /flanders quit              leave

Programmatic use:
    from flanders.voice_integration import FlandersVoice
    FlandersVoice().speak("Okily dokily, captain!")
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if __package__ in (None, ""):
    sys.path.insert(0, str(ROOT))

from flanders import settings  # noqa: E402
from flanders.flanders_character import classify_task, task_response  # noqa: E402

try:
    from flanders import fish_audio_tts
except Exception:
    fish_audio_tts = None

try:
    from flanders import flanders_local_tts
except Exception:
    flanders_local_tts = None

# What a user writes in voice_settings.json, and what it means internally.
_ENGINE_ALIASES = {
    "online": "hosted",
    "remote": "hosted",
    "hosted": "hosted",
    "offline": "offline",
    "local": "local",
    "sapi": "sapi",
    "auto": "auto",
}

HELP_TEXT = """\
Flanders command guide

  /flanders delegate <task>   classify the work and speak the guidance
  /flanders help              this guide
  /flanders modes             delivery modes and merge posture
  /flanders status            the task on the desk
  /flanders quit              leave Flanders' station

Plain text is read aloud only. Only the commands above are acted on.
"""

MODES_TEXT = """\
Delivery modes

  no-mistakes   full pipeline through a pull request, then your merge call
  direct-PR     push and open a pull request without the full pipeline
  local-only    stop on a ready local branch, then your merge call

Merge posture

  yolo off      you approve every merge
  yolo on       firstmate merges green, in-scope work itself
"""


def configured_engine() -> str:
    """The engine chosen in voice_settings.json.

    A user picks "online" or "offline"; the hosted voice is the default so the
    slow local model is opt-in rather than a surprise.
    """
    value = settings.text("engine", "hosted").lower()
    return _ENGINE_ALIASES.get(value, "hosted")


class FlandersVoice:
    """One speaking voice, with the engine chosen once at construction."""

    def __init__(self, engine: str | None = None, device: str | None = None) -> None:
        self.device = device
        self._local = None
        self.last_task: str | None = None
        self.last_classification: str | None = None
        # Explicit argument wins, then voice_settings.json, then the hosted voice.
        self.engine = self._resolve_engine(engine or configured_engine())

    # -- engine selection -------------------------------------------------

    def _local_ready(self) -> bool:
        """True when the offline model, torch, and the reference clip are all there."""
        if flanders_local_tts is None:
            return False
        try:
            import torch  # noqa: F401
        except Exception:
            return False
        checkpoint = ROOT / "fish-speech" / "checkpoints" / "fish-speech-1.5"
        files = [
            checkpoint / "config.json",
            checkpoint / "model.pth",
            checkpoint / "firefly-gan-vq-fsq-8x1024-21hz-generator.pth",
            ROOT / "references" / "flanders_sample.wav",
            ROOT / "references" / "flanders_sample.txt",
        ]
        return all(path.exists() for path in files)

    def _hosted_ready(self) -> bool:
        return fish_audio_tts is not None and fish_audio_tts.has_api_key()

    def _resolve_engine(self, requested: str) -> str:
        requested = _ENGINE_ALIASES.get(str(requested).strip().lower(), requested)

        if requested == "local":
            return "local"
        if requested == "sapi":
            return "sapi"
        if requested == "hosted":
            # Prefer the hosted voice, but never strand a message when no key is
            # present; fall through to the local model, then the Windows voice.
            if self._hosted_ready():
                return "hosted"
            return "local" if self._local_ready() else "sapi"
        if requested == "offline":
            # Background speech: local when available, otherwise the Windows
            # voice. Never the hosted engine, which needs a session key.
            return "local" if self._local_ready() else "sapi"
        if requested != "auto":
            raise ValueError(f"unknown engine: {requested}")

        if self._hosted_ready():
            return "hosted"
        if self._local_ready():
            return "local"
        return "sapi"

    # -- speaking ---------------------------------------------------------

    def _local_voice(self):
        if self._local is None:
            self._local = flanders_local_tts.LocalFishVoice(device=self.device)
        return self._local

    def speak(
        self,
        text: str,
        keep: bool = False,
        save_path: str | os.PathLike[str] | None = None,
    ) -> str:
        """Speak `text` and return the engine that handled it.

        `save_path` writes the audio there and leaves it in place; `keep` keeps
        it under ``state/audio``. Failures fall through to the next engine so a
        message is never silently dropped.
        """
        text = (text or "").strip()
        if not text:
            return "nothing"

        if self.engine == "local":
            try:
                self._local_voice().speak(text, keep=keep, save_path=save_path)
                return "local"
            except Exception as exc:
                print(f"Local voice failed ({exc}); using the Windows voice.")
                return self._speak_sapi(text)

        if self.engine == "hosted":
            if fish_audio_tts.speak(text, keep=keep, save_path=save_path):
                return "hosted"
            if self._local_ready():
                print("Hosted voice failed; using the local voice instead.")
                try:
                    self._local_voice().speak(text, keep=keep, save_path=save_path)
                    return "local"
                except Exception as exc:
                    print(f"Local voice failed ({exc}); using the Windows voice.")
            return self._speak_sapi(text)

        return self._speak_sapi(text)

    def _speak_sapi(self, text: str) -> str:
        try:
            import pyttsx3

            engine = pyttsx3.init()
            engine.setProperty("rate", 150)
            engine.setProperty("volume", 0.95)
            engine.say(text)
            engine.runAndWait()
            return "sapi"
        except Exception as exc:
            print(f"Windows speech failed: {exc}")
            return "failed"

    # -- tasks ------------------------------------------------------------

    def delegate_task(self, task_description: str) -> dict:
        task_description = task_description.strip()
        if not task_description:
            raise ValueError("no task given")

        response = task_response(task_description)
        classification = classify_task(task_description)

        self.last_task = task_description
        self.last_classification = classification

        print()
        print(f"Task           : {task_description}")
        print(f"Classification : {classification}")
        print()
        print(response.detail)
        print()

        engine = self.speak(f"Task noted. {response.headline} Classification: {classification}.")
        print(f"[voice: {engine}]")
        return {
            "task": task_description,
            "classification": classification,
            "response": response.render(),
            "voice": engine,
        }

    def process_command(self, args: list[str]) -> str:
        """Handle one ``/flanders`` command. Returns the reply text."""
        sub = args[0].lower() if args else "help"
        rest = args[1:]

        if sub in ("help", ""):
            reply = HELP_TEXT
        elif sub == "modes":
            reply = MODES_TEXT
        elif sub == "status":
            if self.last_task:
                reply = (
                    f"Task           : {self.last_task}\n"
                    f"Classification : {self.last_classification}\n"
                    f"Voice          : {self.engine}"
                )
            else:
                reply = "No task on the desk yet, captain. Say /flanders delegate <task>."
            print(reply)
            return reply
        elif sub == "quit":
            reply = "Okily dokily! May the Lord watch over your tasks until next we meet!"
            print(reply)
            self.speak(reply)
            return reply
        elif sub == "delegate":
            task = " ".join(rest).strip()
            if not task:
                reply = "Give me the task after the command, captain."
                print(reply)
                return reply
            self.delegate_task(task)
            return "delegated"
        else:
            # An unknown flag is the one case that deserves a spoken reply.
            message = f"I do not know '{sub}', captain."
            print(message)
            print()
            print(HELP_TEXT)
            self.speak(message)
            return message

        print(reply)
        self.speak(reply)
        return reply


COMMAND_NAMES = ("/flanders", "/flander")
QUIT_NAMES = ("/quit", "quit", "exit", "q")
QUIT = object()


class ReadAloud:
    """Ordinary words: say them out loud, but do not answer them."""

    __slots__ = ("text",)

    def __init__(self, text: str) -> None:
        self.text = text

    def __repr__(self) -> str:  # helps test output
        return f"ReadAloud({self.text!r})"


def handle_line(voice, line: str):
    """Dispatch one typed line.

    Returns:
        QUIT        - leave the session
        ReadAloud   - ordinary text: speak it, send no reply
        None        - nothing to do at all
        str         - a command reply, already printed and spoken by the handler
    """
    line = (line or "").strip()
    if not line:
        return None

    parts = line.split()
    head = parts[0].lower()

    if head in QUIT_NAMES:
        return QUIT
    if head not in COMMAND_NAMES:
        # A slash command that is not ours stays completely inert. Plain words
        # are read out loud, but they never become a task or a Slack message.
        if head.startswith("/"):
            return None
        return ReadAloud(line)
    return voice.process_command(parts[1:])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Flanders voice and commands.")
    parser.add_argument("text", nargs="*", help="Say this and exit.")
    parser.add_argument(
        "--engine",
        default=None,
        choices=["auto", "online", "offline", "hosted", "local", "sapi"],
        help="Override voice_settings.json.",
    )
    parser.add_argument("--device", default=None, help="cuda or cpu for the local engine.")
    parser.add_argument("--save", metavar="PATH", help="Write the audio here instead of playing.")
    args = parser.parse_args(argv)

    voice = FlandersVoice(engine=args.engine, device=args.device)
    print(f"Voice engine: {voice.engine}")

    text = " ".join(args.text).strip()
    if text:
        used = voice.speak(text, save_path=args.save)
        print(f"[voice: {used}]")
        return 0 if used not in ("failed", "nothing") else 1

    if args.save:
        print("Nothing to save: give the text to speak on the command line.", file=sys.stderr)
        return 2

    print()
    print(HELP_TEXT)
    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue

        result = handle_line(voice, line)
        if result is QUIT:
            voice.speak("Okily dokily! Until next time, captain!")
            break
        if isinstance(result, ReadAloud):
            # Ordinary words are spoken, never answered and never sent onward.
            voice.speak(result.text)
        # None means there is nothing to do; a command reply has already
        # printed and spoken itself. Either way the loop stays quiet.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
