# The Flanders Slack service

`FlandersSlackWatch` is a real Windows service. It reads `#firstmate` and speaks
new messages out loud. It replaced the old scheduled task + PowerShell
supervisor, which kept dying with `0xC000013A` because it depended on a console
and a three-layer process chain.

## Why there are two processes

Windows services run in **session 0**, which has no audio endpoint. A service can
read Slack all day but it cannot reach the captain's speakers — that is Windows
session isolation, not a bug in this code.

So the work is split:

| Process | Runs as | Session | Job |
|---|---|---|---|
| `FlandersSlackWatch` service | LocalSystem | 0 | Polls Slack, writes speech jobs |
| `flanders/flanders_speaker.py` | the captain | 1 | Reads the jobs, speaks them |

The service starts the speaker itself by duplicating the logged-on user's token
(`WTSQueryUserToken` + `CreateProcessAsUser`). No scheduled task, no PowerShell,
no visible window anywhere.

If nobody is logged on, the service keeps listening and queues jobs. The speaker
starts as soon as a session appears. Jobs older than 10 minutes are dropped
rather than replayed, so a long logout does not produce a wall of speech.

The speaker always runs an **offline** engine — the local model, then the Windows
voice. It never uses the hosted engine, because the service holds no key and
never reaches a secret store. Hosted speech belongs to interactive sessions
where a key is supplied for that session.

## What gets spoken

Slack text is written for eyes. `flanders/flanders_speech.py` turns it into speech:

- **Icons** are dropped, except a short meaningful set spoken as words:
  Done, Warning, Alert, Blocked, Idea.
- **Bold, italic, strike, backticks** lose their markers; the words stay.
- **`&gt;` and friends** are decoded instead of spelled out.
- **Links** are read as their label; a bare URL becomes "a link".
- **Mentions** are read as the person's name, never `<@U123>`.
- **Units** are expanded: `1m` is "1 minute", `3h` is "3 hours".
- **Command help** is removed, so "Reply with `/flanders answer ...`" is never
  read aloud, while the question that preceded it is kept.
- **Acknowledgements** are skipped entirely: "ok", "great", "thanks",
  "sounds good", and bare yes/no.
- **Long messages** stop around 600 characters with "And more."

The raw text still goes to the log, so nothing is lost.

Preview real messages, or check the rules:

```powershell
.\.venv\Scripts\python.exe flanders\flanders_speech.py --preview
.\.venv\Scripts\python.exe tests\test_speech.py
```

## Commands

Install, start and stop need an elevated prompt (administrator):

```powershell
cd C:\Users\abanj\Dev\Flanders
.\.venv\Scripts\python.exe flanders\flanders_service.py install
.\.venv\Scripts\python.exe flanders\flanders_service.py status
.\.venv\Scripts\python.exe flanders\flanders_service.py stop
.\.venv\Scripts\python.exe flanders\flanders_service.py start
.\.venv\Scripts\python.exe flanders\flanders_service.py uninstall
```

`install` also deletes the old scheduled task, so the two can never double up.
The service is set to start automatically at boot and to restart 5s, 10s, then
30s after a failure.

Foreground debugging (no service, prints to the console):

```powershell
.\.venv\Scripts\python.exe flanders\flanders_service.py run
```

## Choosing the output device

The speaker is launched by the service, so it does **not** inherit a shell's
environment variables. The device therefore lives in `voice_settings.json`:

```json
{ "audio_device": "Headset Earphone (Jabra EVOLVE LINK MS)" }
```

Either a name fragment or a numeric index from `tools/audio_devices.py --list` works.
Leave it empty to use the Windows default output.

Set it with:

```powershell
.\.venv\Scripts\python.exe -c "import json,pathlib; p=pathlib.Path('voice_settings.json'); d=json.loads(p.read_text()); d['audio_device']='Jabra'; p.write_text(json.dumps(d,indent=2)+chr(10))"
```

Then restart the service (or just wait — the speaker re-reads settings when it
restarts).

## Files and logs

| Path | Meaning |
|---|---|
| `state/flanders-service.log` | Service: startup, polling, queued messages |
| `state/speaker.log` | Which engine spoke which line, or why it failed |
| `state/speaker.heartbeat` | Written every second while the speaker is alive |
| `state/speech/*.job` | Pending speech jobs (normally empty) |
| `state/service-boot.log` | Import breadcrumbs, useful if the service will not start |

## Troubleshooting

**Service will not start, error 1053.**
The service is launched by the base interpreter, not the venv stub, so it
reconstructs pywin32's import paths by hand. Check `state/service-boot.log` to
see how far it got. If it stops before `win32con`, the venv's `pywin32.pth`
logic is not being applied.

**Service runs, nothing is spoken.**
Check `state/speaker.log`. If there is no "speaker started" line, the speaker
could not be launched into the session (`WTSQueryUserToken` requires LocalSystem).
If it says "spoke via ...", the audio left the application — check the device.

**Flanders repeats himself.**
Two speakers are draining the queue. Only one is supposed to run; it holds
`state/speaker.lock`.
