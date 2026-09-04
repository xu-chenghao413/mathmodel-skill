#!/usr/bin/env python3
"""Validate the public repository's structure, metadata, and CLI entrypoints."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import re
from pathlib import Path

try:
    from scripts.console import configure_stdio
except ImportError:
    from console import configure_stdio


ROOT = Path(__file__).resolve().parent.parent
REQUIRED_PATHS = (
    "SKILL.md",
    "AGENTS.md",
    "README.md",
    "LICENSE",
    "PROVENANCE.md",
    "THIRD_PARTY_NOTICES.md",
    ".codex-plugin/plugin.json",
    "agents/openai.yaml",
    "skills/mathmodel-skill/SKILL.md",
    "scripts/install_skill.py",
    "scripts/doctor.py",
    "scripts/status.py",
    "scripts/console.py",
    "scripts/build_sbom.py",
    "scripts/validate_eval.py",
    "scripts/verify_release.py",
    "evals/README.md",
    "evals/cases/cumcm_autopilot_blocked.json",
    "evals/cases/mcm_guided_confirmation.json",
    "evals/cases/diangong_delivery_gate.json",
    "pyproject.toml",
    "uv.lock",
    "competitions/cumcm/empirical_manifest.json",
    "docs/README.md",
    "GOVERNANCE.md",
    "SUPPORT.md",
    "examples/quickstart/run_demo.py",
    ".github/workflows/ci.yml",
    ".github/workflows/release.yml",
    ".github/workflows/security.yml",
)
CLI_ENTRYPOINTS = (
    "scripts/doctor.py",
    "scripts/status.py",
    "scripts/install_skill.py",
    "scripts/score_artifact.py",
    "scripts/render_paper.py",
    "scripts/validate_delivery.py",
    "scripts/validate_eval.py",
    "scripts/verify_release.py",
    "examples/quickstart/run_demo.py",
)


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _check_json_files(errors: list[str]) -> int:
    count = 0
    for path in sorted(ROOT.rglob("*.json")):
        if any(part in {".git", "__pycache__"} for part in path.parts):
            continue
        try:
            _load_json(path)
            count += 1
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"invalid JSON: {path.relative_to(ROOT)} ({exc})")
    return count


def _check_yaml_files(errors: list[str], require_yaml: bool) -> int:
    try:
        import yaml  # type: ignore
    except ImportError:
        if require_yaml:
            errors.append("PyYAML is required for workflow validation")
        return 0
    count = 0
    yaml_paths = [*ROOT.rglob("*.yml"), *ROOT.rglob("*.yaml")]
    for path in sorted(set(yaml_paths)):
        if any(part in {".git", "__pycache__"} for part in path.parts):
            continue
        try:
            yaml.safe_load(path.read_text(encoding="utf-8"))
            count += 1
        except (OSError, yaml.YAMLError) as exc:
            errors.append(f"invalid YAML: {path.relative_to(ROOT)} ({exc})")
    return count


def _check_metadata(errors: list[str]) -> None:
    plugin = _load_json(ROOT / ".codex-plugin" / "plugin.json")
    if not isinstance(plugin, dict) or not isinstance(plugin.get("version"), str):
        errors.append("plugin manifest is missing a string version")
        return
    version = plugin["version"]
    expected = f"v{version}"
    for relative in ("README.md", "README.en.md", "SKILL.md", "AGENTS.md"):
        text = (ROOT / relative).read_text(encoding="utf-8")
        if expected not in text:
            errors.append(f"{relative} does not mention current version {expected}")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    if f"## {version}" not in changelog:
        errors.append(f"CHANGELOG.md has no entry for {version}")
    if plugin.get("name") != "mathmodel-skill":
        errors.append("plugin name must remain mathmodel-skill")
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    if f'version = "{version}"' not in pyproject:
        errors.append("pyproject.toml does not match plugin version")


def _check_action_pins(errors: list[str]) -> None:
    action_pattern = re.compile(r"^\s*uses:\s*([^@\s]+)@([^\s#]+)", re.MULTILINE)
    for path in sorted((ROOT / ".github" / "workflows").glob("*.y*ml")):
        text = path.read_text(encoding="utf-8")
        for action, ref in action_pattern.findall(text):
            if not re.fullmatch(r"[0-9a-f]{40}", ref):
                errors.append(f"workflow action is not pinned to a commit SHA: {path.relative_to(ROOT)} ({action}@{ref})")


def _check_cli() -> list[str]:
    failures: list[str] = []
    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    for relative in CLI_ENTRYPOINTS:
        result = subprocess.run(
            [sys.executable, str(ROOT / relative), "--help"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if result.returncode != 0:
            failures.append(f"{relative} --help exited {result.returncode}: {result.stderr[-300:]}")
    return failures


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate mathmodel-skill repository structure and CLIs")
    parser.add_argument("--check-cli", action="store_true", help="run --help for supported CLI entrypoints")
    parser.add_argument("--require-yaml", action="store_true", help="fail if PyYAML is unavailable")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    errors: list[str] = []
    missing = [relative for relative in REQUIRED_PATHS if not (ROOT / relative).is_file()]
    errors.extend(f"missing required path: {relative}" for relative in missing)
    try:
        _check_metadata(errors)
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        errors.append(f"metadata check failed: {exc}")
    json_count = _check_json_files(errors)
    yaml_count = _check_yaml_files(errors, args.require_yaml)
    _check_action_pins(errors)
    if args.check_cli:
        errors.extend(_check_cli())
    if errors:
        for error in errors:
            print(f"✗ {error}", file=sys.stderr)
        return 1
    print(f"✓ project verification passed (JSON: {json_count}, YAML: {yaml_count}, CLI: {args.check_cli})")
    return 0


if __name__ == "__main__":
    configure_stdio()
    raise SystemExit(main())
