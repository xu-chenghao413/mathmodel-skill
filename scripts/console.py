"""Small, dependency-free console portability helpers for CLI scripts."""

from __future__ import annotations

import sys


def configure_stdio() -> None:
    """Prefer UTF-8 output while remaining safe on non-standard streams."""

    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            # Embedded runners may expose read-only streams.
            continue
