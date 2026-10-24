#!/usr/bin/env python3
r"""Import the Fish Audio key into the encrypted local store.

The Proton Pass vault is only ever read by this script, run deliberately. No
other path in Flanders can reach it.

Run from the project root:

    .\.venv\Scripts\python.exe scripts\import_key.py --status
    .\.venv\Scripts\python.exe scripts\import_key.py --from-vault
    .\.venv\Scripts\python.exe scripts\import_key.py --forget

--from-vault reads ``NodeHug / Audio Fish / API Key`` with pass-cli and stores
it in the Windows Credential Manager (DPAPI, per user). Nothing is written to a
file, and only a SHA-256 fingerprint is printed.
"""

from __future__ import annotations

import argparse
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
        print("no bootstrap token in the credential store; run the login by hand")
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
            return False

    return run("info", env=session_env()).returncode == 0


def import_from_vault() -> int:
    if not ensure_session():
        return 1

    result = run(
        "item", "view",
        "--vault-name", VAULT_NAME,
        "--item-title", ITEM_TITLE,
        "--field", FIELD,
        env=session_env(),
    )
    if result.returncode != 0:
        print("vault read failed:", result.stderr.strip()[:200])
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
    args = parser.parse_args(argv)

    if args.status:
        print(f"source: {secret_store.describe('fish_audio')}")
        return 0

    if args.forget:
        print("removed" if secret_store.delete_secret("fish_audio") else "nothing to remove")
        return 0

    return import_from_vault()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
