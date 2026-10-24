# Flanders

A Ned Flanders-voiced task assistant: it speaks, listens to a Slack channel, and
keeps its personality in the delivery while staying plain about the facts.

It is not a chat toy bolted onto a voice. The voice is cloned from a reference
sample, the speech engine falls back gracefully, and what reaches the speaker is
cleaned so icons and markup are never read aloud.

## What is in here

| Module | Role |
|---|---|
| `flanders/voice_integration.py` | Engine selection (hosted, local, Windows), `/flanders` command tree |
| `flanders/fish_audio_tts.py` | Hosted Fish Audio voice |
| `flanders/flanders_local_tts.py` | Offline Fish Speech clone |
| `flanders/flanders_speech.py` | Turns Slack text into speakable prose |
| `flanders/flanders_audio.py` | Playback with an explicit output device |
| `flanders/flanders_character.py` | Personality and task classification |
| `flanders/slack_bridge.py` | Reads and posts to the Slack channel |
| `flanders/flanders_service.py` | Windows service that owns the Slack listener |
| `flanders/flanders_speaker.py` | In-session speaker the service drives |
| `flanders/flanders_say.py` | Command-line bridge firstmate calls to speak text |

## Quick start

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-local.txt
.\.venv\Scripts\python.exe flanders\voice_integration.py
```

For the offline voice, run `scripts\setup_local.ps1` once; it fetches the model
and the reference sample. See [`docs/LOCAL_VOICE.md`](docs/LOCAL_VOICE.md).

## Commands

```
/flanders delegate <task>   classify the work and speak the guidance
/flanders help              this guide
/flanders modes             delivery modes and merge posture
/flanders status            the task on the desk
/flanders quit              leave
```

Plain text is read aloud but never answered. Only the commands above act.

## Tests

Automated checks:

```powershell
.\.venv\Scripts\python.exe tests\test_speech.py
.\.venv\Scripts\python.exe tests\test_commands.py
```

The audible checks live in `tests/manual/` because they play sound and need the
local model or a network key:

```powershell
.\.venv\Scripts\python.exe tests\manual\test_local_voice.py
```

## Project layout

```
flanders/     the package: voice, speech, Slack, and the Windows service
docs/         guides: local voice, service, and the agent skill
scripts/      setup and operations (venv, model, API key, service install)
tools/        diagnostics: audio devices, voice variants, benchmarks
tests/        automated checks; tests/manual/ holds the audible ones
references/   voice-clone transcript
```

The package runs directly (`python flanders\voice_integration.py`) or as a
module (`python -m flanders.voice_integration`).

## Documentation

- [`docs/LOCAL_VOICE.md`](docs/LOCAL_VOICE.md) - offline model setup, tuning, and cost notes
- [`docs/SERVICE.md`](docs/SERVICE.md) - the Windows service, and why there are two processes
- [`docs/SKILL.md`](docs/SKILL.md) - how firstmate drives the character

## Credentials

No credentials live in this repository. The hosted voice reads its key from
`fish_audio_key.txt`, which is ignored, or from `FISH_API_KEY`.

## Note on the voice

The voice is a clone of a public character sample, used here for a personal
assistant. It is not affiliated with or endorsed by the rights holders.
