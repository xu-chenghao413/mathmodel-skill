#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Ensure a release tag matches the public version metadata."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def expected_tag() -> str:
    manifest = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    version = manifest.get("version") if isinstance(manifest, dict) else None
    if not isinstance(version, str) or not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("plugin manifest version is not semantic x.y.z")
    return f"v{version}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", default=os.environ.get("GITHUB_REF_NAME"), help="release tag, e.g. v7.4.6")
    args = parser.parse_args(argv)
    if not args.tag:
        parser.error("--tag is required outside GitHub Actions")
    expected = expected_tag()
    if args.tag != expected:
        print(f"[FAIL] release tag {args.tag!r} does not match metadata {expected!r}", file=sys.stderr)
        return 1
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    if f"## {expected[1:]}" not in changelog:
        print(f"[FAIL] CHANGELOG.md has no entry for {expected}", file=sys.stderr)
        return 1
    print(f"[OK] release metadata matches {expected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
