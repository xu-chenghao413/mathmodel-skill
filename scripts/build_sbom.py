#!/usr/bin/env python3
"""Create a deterministic CycloneDX-style SBOM for a source checkout."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from scripts.console import configure_stdio
except ImportError:
    from console import configure_stdio


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build(source: Path, output: Path, name: str, version: str) -> Path:
    source = source.expanduser().resolve()
    output = output.expanduser().resolve()
    if not source.is_dir():
        raise ValueError(f"source is not a directory: {source}")
    if output == source:
        raise ValueError("output must be a file outside the source root")
    components: list[dict[str, object]] = []
    for path in sorted(source.rglob("*")):
        if not path.is_file() or ".git" in path.parts or "__pycache__" in path.parts or "dist" in path.parts:
            continue
        if path.resolve() == output:
            continue
        relative = path.relative_to(source).as_posix()
        components.append(
            {
                "type": "file",
                "name": relative,
                "hashes": [{"alg": "SHA-256", "content": _sha256(path)}],
            }
        )
    payload = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": f"urn:uuid:{hashlib.sha256((name + version).encode()).hexdigest()[:32]}",
        "version": 1,
        "metadata": {
            "timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "component": {"type": "application", "name": name, "version": version},
        },
        "components": components,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a deterministic source SBOM")
    parser.add_argument("--source", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--name", default="mathmodel-skill")
    parser.add_argument("--version", default="working-tree")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        output = build(args.source, args.output, args.name, args.version)
    except (OSError, ValueError) as exc:
        print(f"sbom failed: {exc}", file=sys.stderr)
        return 2
    print(f"SBOM written: {output}")
    return 0


if __name__ == "__main__":
    configure_stdio()
    raise SystemExit(main())
