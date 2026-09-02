#!/usr/bin/env python3
"""Build an adaptive CUMCM paper page budget from question-level evidence load.

The planner keeps the one-page abstract, the official body, and the appendix in
three separate accounting buckets.  Its output is intended to be written to
``analysis/page_budget.json`` and reviewed again after the paper is rendered.
It is a planning heuristic, not an official page-count interpretation.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Sequence


PROFILE_TARGETS = {"compact": 26, "balanced": 27, "dense": 28}  # 2026-08-20 起正文 26-28 页为硬性区间（用户决策），替换原 30 页上限口径
OFFICIAL_BODY_HARD_CAP = 28  # 硬性上限
OFFICIAL_BODY_HARD_FLOOR = 26  # 硬性下限
ABSTRACT_PAGES = 1
SCORE_FIELDS = (
    "importance",
    "scenario_load",
    "derivation_depth",
    "novelty_evidence",
    "validation_load",
    "downstream_reuse",
)
FIELD_WEIGHTS = {
    "importance": 0.30,
    "scenario_load": 0.12,
    "derivation_depth": 0.20,
    "novelty_evidence": 0.18,
    "validation_load": 0.14,
    "downstream_reuse": 0.06,
}
DEFAULT_APPENDIX_ITEMS = (
    "完整可运行的源代码与必要注释",
    "输入输出及支撑材料文件清单",
    "复现实验的环境、依赖、随机种子与运行命令",
    "正文无法容纳但结论依赖的补充表格、诊断图或推导",
)


class BudgetError(ValueError):
    """Raised when a requested budget cannot satisfy the planner contract."""


def _require_number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise BudgetError(f"{field} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise BudgetError(f"{field} must be finite")
    return number


def _score(value: Any, field: str) -> float:
    number = _require_number(value, field)
    if not 0 <= number <= 5:
        raise BudgetError(f"{field} must be between 0 and 5")
    return number


def _discount(value: Any, field: str) -> float:
    number = _require_number(value, field)
    if not 0 <= number <= 1:
        raise BudgetError(f"{field} must be between 0 and 1")
    return number


def _resolve_target(payload: dict[str, Any], profile_override: str | None, target_override: int | None) -> tuple[str, int]:
    profile = profile_override or str(payload.get("profile", "balanced"))
    if profile not in PROFILE_TARGETS:
        raise BudgetError(f"profile must be one of: {', '.join(PROFILE_TARGETS)}")

    explicit = target_override if target_override is not None else payload.get("official_body_target")
    if explicit is None:
        target = PROFILE_TARGETS[profile]
    else:
        if isinstance(explicit, bool) or not isinstance(explicit, int):
            raise BudgetError("official_body_target must be an integer")
        target = explicit
    if target > OFFICIAL_BODY_HARD_CAP:
        raise BudgetError(
            f"official_body_target={target} exceeds the CUMCM hard cap of {OFFICIAL_BODY_HARD_CAP} (hard band 26-28)"
        )
    if target < OFFICIAL_BODY_HARD_FLOOR:
        raise BudgetError(
            f"official_body_target={target} is below the CUMCM hard floor of {OFFICIAL_BODY_HARD_FLOOR} (hard band 26-28)"
        )
    return profile, target


def _section_envelope(target: int) -> dict[str, int]:
    """Reserve body pages, leaving the exact remainder for the question core."""
    # Manually audited 2024 first-prize samples concentrated roughly 70-85%
    # of narrative space on the model/result chain.  These reserves keep the
    # same emphasis without turning the observation into an official quota.
    front = max(2, round(target * 0.10))
    validation = max(2, round(target * 0.08))
    evaluation_ai_refs = max(2, round(target * 0.08))
    core = target - front - validation - evaluation_ai_refs
    if core < 1:
        raise BudgetError("official body target leaves no pages for the core model")
    return {
        "front": front,
        "core": core,
        "validation": validation,
        "evaluation_ai_refs": evaluation_ai_refs,
    }


def _normalize_questions(raw_questions: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_questions, list) or not raw_questions:
        raise BudgetError("questions must be a non-empty list")
    normalized: list[dict[str, Any]] = []
    identifiers: set[str] = set()
    for index, raw in enumerate(raw_questions, start=1):
        if not isinstance(raw, dict):
            raise BudgetError(f"questions[{index - 1}] must be an object")
        identifier = str(raw.get("id", f"Q{index}")).strip()
        if not identifier:
            raise BudgetError(f"questions[{index - 1}].id must not be empty")
        if identifier in identifiers:
            raise BudgetError(f"duplicate question id: {identifier}")
        identifiers.add(identifier)

        scores = {field: _score(raw.get(field, 3), f"{identifier}.{field}") for field in SCORE_FIELDS}
        reuse_discount = _discount(raw.get("reuse_discount", 0), f"{identifier}.reuse_discount")
        raw_weight = sum(scores[field] * FIELD_WEIGHTS[field] for field in SCORE_FIELDS)
        # Reused material still needs a readable first explanation, so the discount
        # can remove at most half of its allocation signal.
        effective_weight = max(0.05, raw_weight * (1 - 0.5 * reuse_discount))
        normalized.append(
            {
                "id": identifier,
                "title": str(raw.get("title", identifier)).strip() or identifier,
                "scores": scores,
                "reuse_discount": reuse_discount,
                "raw_weight": raw_weight,
                "effective_weight": effective_weight,
            }
        )
    return normalized


def _largest_remainder(total_pages: int, questions: Sequence[dict[str, Any]]) -> list[int]:
    if total_pages < len(questions):
        raise BudgetError(
            f"core allocation has {total_pages} pages for {len(questions)} questions; "
            "increase official_body_target or combine non-independent questions"
        )
    remaining = total_pages - len(questions)
    total_weight = sum(float(question["effective_weight"]) for question in questions)
    quotas = [remaining * float(question["effective_weight"]) / total_weight for question in questions]
    pages = [1 + math.floor(quota) for quota in quotas]
    unassigned = total_pages - sum(pages)
    order = sorted(
        range(len(questions)),
        key=lambda index: (quotas[index] - math.floor(quotas[index]), questions[index]["effective_weight"], -index),
        reverse=True,
    )
    for index in order[:unassigned]:
        pages[index] += 1
    return pages


def _appendix_plan(payload: dict[str, Any]) -> dict[str, Any]:
    appendix = payload.get("appendix", {})
    if appendix is None:
        appendix = {}
    if not isinstance(appendix, dict):
        raise BudgetError("appendix must be an object")
    estimate = appendix.get("estimated_pages")
    if estimate is not None:
        if isinstance(estimate, bool) or not isinstance(estimate, int) or estimate < 0:
            raise BudgetError("appendix.estimated_pages must be a non-negative integer or null")
    raw_items = appendix.get("required_items", list(DEFAULT_APPENDIX_ITEMS))
    if not isinstance(raw_items, list) or not all(isinstance(item, str) and item.strip() for item in raw_items):
        raise BudgetError("appendix.required_items must be a list of non-empty strings")
    return {
        "counted_separately": True,
        "allocation_policy": "completeness_driven",
        "page_cap": None,
        "estimated_pages": estimate,
        "required_items": [item.strip() for item in raw_items],
        "instruction": "附录按复现完整性决定长度，不为追求页数而堆放正文性论证；以当年官方规则为最终依据。",
    }


def build_budget(
    payload: dict[str, Any], *, profile_override: str | None = None, target_override: int | None = None
) -> dict[str, Any]:
    """Return the deterministic ``analysis/page_budget.json`` payload."""
    if not isinstance(payload, dict):
        raise BudgetError("input JSON root must be an object")
    profile, target = _resolve_target(payload, profile_override, target_override)
    envelope = _section_envelope(target)
    questions = _normalize_questions(payload.get("questions"))
    allocated_pages = _largest_remainder(envelope["core"], questions)

    question_plans: list[dict[str, Any]] = []
    for question, pages in zip(questions, allocated_pages):
        body_share = pages / target
        core_share = pages / envelope["core"]
        under = core_share < 0.12
        over = core_share > 0.45
        question_plans.append(
            {
                "id": question["id"],
                "title": question["title"],
                "pages": pages,
                "official_body_share": round(body_share, 4),
                "core_share": round(core_share, 4),
                "weight_inputs": {
                    **question["scores"],
                    "reuse_discount": question["reuse_discount"],
                },
                "effective_weight": round(float(question["effective_weight"]), 6),
                "justification_flags": {
                    "under_12_percent": under,
                    "over_45_percent": over,
                    "requires_justification": under or over,
                    "reason": (
                        "核心问题篇幅占比低于 12%，须说明该问为何可短篇幅闭环"
                        if under
                        else "核心问题篇幅占比高于 45%，须说明该问为何应成为主导证据链"
                        if over
                        else None
                    ),
                },
            }
        )

    section_total = sum(envelope.values())
    return {
        "schema_version": "1.0",
        "artifact": "analysis/page_budget.json",
        "competition": "cumcm",
        "abstract": {
            "pages": ABSTRACT_PAGES,
            "counted_separately": True,
            "instruction": "电子版第一页放摘要；本工具将其与官方正文预算分账。",
        },
        "official_body": {
            "profile": profile,
            "target_pages": target,
            "hard_cap_pages": OFFICIAL_BODY_HARD_CAP,
            "hard_floor_pages": OFFICIAL_BODY_HARD_FLOOR,
            "within_hard_band": OFFICIAL_BODY_HARD_FLOOR <= target <= OFFICIAL_BODY_HARD_CAP,
            "sections": {
                "front": {
                    "pages": envelope["front"],
                    "scope": "问题重述、问题分析、假设与符号；只保留后文会调用的内容",
                },
                "core": {
                    "pages": envelope["core"],
                    "scope": "各问的模型、算法、结果与就地解释",
                },
                "validation": {
                    "pages": envelope["validation"],
                    "scope": "稳健性、灵敏度、误差、基线/消融与适用边界",
                },
                "evaluation_ai_refs": {
                    "pages": envelope["evaluation_ai_refs"],
                    "scope": "模型评价、关键 AI 使用声明、参考文献",
                },
            },
            "questions": question_plans,
            "accounting": {
                "section_pages_sum": section_total,
                "question_pages_sum": sum(allocated_pages),
                "core_pages": envelope["core"],
                "sum_matches_target": section_total == target and sum(allocated_pages) == envelope["core"],
            },
        },
        "appendix": _appendix_plan(payload),
        "review_gate": {
            "remeasure_after_render": True,
            "required_checks": [
                "按当年官方模板重新确认摘要、正文与附录的页界",
                "核对实际正文页数落在 26-28 页硬性区间内",
                "逐一解释占正文不足 12% 或超过 45% 的问题篇幅",
                "确认附录中的代码、文件清单和复现说明完整且没有正文性填充",
            ],
        },
        "disclaimer": (
            "本预算来自写作启发式与小样本获奖论文观察，不是官方页数规则，也不保证获奖；"
            "如当年通知、模板或赛题结构与本预算冲突，必须以当年官方文件和实际证据链为准。"
        ),
    }


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


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create an adaptive CUMCM page budget (default output: analysis/page_budget.json)."
    )
    parser.add_argument("--input", required=True, help="JSON file containing questions and optional profile/appendix")
    parser.add_argument("--output", default="analysis/page_budget.json", help="Output JSON path")
    parser.add_argument("--profile", choices=tuple(PROFILE_TARGETS), help="Override the input profile")
    parser.add_argument("--target", type=int, help="Override official_body_target; must be within the hard band 26-28")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        input_path = Path(args.input).expanduser().resolve()
        with input_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        budget = build_budget(payload, profile_override=args.profile, target_override=args.target)
        output_path = Path(args.output).expanduser().resolve()
        atomic_json_write(output_path, budget)
    except (OSError, json.JSONDecodeError, BudgetError) as exc:
        print(f"page-budget error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"output": str(output_path), "official_body_pages": budget["official_body"]["target_pages"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
