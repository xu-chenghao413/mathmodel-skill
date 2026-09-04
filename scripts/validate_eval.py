#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Validate a recorded run against a provider-agnostic agent contract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
CASES = ROOT / "evals" / "cases"


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def list_cases() -> list[Path]:
    return sorted(CASES.glob("*.json"))


def load_case(case_id: str) -> dict[str, Any]:
    path = CASES / f"{case_id}.json"
    if not path.is_file():
        raise FileNotFoundError(f"unknown evaluation case: {case_id}")
    payload = _read_json(path)
    if not isinstance(payload, dict) or payload.get("id") != case_id:
        raise ValueError(f"invalid case metadata: {path.name}")
    return payload


def _events(transcript: Any) -> list[dict[str, Any]]:
    if isinstance(transcript, dict):
        transcript = transcript.get("events", transcript.get("transcript", []))
    if not isinstance(transcript, list):
        return []
    return [item for item in transcript if isinstance(item, dict)]


def _event_names(transcript: Any) -> set[str]:
    return {str(item.get("event")) for item in _events(transcript) if item.get("event")}


def _state_value(state: dict[str, Any], key: str) -> Any:
    execution = state.get("execution") if isinstance(state.get("execution"), dict) else {}
    stages = state.get("stages") if isinstance(state.get("stages"), dict) else {}
    if key == "mode":
        return execution.get("interaction_mode") or state.get("mode")
    if key == "submission_ready":
        stage9 = stages.get("9") if isinstance(stages.get("9"), dict) else {}
        return stage9.get("submission_ready") is True
    if key == "blockers":
        blockers = execution.get("blockers", [])
        return blockers if isinstance(blockers, list) else [str(blockers)]
    return state.get(key)


def validate(case: dict[str, Any], state: dict[str, Any], transcript: Any, workspace: Path | None = None) -> list[str]:
    errors: list[str] = []
    if _state_value(state, "competition") != case.get("competition"):
        errors.append(f"competition must be {case.get('competition')!r}")
    if _state_value(state, "mode") != case.get("mode"):
        errors.append(f"interaction mode must be {case.get('mode')!r}")
    blockers = {str(value) for value in _state_value(state, "blockers")}
    missing_blockers = set(case.get("required_blockers", [])) - blockers
    errors.extend(f"missing blocker: {value}" for value in sorted(missing_blockers))
    names = _event_names(transcript)
    missing_events = set(case.get("required_events", [])) - names
    errors.extend(f"missing event: {value}" for value in sorted(missing_events))
    if "submission_ready" in case:
        expected = bool(case["submission_ready"])
        if _state_value(state, "submission_ready") != expected:
            errors.append(f"submission_ready must be {str(expected).lower()}")
    required_artifacts = set(case.get("required_artifacts", []))
    declared = state.get("artifacts", {})
    declared_names = set(declared) if isinstance(declared, dict) else set(declared or []) if isinstance(declared, list) else set()
    for artifact in sorted(required_artifacts - declared_names):
        errors.append(f"missing declared artifact: {artifact}")
    if workspace is not None:
        for artifact in sorted(required_artifacts):
            relative = declared.get(artifact) if isinstance(declared, dict) else artifact
            if not isinstance(relative, str) or not (workspace / relative).exists():
                errors.append(f"artifact not found in workspace: {artifact}")
    transcript_text = json.dumps(transcript, ensure_ascii=False).lower()
    for phrase in case.get("forbidden_claims", []):
        if str(phrase).lower() in transcript_text:
            errors.append(f"forbidden claim found: {phrase}")
    return errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list-cases", action="store_true", help="list available contract cases")
    parser.add_argument("--case", help="case id to validate")
    parser.add_argument("--workspace", type=Path, help="workspace containing decision_log.json and artifacts")
    parser.add_argument("--state", type=Path, help="explicit state JSON (overrides --workspace)")
    parser.add_argument("--transcript", type=Path, help="JSON or JSONL transcript; defaults to the case fixture")
    parser.add_argument("--json", action="store_true", dest="as_json", help="emit a machine-readable report")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.list_cases:
        for path in list_cases():
            print(path.stem)
        return 0
    if not args.case:
        print("--case is required unless --list-cases is used", file=sys.stderr)
        return 2
    try:
        case = load_case(args.case)
        state = case.get("state", {})
        transcript: Any = case.get("transcript", [])
        workspace = args.workspace.expanduser().resolve() if args.workspace else None
        if args.state:
            state = _read_json(args.state.expanduser().resolve())
        elif workspace:
            state_path = args.state or (workspace / "state" / "decision_log.json")
            state = _read_json(state_path)
        if args.transcript:
            transcript_path = args.transcript.expanduser().resolve()
            if transcript_path.suffix.lower() == ".jsonl":
                transcript = [json.loads(line) for line in transcript_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            else:
                transcript = _read_json(transcript_path)
        errors = validate(case, state, transcript, workspace)
    except (OSError, ValueError, json.JSONDecodeError, TypeError) as exc:
        errors = [str(exc)]
    report = {"case": args.case, "passed": not errors, "errors": errors}
    if args.as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif errors:
        print(f"✗ {args.case}")
        for error in errors:
            print(f"  - {error}")
    else:
        print(f"✓ {args.case}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
