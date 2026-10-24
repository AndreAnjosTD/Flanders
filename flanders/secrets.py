"""Secret storage for Flanders.

A secret is never written to a file. Resolution order:

    1. the environment, for a single session (FISH_API_KEY / FISH_AUDIO_API_KEY)
    2. the Windows Credential Manager, encrypted at rest by DPAPI, per user

Reading Proton Pass is deliberately *not* part of this module. That vault is only
touched by a deliberate, consented action (see scripts/import_key.py), so no
automatic path can reach it.
"""

from __future__ import annotations

import hashlib
import os
import sys

SERVICE = "flanders"
DEFAULT_NAME = "fish_audio"
ENV_NAMES = ("FISH_API_KEY", "FISH_AUDIO_API_KEY")


def fingerprint(value: str) -> str:
    """A one-way reference to a secret, safe to print or log."""
    return "sha256:" + hashlib.sha256(value.encode()).hexdigest()[:12]


def _target(name: str) -> str:
    return f"{SERVICE}:{name}"


def from_environment(name: str = DEFAULT_NAME) -> str | None:
    for env_name in ENV_NAMES:
        value = os.environ.get(env_name, "").strip()
        if value:
            return value
    return None


def from_vault(name: str = DEFAULT_NAME) -> str | None:
    """Read the OS credential store (Windows Credential Manager)."""
    if sys.platform != "win32":
        return None

    try:
        import win32cred
    except ImportError:
        return None

    try:
        credential = win32cred.CredRead(_target(name), win32cred.CRED_TYPE_GENERIC)
    except Exception:  # noqa: BLE001 - absent entry is a normal state
        return None

    blob = credential.get("CredentialBlob")
    if isinstance(blob, bytes):
        blob = blob.decode("utf-16-le")
    text = (blob or "").strip()
    return text or None


def get_secret(name: str = DEFAULT_NAME) -> str | None:
    """Env first, then the OS credential store. Never a file."""
    return from_environment(name) or from_vault(name)


def store_secret(value: str, name: str = DEFAULT_NAME, comment: str = "") -> bool:
    """Encrypt and store a secret in the OS credential store."""
    value = (value or "").strip()
    if not value:
        return False
    if sys.platform != "win32":
        raise RuntimeError("the credential store is only available on Windows")

    import win32cred

    win32cred.CredWrite(
        {
            "Type": win32cred.CRED_TYPE_GENERIC,
            "TargetName": _target(name),
            "UserName": SERVICE,
            "CredentialBlob": value,
            "Persist": win32cred.CRED_PERSIST_LOCAL_MACHINE,
            "Comment": comment or f"Flanders secret: {name}",
        },
        0,
    )
    return True


def delete_secret(name: str = DEFAULT_NAME) -> bool:
    if sys.platform != "win32":
        return False
    try:
        import win32cred

        win32cred.CredDelete(_target(name), win32cred.CRED_TYPE_GENERIC)
        return True
    except Exception:  # noqa: BLE001
        return False


def describe(name: str = DEFAULT_NAME) -> str:
    """A safe, human-readable account of where the secret comes from."""
    if from_environment(name):
        return "environment (this session only)"
    stored = from_vault(name)
    if stored:
        return f"credential store ({fingerprint(stored)})"
    return "absent"
