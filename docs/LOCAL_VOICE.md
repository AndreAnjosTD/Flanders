# Flanders local voice

Flanders speaks through one of three engines, in this order:

| Engine | What it is | Cost | Needs |
|---|---|---|---|
| `hosted` | Fish Audio S2.1-Pro Free, Ned Flanders voice model | $0 | a free Fish Audio account |
| `local` | Fish Speech 1.5 running on this machine | free | the setup below |
| `sapi` | the built-in Windows voice | free | nothing |

The hosted voice is the fast path: instant, higher quality, and billed per
character. The local engine is the offline fallback: free and private, but about
three times slower than real time on this machine.

## What is installed

- `fish-speech/` - Fish Speech source at tag `v1.5.1` (Apache-2.0 code).
- `fish-speech/checkpoints/fish-speech-1.5/` - model weights (CC-BY-NC-SA-4.0).
- `.venv/` - isolated Python environment with PyTorch and the inference deps.
- `references/flanders_sample.wav` and `.txt` - the cloning reference and its
  exact transcript, taken from the public sample on the Fish Audio voice page.

## Setup

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup_local.ps1
```

Re-running is safe; finished steps are skipped.

## Use

```powershell
# one line
.\.venv\Scripts\python.exe flanders\flanders_local_tts.py "Okily dokily, captain!"

# type lines and hear each one
.\.venv\Scripts\python.exe flanders\flanders_local_tts.py --loop

# save to a file instead of playing
.\.venv\Scripts\python.exe flanders\flanders_local_tts.py --save out.wav "Praise the Lord!"

# readiness check
.\.venv\Scripts\python.exe flanders\flanders_local_tts.py --check

# the full command tree, with voice
.\.venv\Scripts\python.exe flanders\voice_integration.py
```

## How the voice is chosen

`flanders/voice_integration.py` picks `hosted` when a key is present, then `local` when
the weights and reference are present, then the Windows voice. If a hosted
request fails, the local voice takes over for that line. Force one with
`--engine local|hosted|sapi`.

## Hosted voice (Drama 3)

The same Ned Flanders voice is available on Fish Audio's Drama 3 model. It is
instant and higher quality, and it needs an API key plus a small prepaid balance.

1. Create a key at <https://fish.audio/app/api-keys/>.
2. Save and verify it:

```powershell
.\.venv\Scripts\python.exe scripts\set_fish_key.py <your-key>
```

The key is written to `fish_audio_key.txt` and read automatically. You can also
set `FISH_API_KEY` in the environment instead.

Fair-use limits apply to the free model. If a request is throttled or fails, the
local voice takes over for that line automatically.

Pricing: the default model is `s2.1-pro-free`, the same model as S2.1-Pro at $0
under fair-use limits, so a free account is enough and nothing is charged. Set
`FISH_AUDIO_MODEL=drama-3` to opt into the flagship Drama 3 model, which bills at
$50 per million UTF-8 bytes ($10 until 12 November 2026).

The voice model id is `8ca8ea05a29548758a9085747db19879`.

## Tuning the voice

`voice_settings.json` holds the knobs, so tuning never needs a code change:

```json
{
  "model": "s2.1-pro-free",
  "voice_id": "8ca8ea05a29548758a9085747db19879",
  "speed": 1.0,
  "temperature": 0.75,
  "top_p": 0.7,
  "style": "[warmly]"
}
```

This is the captain's preferred "neighbourly" setting: warm and conversation.

- `speed`: 0.5 to 2.0. Slower reads as gentler and more sermon-like.
- `temperature`: 0.1 to 1.0. Higher is more varied and lively, lower is steadier.
- `top_p`: 0.1 to 1.0. Diversity of delivery.
- `style`: an optional bracket tag such as `[cheerful]` or `[warmly]`.
- `model`: keep `s2.1-pro-free` for zero cost, or `drama-3` for the flagship.

To hear a comparison, run `tools/voice_variants.py`. It saves four readings of the
same line in `tests/voice/`:

| Variant | Character |
|---|---|
| `neutral` | steady pace, even warmth |
| `brighter` | quicker and more cheerful |
| `measured` | slower and gentler |
| `neighbourly` | warm and conversational |

Environment variables override the file: `FISH_AUDIO_SPEED`,
`FISH_AUDIO_TEMPERATURE`, `FISH_AUDIO_TOP_P`, `FISH_AUDIO_STYLE`,
`FISH_AUDIO_MODEL`, `FISH_AUDIO_VOICE_ID`.

## Speaking from firstmate

`flanders/flanders_say.py` is the bridge. Firstmate (or anything else) hands it text and
Flanders speaks it:

```powershell
.\.venv\Scripts\python.exe flanders\flanders_say.py "Okily dokily, captain!"
.\.venv\Scripts\python.exe flanders\flanders_say.py --file report.txt
Get-Content report.txt | .\.venv\Scripts\python.exe flanders\flanders_say.py
.\.venv\Scripts\python.exe flanders\flanders_say.py --engine local "Private line."
```

The hosted engine sends the text to Fish Audio. Use `--engine local` for
anything that should not leave this machine.

## Hardware

An RTX 4070 Laptop with 8 GB runs Fish Speech 1.5 comfortably. The model is
roughly 1.4 GB, and it fits in under 2 GB of GPU memory.

Measured on this machine: a 4-5 second line takes about 13-18 seconds to
generate, so roughly 3x slower than real time. The cause is that Fish Speech's
fast path depends on `torch.compile`, which the project does not support on
Windows. The GPU sits at about 40% utilisation because the decode loop is
limited by Python-side dispatch, not by memory bandwidth.

Drama 3 is a different story: 35B parameters and at least 48 GB of GPU memory,
so it is only practical through the hosted API or an H100/H200 server. It is not
a local option on this machine.

## Licences and rights

- Fish Speech code: Apache-2.0.
- Fish Speech 1.5 weights: CC-BY-NC-SA-4.0, non-commercial.
- The cloned voice is Ned Flanders, a copyrighted character. Personal use is
  fine; commercial use needs the rights.

## Changing the reference voice

Replace `references/flanders_sample.wav` with 10-30 seconds of clean
single-speaker audio and put the exact transcript in
`references/flanders_sample.txt`. Keep the WAV mono at 44.1 kHz.
