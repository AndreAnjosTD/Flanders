# Flanders

A Ned Flanders-voiced task assistant: it speaks, listens to a Slack channel, and
keeps its personality in the delivery while staying plain about the facts.

It is not a chat toy bolted onto a voice. The voice is cloned from a reference
sample, the speech engine falls back gracefully, and what reaches the speaker is
cleaned so icons and markup are never read aloud.

## What is in here

| File | Role |
|---|---|
| `voice_integration.py` | Engine selection (hosted, local, Windows), `/flanders` command tree |
| `fish_audio_tts.py` | Hosted Fish Audio voice |
| `flanders_local_tts.py` | Offline Fish Speech clone |
| `flanders_speech.py` | Turns Slack text into speakable prose |
| `flanders_audio.py` | Playback with an explicit output device |
| `flanders_character.py` | Personality and task classification |
| `slack_bridge.py` | Reads and posts to the Slack channel |
| `flanders_service.py` | Windows service that owns the Slack listener |
| `flanders_speaker.py` | In-session speaker the service drives |

## Quick start

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-local.txt
.\.venv\Scripts\python.exe voice_integration.py
```

For the offline voice, run `setup_local.ps1` once; it fetches the model and the
reference sample. See `LOCAL_VOICE.md`.

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

```powershell
.\.venv\Scripts\python.exe tests\test_speech.py
.\.venv\Scripts\python.exe tests\test_commands.py
```

## Documentation

- `LOCAL_VOICE.md` - offline model setup, tuning, and cost notes
- `SERVICE.md` - the Windows service, and why there are two processes
- `SKILL.md` - how firstmate drives the character

## Credentials

No credentials live in this repository. The hosted voice reads its key from
`fish_audio_key.txt`, which is ignored, or from `FISH_API_KEY`.

## Note on the voice

The voice is a clone of a public character sample, used here for a personal
assistant. It is not affiliated with or endorsed by the rights holders.
