#!/usr/bin/env python3
"""Run a deterministic, dependency-free end-to-end mathmodel-skill demo.

The fixture is intentionally synthetic.  It demonstrates the same observable
shape as a small delivery: input packet, decision state, model card, computed
results, and a SHA-256 manifest.  It never writes to the skill checkout unless
the caller explicitly chooses a safe output directory.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import sys
from html import escape
from decimal import Decimal, ROUND_DOWN
from pathlib import Path


EXAMPLE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = EXAMPLE_ROOT.parents[1]
DATA_PATH = EXAMPLE_ROOT / "data.csv"
PROBLEM_PATH = EXAMPLE_ROOT / "problem.md"
BUDGET = Decimal("10000.00")


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _read_rows() -> list[dict[str, object]]:
    with DATA_PATH.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        expected = ["region", "population", "demand_index"]
        if reader.fieldnames != expected:
            raise ValueError(f"data.csv must have columns: {', '.join(expected)}")
        rows: list[dict[str, object]] = []
        for row in reader:
            region = (row.get("region") or "").strip()
            if not region:
                raise ValueError("every row needs a non-empty region")
            try:
                population = int(row["population"] or "")
                demand_index = Decimal(row["demand_index"] or "")
            except (KeyError, ValueError, ArithmeticError) as exc:
                raise ValueError(f"invalid numeric data for {region!r}") from exc
            if population <= 0 or demand_index <= 0:
                raise ValueError(f"population and demand_index must be positive: {region!r}")
            rows.append(
                {
                    "region": region,
                    "population": population,
                    "demand_index": demand_index,
                    "weight": Decimal(population) * demand_index,
                }
            )
    if not rows:
        raise ValueError("data.csv must contain at least one row")
    return rows


def _allocate(
    rows: list[dict[str, object]],
    demand_multiplier: tuple[str, Decimal] | None = None,
) -> list[dict[str, object]]:
    """Allocate the budget, optionally perturbing one region's demand index."""
    weighted_rows: list[dict[str, object]] = []
    for row in rows:
        multiplier = (
            demand_multiplier[1]
            if demand_multiplier is not None and row["region"] == demand_multiplier[0]
            else Decimal("1")
        )
        weighted_rows.append(
            {
                **row,
                "scenario_demand_index": row["demand_index"] * multiplier,
                "scenario_weight": row["weight"] * multiplier,
            }
        )
    total_weight = sum((row["scenario_weight"] for row in weighted_rows), Decimal("0"))
    budget_cents = int((BUDGET * 100).to_integral_value())
    allocations: list[dict[str, object]] = []
    for row in weighted_rows:
        raw = BUDGET * row["scenario_weight"] / total_weight
        cents = int((raw * 100).to_integral_value(rounding=ROUND_DOWN))
        allocations.append({**row, "raw_cents": raw * 100, "cents": cents})

    remainder = budget_cents - sum(int(item["cents"]) for item in allocations)
    ranked = sorted(
        range(len(allocations)),
        key=lambda index: (
            allocations[index]["raw_cents"] - allocations[index]["cents"],
            str(allocations[index]["region"]),
        ),
        reverse=True,
    )
    for index in ranked[:remainder]:
        allocations[index]["cents"] += 1

    for item in allocations:
        amount = Decimal(int(item["cents"])) / 100
        item["allocation"] = amount.quantize(Decimal("0.01"))
        item["share"] = (amount / BUDGET * 100).quantize(Decimal("0.01"))
    return allocations


def _write_svg(path: Path, allocations: list[dict[str, object]]) -> None:
    """Write a dependency-free SVG bar chart for the baseline allocation."""
    width, height = 760, 420
    chart_left, chart_top, chart_width, chart_height = 80, 45, 630, 290
    max_value = max(float(item["allocation"]) for item in allocations) or 1.0
    gap = chart_width / len(allocations)
    bar_width = gap * 0.62
    bars: list[str] = []
    for index, item in enumerate(allocations):
        value = float(item["allocation"])
        x = chart_left + index * gap + (gap - bar_width) / 2
        bar_height = value / max_value * chart_height
        y = chart_top + chart_height - bar_height
        label = escape(str(item["region"]))
        bars.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width:.1f}" height="{bar_height:.1f}" fill="#5b5bd6" rx="4"/>'
            f'<text x="{x + bar_width / 2:.1f}" y="{height - 48}" text-anchor="middle" font-size="14" fill="#202124">{label}</text>'
            f'<text x="{x + bar_width / 2:.1f}" y="{max(y - 8, 20):.1f}" text-anchor="middle" font-size="12" fill="#202124">{value:,.2f}</text>'
        )
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
        '<title>Budget allocation by region</title><rect width="100%" height="100%" fill="white"/>'
        f'<text x="{width / 2}" y="25" text-anchor="middle" font-size="18" font-family="sans-serif" fill="#202124">Synthetic budget allocation</text>'
        f'<line x1="{chart_left}" y1="{chart_top + chart_height}" x2="{chart_left + chart_width}" y2="{chart_top + chart_height}" stroke="#777"/>'
        + "".join(bars)
        + "</svg>\n"
    )
    path.write_text(svg, encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_output(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    if resolved in {REPO_ROOT.resolve(), EXAMPLE_ROOT.resolve()}:
        raise ValueError("choose a dedicated output directory, not the repository")
    if resolved in EXAMPLE_ROOT.parents or EXAMPLE_ROOT in resolved.parents:
        raise ValueError("output must not overwrite or sit inside the example source")
    return resolved


def run(output: Path, force: bool = False) -> Path:
    output = _safe_output(output)
    if output.exists():
        if not force:
            raise FileExistsError(f"output already exists: {output}; use --force to replace it")
        if output.is_symlink() or not output.is_dir():
            raise ValueError("--force only removes an existing output directory")
        shutil.rmtree(output)

    rows = _read_rows()
    allocations = _allocate(rows)
    total_weight = sum((row["weight"] for row in rows), Decimal("0"))
    output.mkdir(parents=True)
    (output / "input").mkdir()
    for dirname in ("state", "analysis", "results", "qa"):
        (output / dirname).mkdir()
    shutil.copyfile(PROBLEM_PATH, output / "input" / "problem.md")
    shutil.copyfile(DATA_PATH, output / "input" / "data.csv")

    stage_state = {
        str(index): {"status": "complete"}
        for index in range(10)
    }
    _write_json(
        output / "state" / "decision_log.json",
        {
            "_schema_version": "demo-1.0",
            "competition": "cumcm-demo",
            "mode": "autopilot",
            "current_stage": 9,
            "stages": stage_state,
            "decisions": {
                "objective": "population-demand weighted proportional allocation",
                "budget": "10000.00",
                "data_status": "synthetic fixture",
            },
        },
    )
    _write_json(
        output / "analysis" / "model_card.json",
        {
            "model": "population-demand weighted proportional allocation",
            "objective": "allocate the full budget while preserving transparent demand weighting",
            "formula": "allocation_i = budget * population_i * demand_index_i / sum_j(population_j * demand_index_j)",
            "assumptions": [
                "population is a positive demand proxy",
                "demand_index is a synthetic, dimensionless scenario factor",
                "all units are divisible to 0.01 and the full budget must be allocated",
            ],
            "limitations": [
                "synthetic data only",
                "no travel-time, capacity, uncertainty, or fairness constraint is modeled",
            ],
            "sensitivity": {
                "method": "one-at-a-time demand-index perturbation",
                "scenarios": ["-10%", "baseline", "+10%"],
                "artifact": "results/sensitivity.csv",
            },
            "total_weight": str(total_weight),
        },
    )

    with (output / "results" / "allocation.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["region", "population", "demand_index", "weight", "allocation", "share_pct"],
        )
        writer.writeheader()
        for item in allocations:
            writer.writerow(
                {
                    "region": item["region"],
                    "population": item["population"],
                    "demand_index": item["demand_index"],
                    "weight": item["weight"],
                    "allocation": f"{item['allocation']:.2f}",
                    "share_pct": f"{item['share']:.2f}",
                }
            )

    sensitivity_rows: list[dict[str, object]] = []
    for region in (str(row["region"]) for row in rows):
        for scenario, multiplier in (
            ("-10%", Decimal("0.90")),
            ("baseline", Decimal("1.00")),
            ("+10%", Decimal("1.10")),
        ):
            for item in _allocate(rows, (region, multiplier)):
                sensitivity_rows.append(
                    {
                        "scenario": f"{region}:{scenario}",
                        "perturbed_region": region,
                        "demand_multiplier": multiplier,
                        "region": item["region"],
                        "allocation": f"{item['allocation']:.2f}",
                    }
                )
    with (output / "results" / "sensitivity.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["scenario", "perturbed_region", "demand_multiplier", "region", "allocation"],
        )
        writer.writeheader()
        writer.writerows(sensitivity_rows)
    _write_svg(output / "results" / "allocation.svg", allocations)

    amounts = [item["allocation"] for item in allocations]
    _write_json(
        output / "results" / "summary.json",
        {
            "budget": f"{BUDGET:.2f}",
            "total_allocated": f"{sum(amounts, Decimal('0')):.2f}",
            "regions": len(allocations),
            "largest_allocation": f"{max(amounts):.2f}",
            "smallest_allocation": f"{min(amounts):.2f}",
            "checks": {
                "all_positive": all(amount > 0 for amount in amounts),
                "budget_conserved": sum(amounts, Decimal("0")) == BUDGET,
            },
        },
    )

    files = {
        str(path.relative_to(output)).replace("\\", "/"): _sha256(path)
        for path in sorted(output.rglob("*"))
        if path.is_file()
    }
    _write_json(
        output / "qa" / "manifest.json",
        {
            "schema": "mathmodel-demo-manifest-v1",
            "generated_by": "examples/quickstart/run_demo.py",
            "synthetic_data": True,
            "ready": True,
            "files": files,
        },
    )
    return output


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate the synthetic mathmodel-skill quickstart delivery")
    parser.add_argument("--output", type=Path, default=Path.cwd() / "demo-output")
    parser.add_argument("--force", action="store_true", help="replace an existing dedicated output directory")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        output = run(args.output, force=args.force)
    except (FileExistsError, OSError, ValueError) as exc:
        print(f"demo failed: {exc}", file=sys.stderr)
        return 2
    print(f"demo complete: {output}")
    print("artifacts: input/, state/, analysis/, results/ (allocation, sensitivity, SVG), qa/manifest.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
