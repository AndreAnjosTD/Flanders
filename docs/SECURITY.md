# Security and privacy

A short, honest account of what this project holds, where it holds it, and what
it refuses to do. Everything here is enforced by code, not by convention, unless
the section says otherwise.

## The assets

| Asset | Where it lives | Protection |
|---|---|---|
| Fish Audio API key | Windows Credential Manager (`flanders:fish_audio`), or `FISH_API_KEY` for one session | DPAPI, per user, at rest |
| Proton Pass bootstrap token | Windows Credential Manager (`flanders:proton_pass_pat`) | DPAPI, per user, at rest |
| Slack bot token | `config/slack.env` in the firstmate home | file permissions of that home; read into memory only |
| Spoken text | memory, plus a short excerpt in `state/*.log` | local to the machine |

No credential is ever written to a file by this project. `git` history was
scanned for token patterns when this document was written and contains none.

## How secrets are reached

`flanders/secret_store.py` is the only module that reads a stored secret. Its
resolution order is the environment first, then the credential store, and each
secret has its own environment variable names, so asking for one secret can
never quietly return another.

Only a fingerprint is ever printed:

```
sha256:1a1f80ff5762
```

That is identification, not authentication. Twelve hex characters of a SHA-256
digest tell two keys apart and are useless for recovering a 51-character random
key.

## The vault boundary

The Proton Pass vault is not part of the running application. Exactly one script
touches it, and only when a person runs it:

```powershell
.\.venv\Scripts\python.exe scripts\import_key.py --from-vault
```

The rules that hold:

- **Consent is per request, never standing.** No code path reads the vault on a
  timer, at startup, or as a fallback.
- **`pass-cli` runs with an isolated session directory** (`%TEMP%\pass-agent-flanders`)
  so it cannot disturb any other Proton session on the machine.
- **Every vault command carries a reason** via `PROTON_PASS_AGENT_REASON`, as the
  CLI requires.
- **The token is passed as a child-process environment variable** and is never
  written to disk, echoed, or logged.
- **A failure is loud.** If the session cannot be established, the exact recovery
  command is printed and Flanders says out loud that vault access needs renewing.
- **Vault expiry cannot silence the voice.** The Fish Audio key stays cached, so
  speech keeps working while the Proton session is dormant.

## What leaves the machine

| Destination | What is sent | When |
|---|---|---|
| `api.fish.audio` | the text being spoken | only when the hosted voice is used |
| `slack.com` | bot token, and the messages you post | when the bridge reads or posts |
| `modelscope.cn` | nothing (a download) | only during `setup_local.ps1` |

The hosted voice is a third party, so anything that must not leave the machine
has to be spoken with `--engine local` or `engine: offline` in
`voice_settings.json`.

## Defensive choices in the code

- **HTTPS only.** Every URL opener checks the scheme first; anything else is
  refused rather than attempted. This is why the security linter's URL warnings
  are annotated rather than suppressed globally.
- **Absolute paths for Windows tools.** The service resolves `sc.exe` and
  `schtasks.exe` under `%SYSTEMROOT%\System32`. An elevated process should never
  let a planted executable win a `PATH` lookup.
- **No shell.** Subprocesses are always a fixed executable plus an argument list;
  there is no `shell=True`, no string interpolation into a command line, and no
  `eval`/`exec` anywhere in the project.
- **Bounded responses.** A TTS response is capped at 32 MB and a spoken line at
  2000 characters, so a hostile or broken endpoint cannot exhaust memory.
- **Failing safely, not silently.** A missing key, a rejected key, or an
  unreachable service falls through to the next voice; each failure says what
  went wrong.

## Process model

The Windows service runs as `LocalSystem` because only a privileged process can
hand a token to a process in the logged-on session. It does not speak, and it
never touches audio:

```
LocalSystem service   ->  reads Slack, writes speech jobs
user-token speaker    ->  reads jobs, reads the user's credential store, speaks
```

Secrets therefore stay in the user's DPAPI scope, not the system account's. The
service's only privileges are the ones needed to start that companion process.

## Local state

`state/` holds the speech queue, heartbeats, and logs. It is git-ignored and
lives under the checkout, so it is readable by the account that runs Flanders and
by an administrator. Logs record what was spoken, truncated to about ninety
characters, and the engine that spoke it; they never record a key.

## Rotating a credential

```powershell
# Replace the Fish Audio key (prompts hidden, or read the vault with consent)
.\.venv\Scripts\python.exe scripts\import_key.py --store-token
.\.venv\Scripts\python.exe scripts\import_key.py --from-vault

# Remove the cached key entirely
.\.venv\Scripts\python.exe scripts\import_key.py --forget
```

Replacing the Slack token means editing `config/slack.env` and restarting the
service. A token that has ever been pasted into a chat window should be treated
as burnt and rotated.

## Known limits

These are real, and naming them is cheaper than pretending otherwise:

- **The fingerprint is not authentication.** It identifies a key; it cannot prove
  one is genuine.
- **The vault is checked only when an import runs.** A quietly expired token is
  noticed at the next deliberate import, not before.
- **The hosted voice is a third party.** Text leaves the machine when it is used.
- **The service runs as `LocalSystem`.** That is what the session hand-off needs,
  so the checkout it runs from should not be writable by other users.
- **Model weights are downloaded without a pinned hash** during `setup_local.ps1`,
  because ModelScope publishes no stable digest for them.
- **Message excerpts are logged.** Anything posted in the watched channel may
  appear, truncated, in `state/`.
