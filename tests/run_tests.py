#!/usr/bin/env python3
"""Run every automated check under ``tests/``.

Each check is a standalone script so it can also be run on its own; this runner
just finds them, runs each in a fresh interpreter, and reports a single verdict.
The audible checks in ``tests/manual/`` are deliberately excluded: they play
sound and need the local model or a live key.

Run:
    .\\.venv\\Scripts\\python.exe tests\\run_tests.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> int:
    checks = sorted(HERE.glob("test_*.py"))
    if not checks:
        print("No checks found.")
        return 1

    failures = []
    for path in checks:
        print(f"\n=== {path.name} " + "=" * (60 - len(path.name)))
        result = subprocess.run(  # noqa: S603 - our own interpreter and test files
            [sys.executable, str(path)],
            capture_output=True,
            text=True,
            check=False,
        )
        print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)
        if result.returncode != 0:
            failures.append(path.name)

    print("\n" + "-" * 64)
    if failures:
        print("FAILED: " + ", ".join(failures))
        return 1
    print(f"All {len(checks)} check files passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
