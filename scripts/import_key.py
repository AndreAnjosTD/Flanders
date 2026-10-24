#!/usr/bin/env python3
r"""Import the Fish Audio key into the encrypted local store.

The Proton Pass vault is only ever read by this script, run deliberately. No
other path in Flanders can reach it.

Run from the project root:

    .\.venv\Scripts\python.exe scripts\import_key.py --status
    .\.venv\Scripts\python.exe scripts\import_key.py --from-vault
    .\.venv\Scripts\python.exe scripts\import_key.py --session
    .\.venv\Scripts\python.exe scripts\import_key.py --store-token
    .\.venv\Scripts\python.exe scripts\import_key.py --forget

--from-vault reads ``NodeHug / Audio Fish / API Key`` with pass-cli and stores
it in the Windows Credential Manager (DPAPI, per user). Nothing is written to a
file, and only a SHA-256 fingerprint is printed.

When the Proton session expires, --from-vault re-authenticates automatically with
the bootstrap token from the credential store. If that token itself is revoked,
--store-token replaces it. --session reports the vault state on its own.
"""

from __future__ import annotations

import argparse
import getpass
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from flanders import secret_store  # noqa: E402

VAULT_NAME = "NodeHug"
ITEM_TITLE = "Audio Fish"
FIELD = "API Key"
REASON = "Import the Fish Audio API key into the encrypted local store for Flanders"


def pass_cli() -> Path:
    local = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "ProtonPass" / "pass-cli.exe"
    return local if local.exists() else Path("pass-cli")


def session_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PROTON_PASS_SESSION_DIR"] = str(Path(os.environ.get("TEMP", "")) / "pass-agent-flanders")
    env["PROTON_PASS_AGENT_REASON"] = REASON
    return env


def run(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([str(pass_cli()), *args], capture_output=True, text=True, env=env)


def ensure_session() -> bool:
    if run("info", env=session_env()).returncode == 0:
        return True

    print("session expired; re-authenticating with the stored bootstrap token")
    run("logout", "--force", env=session_env())
    bootstrap = secret_store.get_secret("proton_pass_pat")
    if not bootstrap:
        print("no bootstrap token stored; run: scripts\\import_key.py --store-token")
        return False

    env = session_env()
    env["PROTON_PASS_PERSONAL_ACCESS_TOKEN"] = bootstrap
    login = run("login", env=env)
    if login.returncode != 0:
        # A session can already be live even when login refuses; treat that as
        # success and confirm it with the real health check below.
        combined = (login.stdout + login.stderr).lower()
        if "already authenticated" not in combined:
            print("login failed:", login.stderr.strip()[:200])
            print("if the token was revoked or expired, run: scripts\\import_key.py --store-token")
            return False

    return run("info", env=session_env()).returncode == 0


def store_token() -> int:
    """Replace the bootstrap token when the old one is revoked or expired."""
    token = getpass.getpass("Proton Pass personal access token (input hidden): ").strip()
    if not token:
        print("no token entered")
        return 1
    if not secret_store.store_secret(
        token, "proton_pass_pat", "Proton Pass bootstrap PAT for Flanders"
    ):
        print("could not store the token")
        return 1
    print(f"stored bootstrap token: {secret_store.fingerprint(token)}")
    return 0


def session_status() -> int:
    if ensure_session():
        print("vault session: active")
        return 0
    print("vault session: unavailable")
    return 1


def notify_renewal(reason: str) -> None:
    """Ask Flanders to say the renewal notice out loud.

    Never let the notice break the script: if speech is unavailable, the printed
    line still carries the same instruction.
    """
    line = (
        "Okily dokily, captain! Proton vault access needs renewing. "
        "When you are ready, run the import key script with the store token option."
    )
    print(f"renewal needed ({reason})")
    print("  run: .\\.venv\\Scripts\\python.exe scripts\\import_key.py --store-token")
    try:
        subprocess.run(
            [sys.executable, str(ROOT / "flanders" / "flanders_say.py"), line],
            capture_output=True,
            text=True,
            timeout=180,
        )
    except Exception:  # noqa: BLE001 - the notice must never be fatal
        pass


def import_from_vault() -> int:
    if not ensure_session():
        notify_renewal("vault session could not be established")
        return 1

    result = run(
        "item", "view",
        "--vault-name", VAULT_NAME,
        "--item-title", ITEM_TITLE,
        "--field", FIELD,
        env=session_env(),
    )
    if result.returncode != 0:
        detail = result.stderr.strip()[:200] or "the vault refused the read"
        print("vault read failed:", detail)
        notify_renewal(detail)
        return 1

    key = result.stdout.strip()
    if not key:
        print("the vault returned an empty value")
        return 1

    if not secret_store.store_secret(key, "fish_audio", "Fish Audio API key for Flanders"):
        print("could not store the key")
        return 1

    print(f"stored in the credential store: {secret_store.fingerprint(key)}")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Manage the Fish Audio key.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--status", action="store_true", help="say where the key comes from")
    group.add_argument("--from-vault", action="store_true", help="read the vault once and store the key")
    group.add_argument("--forget", action="store_true", help="delete the stored key")
    group.add_argument("--session", action="store_true", help="report the vault session, re-authenticating if needed")
    group.add_argument("--store-token", action="store_true", help="replace the bootstrap token (hidden prompt)")
    args = parser.parse_args(argv)

    if args.status:
        print(f"source: {secret_store.describe('fish_audio')}")
        return 0

    if args.forget:
        print("removed" if secret_store.delete_secret("fish_audio") else "nothing to remove")
        return 0

    if args.session:
        return session_status()

    if args.store_token:
        return store_token()

    return import_from_vault()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
