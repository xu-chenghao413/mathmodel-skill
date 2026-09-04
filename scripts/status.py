"""Show a compact, machine-readable snapshot of a mathmodel workspace."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


STAGE_LABELS = {
    0: "kickoff",
    1: "problem_selection",
    2: "analysis",
    3: "model_selection",
    4: "foundation",
    5: "subproblem_loop",
    6: "robustness",
    7: "evaluation",
    8: "writing",
    9: "review",
}


def resolve_state_path(workspace: Path, explicit: Path | None = None) -> Path:
    """Resolve a decision log using the same precedence as workspace tools."""

    if explicit is not None:
        return explicit.expanduser().resolve()
    state_dir = os.environ.get("MATHMODEL_STATE_DIR") or os.environ.get("CUMCM_STATE_DIR")
    if state_dir:
        return Path(state_dir).expanduser().resolve() / "decision_log.json"
    return workspace.expanduser().resolve() / "state" / "decision_log.json"


def _stage_number(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 9:
        return None
    return value


def snapshot(state: dict[str, Any], state_path: Path) -> dict[str, Any]:
    """Build the stable public status shape consumed by humans and automation."""

    execution = state.get("execution") if isinstance(state.get("execution"), dict) else {}
    stages = state.get("stages") if isinstance(state.get("stages"), dict) else {}
    current_stage = _stage_number(state.get("current_stage"))
    stage_data = stages.get(str(current_stage), {}) if current_stage is not None else {}
    if not isinstance(stage_data, dict):
        stage_data = {}
    blockers = execution.get("blockers", [])
    if not isinstance(blockers, list):
        blockers = [str(blockers)]
    blockers = [str(item) for item in blockers if str(item).strip()]
    stage9 = stages.get("9", {})
    if not isinstance(stage9, dict):
        stage9 = {}
    submission_ready = stage9.get("submission_ready") is True
    status = "ready" if submission_ready else "blocked" if blockers else "in_progress"
    mode = execution.get("interaction_mode") or state.get("mode")
    return {
        "status": status,
        "competition": state.get("competition"),
        "mode": mode,
        "current_stage": current_stage,
        "current_stage_label": stage_data.get("_label") or (STAGE_LABELS.get(current_stage) if current_stage is not None else None),
        "blockers": blockers,
        "submission_ready": submission_ready,
        "state_path": str(state_path),
    }


def load_snapshot(state_path: Path) -> dict[str, Any]:
    """Read and validate the decision log before building a snapshot."""

    if not state_path.exists():
        return {
            "status": "missing",
            "blockers": ["state_file_missing"],
            "submission_ready": False,
            "state_path": str(state_path),
        }
    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "status": "invalid",
            "blockers": ["state_file_invalid"],
            "error": str(exc),
            "submission_ready": False,
            "state_path": str(state_path),
        }
    if not isinstance(payload, dict):
        return {
            "status": "invalid",
            "blockers": ["state_root_not_object"],
            "submission_ready": False,
            "state_path": str(state_path),
        }
    return snapshot(payload, state_path)


def _print_human(data: dict[str, Any]) -> None:
    print("mathmodel-skill status")
    print(f"  status: {data.get('status', 'unknown')}")
    print(f"  competition: {data.get('competition') or 'unknown'}")
    print(f"  mode: {data.get('mode') or 'unknown'}")
    stage = data.get("current_stage")
    label = data.get("current_stage_label")
    print(f"  stage: {stage}/9 ({label or 'unknown'})" if stage is not None else "  stage: unknown")
    print(f"  submission_ready: {str(bool(data.get('submission_ready'))).lower()}")
    blockers = data.get("blockers") or []
    if blockers:
        print("  blockers:")
        for blocker in blockers:
            print(f"    - {blocker}")
    print(f"  state: {data.get('state_path')}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=Path.cwd(), help="Contest workspace (default: current directory)")
    parser.add_argument("--state", type=Path, default=None, help="Explicit decision_log.json path")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Print a JSON snapshot")
    parser.add_argument("--require-ready", action="store_true", help="Return non-zero until submission_ready is true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    state_path = resolve_state_path(args.workspace, args.state)
    data = load_snapshot(state_path)
    if args.as_json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        _print_human(data)
    if data["status"] in {"missing", "invalid"}:
        return 2
    if args.require_ready and not data.get("submission_ready"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
