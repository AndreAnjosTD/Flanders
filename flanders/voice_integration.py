#!/usr/bin/env python3
"""
Flanders voice integration.

Speaks Flanders' replies through the best voice available, in this order:

1. hosted - Fish Audio Drama 3 with the Ned Flanders voice model (needs a key)
2. local  - Fish Speech 1.5 on this machine (offline, free, cloned voice)
3. sapi   - the built-in Windows voice (robotic last resort)

If the hosted voice fails, the local one takes over automatically.

Every engine accepts an arbitrary string at runtime, so nothing is generated
per phrase.

Commands:
    /flander delegate <task>   classify a task and speak the result
    /flander help              show the command guide
    /flander modes             show delivery modes
    /flander status            show the last task
    /flander quit              leave

Programmatic use:
    from voice_integration import FlandersVoice
    FlandersVoice().speak("Okily dokily, captain!")
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if __package__ in (None, ""):
    sys.path.insert(0, str(ROOT))

from flanders.flanders_character import classify_task, flanders_response  # noqa: E402

try:
    from flanders import fish_audio_tts
except Exception:  # noqa: BLE001
    fish_audio_tts = None

try:
    from flanders import flanders_local_tts
except Exception:  # noqa: BLE001
    flanders_local_tts = None


HELP_TEXT = """\
Flanders command guide

  /flander delegate <task>   classify the work and speak the guidance
  /flander help              this guide
  /flander modes             delivery modes and merge posture
  /flander status            the task on the desk
  /flander quit              leave Flanders' station

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


class FlandersVoice:
    def __init__(self, engine: str = "auto", device: str | None = None) -> None:
        self.device = device
        self._local = None
        self.last_task: str | None = None
        self.last_classification: str | None = None
        self.engine = self._resolve_engine(engine)

    # -- engine selection -------------------------------------------------

    def _local_ready(self) -> bool:
        if flanders_local_tts is None:
            return False
        try:
            import torch  # noqa: F401
        except Exception:  # noqa: BLE001
            return False
        files = [
            HERE / "fish-speech" / "checkpoints" / "fish-speech-1.5" / "config.json",
            HERE / "fish-speech" / "checkpoints" / "fish-speech-1.5" / "model.pth",
            HERE / "fish-speech" / "checkpoints" / "fish-speech-1.5"
            / "firefly-gan-vq-fsq-8x1024-21hz-generator.pth",
            HERE / "references" / "flanders_sample.wav",
            HERE / "references" / "flanders_sample.txt",
        ]
        return all(path.exists() for path in files)

    def _hosted_ready(self) -> bool:
        return fish_audio_tts is not None and bool(fish_audio_tts._api_key())

    def _resolve_engine(self, requested: str) -> str:
        if requested == "local":
            return "local"
        if requested == "hosted":
            return "hosted"
        if requested == "sapi":
            return "sapi"
        if requested != "auto":
            raise ValueError(f"unknown engine: {requested}")

        if self._hosted_ready():
            return "hosted"
        if self._local_ready():
            return "local"
        return "sapi"

    # -- speaking ---------------------------------------------------------

    def speak(self, text: str, keep: bool = False) -> str:
        """Speak `text` and return the engine that handled it."""
        text = (text or "").strip()
        if not text:
            return "nothing"

        if self.engine == "local":
            if self._local is None:
                self._local = flanders_local_tts.LocalFishVoice(device=self.device)
            self._local.speak(text, keep=keep)
            return "local"

        if self.engine == "hosted":
            if fish_audio_tts.speak(text, keep=keep):
                return "hosted"
            if self._local_ready():
                print("Hosted voice failed; using the local voice instead.")
                if self._local is None:
                    self._local = flanders_local_tts.LocalFishVoice(device=self.device)
                self._local.speak(text, keep=keep)
                return "local"
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
        except Exception as exc:  # noqa: BLE001
            print(f"Windows speech failed: {exc}")
            return "failed"

    # -- tasks ------------------------------------------------------------

    def delegate_task(self, task_description: str) -> dict:
        task_description = task_description.strip()
        if not task_description:
            raise ValueError("no task given")

        classification = classify_task(task_description)
        response = flanders_response(task_description)

        self.last_task = task_description
        self.last_classification = classification

        spoken = (
            f"Okily dokily! Task: {task_description}. "
            f"Classification: {classification}. {response}"
        )

        print()
        print(f"Task           : {task_description}")
        print(f"Classification : {classification}")
        print()
        print(response)
        print()

        engine = self.speak(spoken)
        print(f"[voice: {engine}]")
        return {
            "task": task_description,
            "classification": classification,
            "response": response,
            "voice": engine,
        }

    def process_flander_command(self, command: str, args: list[str]) -> str:
        """Handle the /flander command tree. Returns the reply text."""
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
                reply = "No task on the desk yet, captain. Say /flander delegate <task>."
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


COMMAND_NAMES = ("/flander", "/flanders")
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
    return voice.process_flander_command(head, parts[1:])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Flanders voice and commands.")
    parser.add_argument("text", nargs="*", help="Say this and exit.")
    parser.add_argument("--engine", default="auto", choices=["auto", "local", "hosted", "sapi"])
    parser.add_argument("--device", default=None, help="cuda or cpu for the local engine.")
    parser.add_argument("--save", metavar="PATH", help="Save the audio instead of playing.")
    args = parser.parse_args(argv)

    voice = FlandersVoice(engine=args.engine, device=args.device)
    print(f"Voice engine: {voice.engine}")

    text = " ".join(args.text).strip()
    if text:
        print(f"[voice: {voice.speak(text, keep=bool(args.save))}]")
        return 0

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
