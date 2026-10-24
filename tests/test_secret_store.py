#!/usr/bin/env python3
r"""Checks for secret resolution: per-secret environment names, no leakage.

Run:
    .\.venv\Scripts\python.exe tests\test_secret_store.py

Nothing here touches the real credential store or the network.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flanders import secret_store

FISH_KEY = "fish-key-for-tests"
PAT = "pst_test_value"


def check(condition: bool, label: str) -> bool:
    print(f"  {'ok  ' if condition else 'FAIL'} {label}")
    return condition


def without_env() -> dict[str, str]:
    """A clean environment: every secret variable removed."""
    saved = dict(os.environ)
    for names in secret_store.ENV_NAMES.values():
        for name in names:
            os.environ.pop(name, None)
    return saved


def restore(saved: dict[str, str]) -> None:
    os.environ.clear()
    os.environ.update(saved)


def main() -> int:
    passed = True
    saved = without_env()
    try:
        print("the session environment wins when it carries the secret:")
        os.environ["FISH_API_KEY"] = FISH_KEY
        passed &= check(
            secret_store.from_environment("fish_audio") == FISH_KEY,
            "FISH_API_KEY is picked up for fish_audio",
        )

        print("\nthe second variable name works too:")
        del os.environ["FISH_API_KEY"]
        os.environ["FISH_AUDIO_API_KEY"] = FISH_KEY
        passed &= check(
            secret_store.get_secret("fish_audio") == FISH_KEY,
            "FISH_AUDIO_API_KEY is picked up for fish_audio",
        )

        print("\none secret can never be served by another's variable:")
        # This was a real bug: the lookup ignored the secret name, so a Fish key
        # in the environment could be handed back when the vault PAT was asked
        # for, and pass-cli would then reject a perfectly good login.
        passed &= check(
            secret_store.from_environment("proton_pass_pat") is None,
            "a Fish key is not returned as the Proton Pass token",
        )
        os.environ["PROTON_PASS_PERSONAL_ACCESS_TOKEN"] = PAT
        passed &= check(
            secret_store.from_environment("proton_pass_pat") == PAT,
            "PROTON_PASS_PERSONAL_ACCESS_TOKEN is returned for the PAT",
        )
        passed &= check(
            secret_store.from_environment("fish_audio") == FISH_KEY,
            "the Fish key still resolves independently",
        )

        print("\nunknown secrets resolve to nothing, never to something else:")
        passed &= check(
            secret_store.from_environment("no-such-secret") is None,
            "an unknown name returns None",
        )

        print("\nfingerprints identify without revealing:")
        first = secret_store.fingerprint(FISH_KEY)
        second = secret_store.fingerprint(PAT)
        passed &= check(first.startswith("sha256:"), f"{first} carries a prefix")
        passed &= check(len(first) == len("sha256:") + 12, f"{first} is 12 hex characters")
        passed &= check(first != second, "different secrets get different fingerprints")
        passed &= check(FISH_KEY not in first, "the secret is not recoverable from it")
        passed &= check(secret_store.fingerprint(FISH_KEY) == first, "the fingerprint is stable")

        print("\nstatus describes the source without the value:")
        os.environ.pop("PROTON_PASS_PERSONAL_ACCESS_TOKEN", None)
        described = secret_store.describe("fish_audio")
        passed &= check(described.startswith("environment"), f"describe -> {described}")
        passed &= check(FISH_KEY not in described, "describe never prints the value")
    finally:
        restore(saved)

    print("\nALL PASS" if passed else "\nFAILURES")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
