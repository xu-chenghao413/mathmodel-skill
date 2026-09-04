#!/usr/bin/env python3
"""Cross-platform smoke test for the portable installer.

This intentionally uses only the standard library so GitHub Actions can run it
on Linux, macOS, and Windows before optional modeling dependencies are installed.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from install_skill import install_payload


ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="mathmodel-install-smoke-") as temp:
        destination = Path(temp) / "installed"
        created = install_payload(ROOT, destination)
        required = ("SKILL.md", "references", "competitions", "templates", "scripts")
        missing = [name for name in required if not (destination / name).exists()]
        forbidden = [name for name in (".git", ".github", "tests", "state") if (destination / name).exists()]
        if missing or forbidden or len(created) < 20:
            print(f"smoke failed: missing={missing}, forbidden={forbidden}, copied={len(created)}", file=sys.stderr)
            return 1

        result = subprocess.run(
            [
                sys.executable,
                str(destination / "scripts" / "doctor.py"),
                "--competition",
                "cumcm",
                "--skip-tools",
            ],
            cwd=destination,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if result.returncode != 0:
            print(result.stdout, end="")
            print(result.stderr, end="", file=sys.stderr)
            return result.returncode or 1

    print("portable install smoke: pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
