#!/usr/bin/env python3
r"""Flanders' voice, running inside the captain's interactive session.

A Windows service lives in session 0, which has no audio endpoint - it can read
Slack all day but it cannot reach the speakers. So the service writes speech
jobs to state/speech/, and this small process (started by the service in the
logged-on session) takes them and speaks them out loud.

It is not meant to be run by hand, but it can be:
    .\.venv\Scripts\pythonw.exe flanders_speaker.py
    .\.venv\Scripts\python.exe  flanders_speaker.py --once

It exits when state/speaker.stop appears, or when told to stop.
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if __package__ in (None, ""):
    sys.path.insert(0, str(ROOT))

STATE = ROOT / "state"
QUEUE = STATE / "speech"
HEARTBEAT = STATE / "speaker.heartbeat"
PID_FILE = STATE / "speaker.pid"
LOCK_FILE = STATE / "speaker.lock"
STOP_FILE = STATE / "speaker.stop"
LOG = STATE / "speaker.log"

MAX_AGE_SECONDS = 600  # drop messages that piled up while nobody was listening


def log(text: str) -> None:
    line = f"{datetime.now().isoformat(timespec='seconds')} {text}"
    try:
        STATE.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except OSError:
        pass


def heartbeat(text: str = "ok") -> None:
    try:
        STATE.mkdir(parents=True, exist_ok=True)
        HEARTBEAT.write_text(
            f"{datetime.now().isoformat(timespec='seconds')} {text}\n",
            encoding="utf-8",
        )
    except OSError:
        pass


def _take_lock():
    """Prevent two speakers from reading the same queue."""
    try:
        import msvcrt

        STATE.mkdir(parents=True, exist_ok=True)
        handle = LOCK_FILE.open("a+")
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        return handle
    except (ImportError, OSError):
        return None


def drain(voice) -> int:
    """Speak every queued job, newest last. Returns how many were spoken."""
    if not QUEUE.is_dir():
        return 0

    spoken = 0
    for job in sorted(QUEUE.glob("*.job")):
        try:
            payload = json.loads(job.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            job.unlink(missing_ok=True)
            continue

        text = " ".join(str(payload.get("text", "")).split())
        try:
            age = time.time() - float(payload.get("epoch", 0))
        except (TypeError, ValueError):
            age = 0.0

        if not text:
            job.unlink(missing_ok=True)
            continue

        if age > MAX_AGE_SECONDS:
            log(f"dropped stale message ({int(age)}s old): {text[:80]}")
            job.unlink(missing_ok=True)
            continue

        try:
            used = voice.speak(text)
            log(f"spoke via {used}: {text[:80]}")
            spoken += 1
        except Exception as exc:  # noqa: BLE001 - one bad line must not stop the queue
            log(f"speak failed ({exc}): {text[:80]}")

        job.unlink(missing_ok=True)

    return spoken


def main(argv: list[str]) -> int:
    once = "--once" in argv
    STATE.mkdir(parents=True, exist_ok=True)
    STOP_FILE.unlink(missing_ok=True)

    lock = _take_lock()
    if lock is None and not once:
        log("another speaker already holds the queue; exiting")
        return 0

    PID_FILE.write_text(str(os.getpid()), encoding="utf-8")

    from flanders.voice_integration import FlandersVoice

    # Engine comes from voice_settings.json (online by default), so a user
    # switches between remote and local with one config value.
    voice = FlandersVoice()
    heartbeat("starting")
    log(f"speaker started (pid {os.getpid()}) engine={voice.engine}")

    # Speak deliberately blocks for seconds per line, so prove liveness from a
    # separate thread; otherwise the service thinks the speaker died mid-sentence
    # and starts another one.
    def beat() -> None:
        while True:
            heartbeat("ok")
            time.sleep(2.0)

    threading.Thread(target=beat, daemon=True).start()

    try:
        if once:
            drain(voice)
            return 0

        while True:
            if STOP_FILE.exists():
                log("stop requested")
                break
            drain(voice)
            time.sleep(1.0)
    except KeyboardInterrupt:
        pass
    finally:
        log("speaker stopped")
        PID_FILE.unlink(missing_ok=True)
        if lock is not None:
            lock.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
