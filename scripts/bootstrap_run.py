#!/usr/bin/env python3
"""Initialize or resume a mathmodel autopilot workspace without overwriting work."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


COMPETITIONS = ("cumcm", "mcm", "diangong")
NATURE_SKILLS = (
    "nature-academic-search",
    "nature-citation",
    "nature-data",
    "nature-downloader",
    "nature-experiment-log",
    "nature-figure",
    "nature-image2ppt",
    "nature-literature-pipeline",
    "nature-paper-card",
    "nature-paper-to-patent",
    "nature-paper2ppt",
    "nature-polishing",
    "nature-reader",
    "nature-ref-verifier",
    "nature-response",
    "nature-reviewer",
    "nature-statistics",
    "nature-writing",
)
BOOTSTRAP_BLOCKER_PREFIXES = (
    "missing_problem:",
    "missing_attachment:",
    "not_a_file_problem:",
    "not_a_file_attachment:",
    "unreadable_problem:",
    "unreadable_attachment:",
    "competition_template_unresolved",
    "problem_source_missing",
)
WORKSPACE_DIRS = (
    "input",
    "data_raw",
    "data_processed",
    "analysis",
    "src",
    "results",
    "figures",
    "paper_workspace",
    "paper_output",
    "support_materials",
    "qa",
    "state",
    "delivery",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def readable_hint(path: Path) -> str:
    text = path.name
    if path.suffix.lower() in {".txt", ".md", ".tex", ".csv", ".json"} and path.exists():
        try:
            text += "\n" + path.read_text(encoding="utf-8", errors="ignore")[:200_000]
        except OSError:
            pass
    return text.lower()


def infer_competition(paths: list[Path]) -> tuple[str | None, float, dict[str, int]]:
    scores = {key: 0 for key in COMPETITIONS}
    patterns = {
        "cumcm": (r"cumcm", r"全国大学生数学建模", r"国赛"),
        "mcm": (r"\bmcm\b", r"\bicm\b", r"comap", r"mathematical contest in modeling"),
        "diangong": (r"diangong", r"电工杯", r"中国电机工程学会杯"),
    }
    for path in paths:
        haystack = readable_hint(path)
        for competition, regexes in patterns.items():
            scores[competition] += sum(bool(re.search(pattern, haystack, re.IGNORECASE)) for pattern in regexes)
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    if ranked[0][1] == 0 or (len(ranked) > 1 and ranked[0][1] == ranked[1][1]):
        return None, 0.0, scores
    confidence = min(0.98, 0.60 + 0.10 * ranked[0][1])
    return ranked[0][0], confidence, scores


def source_record(path_text: str, kind: str, workspace: Path) -> tuple[dict[str, Any], str | None]:
    raw = Path(path_text).expanduser()
    path = raw if raw.is_absolute() else workspace / raw
    path = path.resolve()
    record: dict[str, Any] = {"kind": kind, "path": str(path), "exists": path.exists()}
    if not path.exists():
        return record, f"missing_{kind}:{path}"
    if not path.is_file():
        return record, f"not_a_file_{kind}:{path}"
    try:
        record.update({"bytes": path.stat().st_size, "sha256": file_hash(path)})
    except OSError as exc:
        return record, f"unreadable_{kind}:{path}:{exc}"
    return record, None


def ensure_execution_schema(state: dict[str, Any]) -> dict[str, Any]:
    execution = state.setdefault("execution", {})
    execution.setdefault("interaction_mode", "guided")
    execution.setdefault("status", "initialized")
    execution.setdefault("plot_backend", "python")
    execution.setdefault("source_packet", {})
    nature_router = execution.setdefault("nature_router", {})
    for key in ("available", "used", "skipped", "degraded"):
        nature_router.setdefault(key, [])
    execution.setdefault("checkpoints", [])
    execution.setdefault("blockers", [])
    state.setdefault("evidence", {"claims": [], "references": {}, "data_provenance": [], "terminology_ledger": []})
    state.setdefault("artifacts", {"required": [], "produced": [], "validation_report": None})
    state.setdefault("qa", {})
    return execution


def ensure_cumcm_compliance(state: dict[str, Any], workspace: Path) -> None:
    compliance = state.setdefault("compliance", {}).setdefault("cumcm", {})
    compliance.setdefault("ruleset", "cumcm_2026")
    compliance.setdefault(
        "source_priority",
        ["current_year_official_notice", "cumcm_2026_baseline", "historical_2025_workflow_example"],
    )
    ai = compliance.setdefault("ai", {})
    ai.setdefault("used", True)
    ai.setdefault("team_led_core_modeling_confirmed", False)
    ai.setdefault("human_ai_review_confirmed", False)
    ai.setdefault("usage_log", "qa/ai_usage_log.json")
    ai.setdefault("details_pdf", "qa/AI 工具使用详情.pdf")
    compliance.setdefault("anonymity_confirmed", False)
    paper = compliance.setdefault("paper", {})
    paper.setdefault("electronic_first_page_abstract", False)
    paper.setdefault("pdf_total_pages", None)
    paper.setdefault("abstract_pages", None)
    paper.setdefault("official_body_start_pdf_page", None)
    paper.setdefault("official_body_end_pdf_page", None)
    paper.setdefault("official_body_pages", None)
    paper.setdefault("appendix_start_pdf_page", None)
    paper.setdefault("appendix_pages", None)
    paper.setdefault("page_structure_audit", "qa/page_structure_audit.json")
    paper.setdefault("page_structure_audited", False)
    paper.setdefault("a4_margin_and_pagination_audited", False)
    paper.setdefault("appendix_included", False)
    paper.setdefault("support_file_list_in_appendix", False)
    compliance.setdefault("package", {"path": None, "submission_ready": False})

    usage_log = workspace / "qa" / "ai_usage_log.json"
    if not usage_log.exists():
        atomic_json_write(
            usage_log,
            {
                "schema_version": "1.1",
                "ruleset": "cumcm_2026",
                "recording_scope": "key_material_interactions",
                "recording_mode": "summary-only",
                "tools": [],
                "uses": [],
                "key_interactions": [],
                "team_led_core_modeling_confirmed": False,
                "human_ai_review_confirmed": False,
            },
        )


def discover_nature_skills() -> list[dict[str, str]]:
    roots = (
        Path.home() / ".agents" / "skills",
        Path.home() / ".codex" / "skills",
        Path.home() / ".claude" / "skills",
    )
    found: list[dict[str, str]] = []
    seen: set[str] = set()
    for name in NATURE_SKILLS:
        for root in roots:
            skill_file = root / name / "SKILL.md"
            if skill_file.exists() and name not in seen:
                found.append({"name": name, "path": str(skill_file.resolve())})
                seen.add(name)
                break
    return found


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True, help="User contest workspace")
    parser.add_argument("--mode", choices=("autopilot", "guided"), default="autopilot")
    parser.add_argument("--competition", choices=("auto",) + COMPETITIONS, default="auto")
    parser.add_argument("--problem", action="append", default=[], help="Problem file; repeatable")
    parser.add_argument("--attachment", action="append", default=[], help="Required attachment; repeatable")
    parser.add_argument("--plot-backend", choices=("python", "r"), default="python")
    parser.add_argument("--resume", action="store_true", help="Resume an existing state without replacing it")
    return parser.parse_args()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    workspace = Path(args.workspace).expanduser().resolve()
    skill_root = Path(__file__).resolve().parents[1]
    template_path = skill_root / "templates" / "shared" / "decision_log.json"
    state_path = workspace / "state" / "decision_log.json"

    workspace.mkdir(parents=True, exist_ok=True)
    for name in WORKSPACE_DIRS:
        (workspace / name).mkdir(parents=True, exist_ok=True)

    if state_path.exists() and not args.resume:
        print(json.dumps({"status": "state_exists", "path": str(state_path), "hint": "use --resume"}, ensure_ascii=False))
        return 2

    if state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8"))
    else:
        if not template_path.exists():
            print(json.dumps({"status": "template_missing", "path": str(template_path)}, ensure_ascii=False))
            return 2
        state = json.loads(template_path.read_text(encoding="utf-8"))

    execution = ensure_execution_schema(state)
    execution["interaction_mode"] = args.mode
    execution["plot_backend"] = args.plot_backend
    execution.setdefault("started_at", utc_now())
    state.setdefault("started_at", execution["started_at"])
    execution["last_bootstrap_at"] = utc_now()
    execution.setdefault("nature_router", {})["available"] = discover_nature_skills()

    records: list[dict[str, Any]] = []
    blockers: list[str] = []
    for value in args.problem:
        record, blocker = source_record(value, "problem", workspace)
        records.append(record)
        if blocker:
            blockers.append(blocker)
    for value in args.attachment:
        record, blocker = source_record(value, "attachment", workspace)
        records.append(record)
        if blocker:
            blockers.append(blocker)

    existing_packet = execution.setdefault("source_packet", {})
    by_path = {item.get("path"): item for item in existing_packet.get("files", []) if item.get("path")}
    by_path.update({item.get("path"): item for item in records if item.get("path")})
    existing_packet["files"] = list(by_path.values())
    existing_packet["created_or_updated_at"] = utc_now()

    valid_paths = [Path(item["path"]) for item in existing_packet["files"] if item.get("exists")]
    if args.competition == "auto":
        inferred, confidence, scores = infer_competition(valid_paths)
        existing_packet["competition_inference"] = {
            "value": inferred,
            "confidence": confidence,
            "signals": scores,
            "template_locked": inferred is not None,
        }
        if inferred:
            state["competition"] = inferred
        elif args.mode == "autopilot":
            blockers.append("competition_template_unresolved")
    else:
        state["competition"] = args.competition
        existing_packet["competition_inference"] = {
            "value": args.competition,
            "confidence": 1.0,
            "signals": {args.competition: 1},
            "template_locked": True,
        }

    if args.mode == "autopilot" and not any(item.get("kind") == "problem" and item.get("exists") for item in existing_packet["files"]):
        blockers.append("problem_source_missing")

    if state.get("competition") == "cumcm":
        ensure_cumcm_compliance(state, workspace)

    persistent_blockers = [
        item
        for item in execution.get("blockers", [])
        if not item.startswith(BOOTSTRAP_BLOCKER_PREFIXES)
    ]
    execution["blockers"] = sorted(set(persistent_blockers + blockers))
    execution["status"] = "blocked" if execution["blockers"] else "initialized"
    state["_schema_version"] = "4.1"
    atomic_json_write(state_path, state)

    print(
        json.dumps(
            {
                "status": execution["status"],
                "workspace": str(workspace),
                "state": str(state_path),
                "competition": state.get("competition"),
                "source_files": len(existing_packet["files"]),
                "blockers": execution["blockers"],
            },
            ensure_ascii=False,
        )
    )
    return 1 if execution["blockers"] else 0


if __name__ == "__main__":
    sys.exit(main())
