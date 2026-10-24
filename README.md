<p align="center">
  <img src="docs/banner.png" alt="Flanders — a neighbourly voice for task delegation" width="100%">
</p>

<p align="center">
  <img alt="Python 3.12" src="https://img.shields.io/badge/python-3.12-3776AB?logo=python&logoColor=white">
  <img alt="Platform: Windows" src="https://img.shields.io/badge/platform-Windows-0078D4?logo=windows&logoColor=white">
  <img alt="Voices: hosted, local, SAPI" src="https://img.shields.io/badge/voices-hosted%20%7C%20local%20%7C%20SAPI-brightgreen">
  <img alt="Mood: okily dokily" src="https://img.shields.io/badge/mood-okily%20dokily-yellowgreen">
  <img alt="Repository: private" src="https://img.shields.io/badge/repository-private-lightgrey?logo=github">
</p>

# Flanders

Hi-diddly-ho! This here is a task assistant with the voice of Springfield's
friendliest neighbour and the manners to match. It reads a Slack channel out
loud, keeps the personality in the delivery, and stays plain about the facts — no
dressing up a failure as a success, and no hollering about routine progress.

Okily dokily. Aw, hamburgers, one honest note before the tour: the voice is a
clone of a public character sample, put to work here for a personal assistant. It
is not affiliated with, or endorsed by, anybody official.

---

## 🎙️ What it does

- **Speaks any text handed to it**, through the best voice it can find.
- **Watches a Slack channel** and reads new messages aloud.
- **Cleans Slack text first**, so emoji codes and markup never come out as
  "colon wave colon".
- **Keeps quiet on noise** — acknowledgements and command help are skipped,
  because "great!" does not need a public announcement.
- **Runs as a Windows service** — no console window, no supervisor script, and it
  restarts itself if it trips.

## 🧩 The pieces

| Module | What it does |
|---|---|
| `flanders/voice_integration.py` | Picks the voice engine and owns the `/flanders` command tree |
| `flanders/fish_audio_tts.py` | Hosted Fish Audio voice, free tier |
| `flanders/flanders_local_tts.py` | Offline Fish Speech clone on the local GPU |
| `flanders/flanders_speech.py` | Turns Slack text into speakable prose |
| `flanders/flanders_audio.py` | Plays audio on a chosen output device |
| `flanders/flanders_character.py` | Personality and task classification |
| `flanders/slack_bridge.py` | Reads and posts to the Slack channel |
| `flanders/flanders_service.py` | The Windows service that owns the listener |
| `flanders/flanders_speaker.py` | The in-session speaker the service drives |
| `flanders/flanders_say.py` | The command-line bridge firstmate calls to speak text |

## 🛠️ How a message becomes speech

```mermaid
flowchart LR
  A["Slack: #firstmate"] --> B["FlandersSlackWatch<br/>Windows service<br/>(session 0)"]
  B --> C[("Speech queue")]
  C --> D["flanders_speaker.py<br/>(logged-on session)"]
  D --> E{"Voice engine"}
  E --> F["Hosted · Fish Audio"]
  E --> G["Local · Fish Speech"]
  E --> H["Fallback · Windows SAPI"]
  F --> I(("Speakers"))
  G --> I
  H --> I
```

Windows keeps services on a separate desktop with no audio endpoint, so a service
can read Slack all day and still never make a sound. That is why the work is
split in two: **the service listens**, and a small companion in the logged-on
session **does the talking**. The service starts that companion itself and keeps
it alive.

## 🎚️ The voice ladder

Three engines, tried in order, so a network hiccup never leaves the room silent:

| Order | Engine | Notes |
|---|---|---|
| 1 | **Hosted** — Fish Audio `s2.1-pro-free` | Free under fair-use limits; needs a key |
| 2 | **Local** — Fish Speech 1.5 | Offline, free, cloned from the reference sample; slower |
| 3 | **Fallback** — Windows SAPI | Robotic, but always there |

## ⚡ Quick start

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-local.txt
.\.venv\Scripts\python.exe flanders\voice_integration.py
```

The offline voice needs one extra pass to fetch the model and the reference
sample:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup_local.ps1
```

Much obliged to [`docs/LOCAL_VOICE.md`](docs/LOCAL_VOICE.md) for the details.

## 🗣️ The command tree

```
/flanders delegate <task>   classify the work and speak the guidance
/flanders help              the guide
/flanders modes             delivery modes and merge posture
/flanders status            the task on the desk
/flanders quit              leave
```

Plain text is read aloud but never answered, and never turned into a task. Only
the commands above actually do something.

## ✅ Tests

Automated checks, safe to run anywhere:

```powershell
.\.venv\Scripts\python.exe tests\test_speech.py
.\.venv\Scripts\python.exe tests\test_commands.py
```

The audible checks live in `tests/manual/`, because they play sound and need the
local model or a network key:

```powershell
.\.venv\Scripts\python.exe tests\manual\test_local_voice.py
```

## 🗂️ Project layout

```
flanders/     the package: voice, speech, Slack, and the Windows service
docs/         guides: local voice, service, and the agent skill
scripts/      setup and operations (venv, model, API key, service install)
tools/        diagnostics: audio devices, voice probe, benchmarks
tests/        automated checks; tests/manual/ holds the audible ones
references/   voice-clone transcript
```

The package runs directly (`python flanders\voice_integration.py`) or as a module
(`python -m flanders.voice_integration`).

## 📚 Documentation

- [`docs/LOCAL_VOICE.md`](docs/LOCAL_VOICE.md) — offline model, tuning, and cost notes
- [`docs/SERVICE.md`](docs/SERVICE.md) — the service, and why there are two processes
- [`docs/SKILL.md`](docs/SKILL.md) — how firstmate drives the character

## 🔐 Credentials

No credentials live in this repository. The hosted voice reads its key from
`fish_audio_key.txt`, which is ignored by git, or from `FISH_API_KEY`. To store a
key safely:

```powershell
.\.venv\Scripts\python.exe scripts\set_fish_key.py <the-key>
```

## ⚖️ A note on the voice

The voice is a clone of a public character sample, used for a personal assistant.
No affiliation with, or endorsement by, the rights holders is claimed or implied.

---

<p align="center"><em>Okily dokily! Much obliged for reading.</em></p>
