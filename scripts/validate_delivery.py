#!/usr/bin/env python3
"""Validate a completed mathmodel workspace and generate its delivery manifest."""

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
from typing import Any, Iterable

try:
    from scripts.console import configure_stdio
except ImportError:
    from console import configure_stdio


PLACEHOLDER_RE = re.compile(
    r"\b(?:TODO|TBD|AUTHOR_INPUT_NEEDED)\b|\[TO CONFIRM(?::[^\]]*)?\]|\?\?",
    re.IGNORECASE,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    atomic_write(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def first_existing(paths: Iterable[Path]) -> Path | None:
    return next((path for path in paths if path.exists() and path.is_file()), None)


def nonempty_files(directory: Path, suffixes: set[str] | None = None) -> list[Path]:
    if not directory.exists():
        return []
    files = [path for path in directory.rglob("*") if path.is_file() and path.stat().st_size > 0]
    if suffixes is not None:
        files = [path for path in files if path.suffix.lower() in suffixes]
    return sorted(files)


def check(name: str, passed: bool, evidence: str, severity: str = "error") -> dict[str, str]:
    return {"name": name, "status": "pass" if passed else "fail", "severity": severity, "evidence": evidence}


def read_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except (OSError, json.JSONDecodeError) as exc:
        return None, str(exc)


def page_structure_ok(payload: dict[str, Any] | None) -> tuple[bool, str]:
    if payload is None:
        return False, "missing or invalid"
    keys = (
        "pdf_total_pages",
        "abstract_pages",
        "official_body_start_pdf_page",
        "official_body_end_pdf_page",
        "official_body_pages",
        "appendix_start_pdf_page",
        "appendix_pages",
    )
    if not all(isinstance(payload.get(key), int) and not isinstance(payload.get(key), bool) for key in keys):
        return False, "required integer page fields missing"
    total = payload["pdf_total_pages"]
    abstract = payload["abstract_pages"]
    body_start = payload["official_body_start_pdf_page"]
    body_end = payload["official_body_end_pdf_page"]
    body = payload["official_body_pages"]
    appendix_start = payload["appendix_start_pdf_page"]
    appendix = payload["appendix_pages"]
    passed = all(
        (
            total > 0,
            abstract == 1,
            body_start == abstract + 1,
            body == body_end - body_start + 1,
            26 <= body <= 28,
            appendix_start == body_end + 1,
            appendix >= 1,
            total == abstract + body + appendix,
        )
    )
    return passed, json.dumps({key: payload.get(key) for key in keys}, ensure_ascii=False)


def rel(path: Path, workspace: Path) -> str:
    try:
        return path.resolve().relative_to(workspace).as_posix()
    except ValueError:
        return str(path.resolve())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True, help="Completed contest workspace")
    parser.add_argument("--report", help="JSON report path; defaults to qa/delivery_validation.json")
    return parser.parse_args()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    workspace = Path(args.workspace).expanduser().resolve()
    report_path = Path(args.report).expanduser().resolve() if args.report else workspace / "qa" / "delivery_validation.json"
    state_path = workspace / "state" / "decision_log.json"
    checks: list[dict[str, str]] = []
    artifacts: list[Path] = []

    state, state_error = read_json(state_path) if state_path.exists() else (None, "missing")
    checks.append(check("decision_log", state is not None, rel(state_path, workspace) if state else state_error or "invalid"))
    if state_path.exists():
        artifacts.append(state_path)
    if state is not None:
        execution = state.get("execution") or {}
        unresolved_blockers = execution.get("blockers") or []
        checks.append(check("state_blockers_closed", not unresolved_blockers, ", ".join(map(str, unresolved_blockers)) or "none"))
        inference = (execution.get("source_packet") or {}).get("competition_inference") or {}
        checks.append(check("competition_template_locked", inference.get("template_locked") is True, json.dumps(inference, ensure_ascii=False)))
        aggregate = ((((state.get("stages") or {}).get("9") or {}).get("panel_scores") or {}).get("aggregate_v1") or {})
        blocking_open = aggregate.get("blocking_open")
        checks.append(check("review_blockers_closed", blocking_open == 0, f"blocking_open={blocking_open}"))

    final_hint = None
    if state:
        final_hint = (((state.get("stages") or {}).get("9") or {}).get("final_pdf_path"))
    pdf_candidates = [workspace / "paper_output" / "paper.pdf", workspace / "paper.pdf"]
    if final_hint:
        hinted = Path(final_hint)
        pdf_candidates.insert(0, hinted if hinted.is_absolute() else workspace / hinted)
    pdf_path = first_existing(pdf_candidates)
    pdf_valid = False
    pdf_evidence = "missing"
    if pdf_path:
        try:
            head = pdf_path.read_bytes()[:5]
            pdf_valid = head == b"%PDF-" and pdf_path.stat().st_size >= 5_000
            pdf_evidence = f"{rel(pdf_path, workspace)} ({pdf_path.stat().st_size} bytes)"
            artifacts.append(pdf_path)
        except OSError as exc:
            pdf_evidence = str(exc)
    checks.append(check("final_pdf", pdf_valid, pdf_evidence))

    tex_path = first_existing((workspace / "paper_output" / "paper.tex", workspace / "paper_workspace" / "paper.tex"))
    checks.append(check("editable_tex", tex_path is not None, rel(tex_path, workspace) if tex_path else "missing"))
    if tex_path:
        artifacts.append(tex_path)

    bib_path = first_existing((workspace / "paper_output" / "references.bib", workspace / "paper_workspace" / "references.bib"))
    checks.append(check("references_bib", bib_path is not None, rel(bib_path, workspace) if bib_path else "missing"))
    if bib_path:
        artifacts.append(bib_path)

    run_entry = first_existing(
        list((workspace / "src").glob("run_all.*")) if (workspace / "src").exists() else []
    )
    checks.append(check("run_entrypoint", run_entry is not None, rel(run_entry, workspace) if run_entry else "src/run_all.* missing"))
    if run_entry:
        artifacts.append(run_entry)

    environment = first_existing(
        (
            workspace / "requirements.txt",
            workspace / "environment.yml",
            workspace / "pyproject.toml",
            workspace / "renv.lock",
        )
    )
    checks.append(check("environment_lock", environment is not None, rel(environment, workspace) if environment else "missing"))
    if environment:
        artifacts.append(environment)

    result_files = nonempty_files(workspace / "results")
    checks.append(check("structured_results", bool(result_files), f"{len(result_files)} non-empty files"))
    artifacts.extend(result_files)

    figure_files = nonempty_files(workspace / "figures", {".png", ".jpg", ".jpeg", ".svg", ".pdf", ".tif", ".tiff"})
    checks.append(check("figures", bool(figure_files), f"{len(figure_files)} figure files"))
    artifacts.extend(figure_files)

    qa_files = {
        "statistics_audit": workspace / "qa" / "statistics_audit.md",
        "citation_audit": workspace / "qa" / "citation_audit.md",
        "consistency_sweep": workspace / "qa" / "consistency_sweep.md",
        "visual_qa": workspace / "qa" / "visual_qa.md",
        "reviewer_synthesis": workspace / "qa" / "reviewer_synthesis.md",
    }
    for name, path in qa_files.items():
        ok = path.exists() and path.is_file() and path.stat().st_size > 0
        checks.append(check(name, ok, rel(path, workspace) if ok else "missing or empty"))
        if ok:
            artifacts.append(path)

    algorithm_audit_path = workspace / "qa" / "algorithm_claim_consistency.json"
    algorithm_audit, algorithm_error = (
        read_json(algorithm_audit_path) if algorithm_audit_path.exists() else (None, "missing")
    )
    algorithm_ok = algorithm_audit is not None and algorithm_audit.get("blocking_count") == 0
    checks.append(
        check(
            "algorithm_claim_consistency",
            algorithm_ok,
            f"blocking_count={algorithm_audit.get('blocking_count')}" if algorithm_audit else algorithm_error or "invalid",
        )
    )
    if algorithm_audit_path.exists():
        artifacts.append(algorithm_audit_path)

    for reviewer_id in (1, 2, 3):
        reviewer_path = workspace / "qa" / f"reviewer_{reviewer_id}.json"
        reviewer, reviewer_error = read_json(reviewer_path) if reviewer_path.exists() else (None, "missing")
        checks.append(
            check(
                f"reviewer_{reviewer_id}",
                reviewer is not None,
                rel(reviewer_path, workspace) if reviewer else reviewer_error or "invalid",
            )
        )
        if reviewer_path.exists():
            artifacts.append(reviewer_path)

    repro_path = workspace / "qa" / "reproducibility.json"
    repro, repro_error = read_json(repro_path) if repro_path.exists() else (None, "missing")
    exit_code = None if repro is None else repro.get("exit_code", repro.get("returncode"))
    repro_ok = repro is not None and exit_code == 0
    checks.append(check("reproducibility", repro_ok, f"exit_code={exit_code}" if repro else repro_error or "invalid"))
    if repro_path.exists():
        artifacts.append(repro_path)

    placeholder_hits: list[str] = []
    for source in (tex_path, bib_path):
        if not source:
            continue
        try:
            for line_no, line in enumerate(source.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
                if PLACEHOLDER_RE.search(line):
                    placeholder_hits.append(f"{rel(source, workspace)}:{line_no}")
        except OSError as exc:
            placeholder_hits.append(f"{rel(source, workspace)}:read_error:{exc}")
    checks.append(check("no_placeholders", not placeholder_hits, ", ".join(placeholder_hits[:20]) or "none"))

    if state is not None and state.get("competition") == "cumcm":
        compliance = ((state.get("compliance") or {}).get("cumcm") or {})
        checks.append(check("cumcm_ruleset", compliance.get("ruleset") == "cumcm_2026", str(compliance.get("ruleset"))))
        checks.append(
            check(
                "cumcm_paper_under_20mb",
                pdf_path is not None and pdf_path.stat().st_size <= 20 * 1024 * 1024,
                f"bytes={pdf_path.stat().st_size if pdf_path else 'missing'}",
            )
        )

        ai_log_path = workspace / "qa" / "ai_usage_log.json"
        ai_log, ai_log_error = read_json(ai_log_path) if ai_log_path.exists() else (None, "missing")
        ai_log_ok = bool(
            ai_log
            and ai_log.get("tools")
            and ai_log.get("uses")
            and ai_log.get("recording_scope") == "key_material_interactions"
            and ai_log.get("recording_mode", "summary-only") == "summary-only"
        )
        checks.append(check("cumcm_ai_usage_log", ai_log_ok, rel(ai_log_path, workspace) if ai_log_ok else ai_log_error or "tools/uses or key-event recording scope invalid"))
        if ai_log_path.exists():
            artifacts.append(ai_log_path)

        ai_details_path = workspace / "qa" / "AI 工具使用详情.pdf"
        ai_details_ok = False
        if ai_details_path.exists():
            try:
                ai_details_ok = ai_details_path.stat().st_size >= 5000 and ai_details_path.read_bytes()[:5] == b"%PDF-"
            except OSError:
                ai_details_ok = False
        checks.append(check("cumcm_ai_details_pdf", ai_details_ok, rel(ai_details_path, workspace) if ai_details_ok else "missing or invalid PDF"))
        if ai_details_path.exists():
            artifacts.append(ai_details_path)

        page_budget_path = workspace / "analysis" / "page_budget.json"
        page_budget, page_budget_error = read_json(page_budget_path) if page_budget_path.exists() else (None, "missing")
        budget_target = (page_budget.get("official_body") or {}).get("target_pages") if page_budget else None
        page_budget_ok = bool(
            page_budget
            and isinstance(budget_target, int)
            and not isinstance(budget_target, bool)
            and 26 <= budget_target <= 28
            and ((page_budget.get("appendix") or {}).get("allocation_policy") == "completeness_driven")
        )
        checks.append(check("cumcm_page_budget", page_budget_ok, rel(page_budget_path, workspace) if page_budget_ok else page_budget_error or "invalid budget"))
        if page_budget_path.exists():
            artifacts.append(page_budget_path)

        novelty_path = workspace / "analysis" / "novelty_ledger.json"
        novelty, novelty_error = read_json(novelty_path) if novelty_path.exists() else (None, "missing")
        novelty_ok = novelty is not None and novelty.get("unsupported_claims", 1) == 0
        checks.append(check("cumcm_novelty_ledger", novelty_ok, f"unsupported_claims={novelty.get('unsupported_claims')}" if novelty else novelty_error or "invalid"))
        if novelty_path.exists():
            artifacts.append(novelty_path)

        page_audit_path = workspace / "qa" / "page_structure_audit.json"
        page_audit, page_audit_error = read_json(page_audit_path) if page_audit_path.exists() else (None, "missing")
        structure_ok, structure_evidence = page_structure_ok(page_audit)
        checks.append(check("cumcm_page_structure", structure_ok, structure_evidence if page_audit else page_audit_error or structure_evidence))
        paper_state = compliance.get("paper") or {}
        state_matches = structure_ok and paper_state.get("page_structure_audited") is True and all(
            paper_state.get(key) == page_audit.get(key)
            for key in (
                "pdf_total_pages",
                "abstract_pages",
                "official_body_start_pdf_page",
                "official_body_end_pdf_page",
                "official_body_pages",
                "appendix_start_pdf_page",
                "appendix_pages",
            )
        )
        checks.append(check("cumcm_page_structure_state_matches", state_matches, rel(page_audit_path, workspace) if state_matches else "state/audit mismatch"))
        if page_audit_path.exists():
            artifacts.append(page_audit_path)

        tex_text = tex_path.read_text(encoding="utf-8", errors="ignore") if tex_path else ""
        normalized_tex = re.sub(r"\s+", "", tex_text)
        ai_pos = normalized_tex.find("AI工具使用声明")
        ref_pos = normalized_tex.rfind("参考文献")
        checks.append(check("cumcm_no_table_of_contents", "\\tableofcontents" not in tex_text, "tableofcontents absent" if "\\tableofcontents" not in tex_text else "tableofcontents present"))
        checks.append(check("cumcm_ai_statement_before_references", ai_pos >= 0 and ref_pos > ai_pos, f"ai={ai_pos}, references={ref_pos}"))
        appendix_ok = "支撑材料文件列表" in tex_text and ("程序代码" in tex_text or "源程序" in tex_text)
        checks.append(check("cumcm_appendix_contract", appendix_ok, "support list and source-code appendix markers" if appendix_ok else "required appendix markers missing"))

        # === 2026-08-20 新增强制性硬门 ===

        # 硬门 H1: 摘要恰好 1 页（从"原则上不超过 1 页"升级为硬门）
        abstract_pages_value = page_audit.get("abstract_pages") if page_audit else None
        abstract_pages_ok = abstract_pages_value == 1
        checks.append(check("cumcm_abstract_one_page", abstract_pages_ok, f"abstract_pages={abstract_pages_value}"))

        # 硬门 H2: 附录结构——必须含三段且按 A/B/C 顺序（支撑材料→源代码→结果详表）
        appendix_section_aliases = [
            ("支撑材料文件列表", ("支撑材料文件列表",)),
            ("完整源程序代码", ("建模完整源程序代码", "完整源程序代码", "源程序代码")),
            ("计算结果详表", ("计算结果详表",)),
        ]
        appendix_hits = []
        missing_sections = []
        for canonical, aliases in appendix_section_aliases:
            positions = [tex_text.find(alias) for alias in aliases if tex_text.find(alias) >= 0]
            if not positions:
                missing_sections.append(canonical)
                appendix_hits.append((canonical, -1))
            else:
                appendix_hits.append((canonical, min(positions)))
        if missing_sections:
            appendix_three_ok = False
            appendix_order_evidence = f"missing: {missing_sections}"
        else:
            positions = [pos for _, pos in appendix_hits]
            appendix_three_ok = positions == sorted(positions)
            appendix_order_evidence = "all present in A/B/C order" if appendix_three_ok else f"order={positions}"
        checks.append(check("cumcm_appendix_three_sections_in_order", appendix_three_ok, appendix_order_evidence))

        # 硬门 H3: 附录大标题 + 节前缀"附录A/B/C"（缺一即阻断）
        has_appendix_heading = bool(re.search(r"\\heiti\s*附录|\\section\*?\{附录\}", tex_text))
        has_appendix_label = r"\renewcommand{\thesection}{附录\Alph{section}}" in tex_text
        appendix_struct_ok = has_appendix_heading and has_appendix_label
        appendix_struct_evidence = (
            "OK: big 附录 heading + 附录X prefix"
            if appendix_struct_ok
            else f"missing heading={not has_appendix_heading}, missing prefix={not has_appendix_label}"
        )
        checks.append(check("cumcm_appendix_heading_and_prefix", appendix_struct_ok, appendix_struct_evidence))

        # 硬门 H4: 流程图必须是真图形（figure 环境中不得用 tabular+rightarrow 拼流程图）
        flow_evidence = "OK: no tabular+rightarrow inside figure"
        flow_ok = True
        # 精确检查每个 \begin{figure}...\caption{} 块内是否同时出现 tabular 与 \rightarrow
        for fig_match in re.finditer(r"\\begin\{figure\}\[?[^\]]*\]?", tex_text):
            block_end = tex_text.find(r"\end{figure}", fig_match.end())
            if block_end < 0:
                continue
            block = tex_text[fig_match.start():block_end]
            if r"\begin{tabular}" in block and r"\rightarrow" in block:
                flow_ok = False
                flow_evidence = f"tabular+rightarrow inside figure at offset {fig_match.start()}"
                break
        checks.append(check("cumcm_flowchart_must_be_real_graphics", flow_ok, flow_evidence))

        # 硬门 H5: 匿名门——论文 PDF 全文（已提取文本）不得含身份/学校/赛区关键词（与之前 document scan 互不重复）
        final_pdf_text = ""
        if pdf_path:
            try:
                from PyPDF2 import PdfReader  # type: ignore
                final_pdf_text = "\n".join(p.extract_text() or "" for p in PdfReader(str(pdf_path)).pages)
            except Exception:
                final_pdf_text = ""
        identity_terms = ["赛区评阅编号", "赛区组委会", "承诺书", "参赛学校", "所在学校", "赛区编号"]
        identity_hits = [t for t in identity_terms if t in final_pdf_text]
        anonymity_ok = not identity_hits
        checks.append(check("cumcm_anonymity_no_identity_terms", anonymity_ok, ",".join(identity_hits) if identity_hits else "none"))

        # 软性门 W1: 分组对比类箱线图应有 n= 标注（不阻断，仅警告）
        # n= 标注可能位于 .tex 正文、figure 源 .py、或 figure 注释中
        # 扫描三层：(a) .tex 全局是否含 n=；(b) src/ 下 .py 源文件中是否含 'n=' 紧邻 boxplot 调用
        boxplot_keywords = ["箱线图", "boxplot", "box 图", "Box Plot"]
        has_boxplot_keyword = any(kw in tex_text for kw in boxplot_keywords)
        if has_boxplot_keyword:
            tex_has_n = bool(re.search(r"n\s*=\s*\d+", tex_text))
            # 扫描 src/ 下的 figure 生成源文件
            src_dir = workspace / "src"
            py_has_n = False
            if src_dir.is_dir():
                for py_file in src_dir.glob("*.py"):
                    try:
                        py_text = py_file.read_text(encoding="utf-8")
                    except Exception:
                        continue
                    if "boxplot" in py_text and re.search(r"n\s*=\s*\{|ax\.text\([^)]*n=|['\"]n=\{|f['\"]n=\{|f['\"]n =", py_text):
                        py_has_n = True
                        break
            box_n_ok = tex_has_n or py_has_n
            box_n_evidence = (
                "OK: n= in tex or py source"
                if box_n_ok
                else f"box plot mentioned but no n= in tex (tex_n={tex_has_n}) or src/*.py (py_n={py_has_n})"
            )
        else:
            box_n_ok = True
            box_n_evidence = "no box plot in paper"
        checks.append(check("cumcm_boxplot_n_labels", box_n_ok, box_n_evidence, severity="warning"))

    blockers = [item for item in checks if item["status"] == "fail" and item["severity"] == "error"]
    ready = not blockers
    unique_artifacts = sorted({path.resolve() for path in artifacts if path.exists()}, key=str)
    artifact_rows = [
        {"path": rel(path, workspace), "bytes": path.stat().st_size, "sha256": sha256(path)}
        for path in unique_artifacts
    ]
    report = {
        "schema_version": "1.0",
        "generated_at": utc_now(),
        "workspace": str(workspace),
        "submission_ready": ready,
        "checks": checks,
        "blocking_checks": [item["name"] for item in blockers],
        "artifacts": artifact_rows,
    }
    atomic_json(report_path, report)

    manifest_lines = [
        "# DELIVERY MANIFEST",
        "",
        f"- Generated: `{report['generated_at']}`",
        f"- Submission ready: `{'YES' if ready else 'NO'}`",
        f"- Validation report: `{rel(report_path, workspace)}`",
        "",
        "## Validation",
        "",
        "| Check | Status | Evidence |",
        "|---|---|---|",
    ]
    for item in checks:
        evidence = item["evidence"].replace("|", "\\|")
        manifest_lines.append(f"| {item['name']} | {item['status'].upper()} | {evidence} |")
    manifest_lines.extend(["", "## Artifacts", "", "| Path | Bytes | SHA-256 |", "|---|---:|---|"])
    for item in artifact_rows:
        manifest_lines.append(f"| `{item['path']}` | {item['bytes']} | `{item['sha256']}` |")
    if blockers:
        manifest_lines.extend(["", "## Blocking checks", ""])
        manifest_lines.extend(f"- `{item['name']}`: {item['evidence']}" for item in blockers)
    atomic_write(workspace / "DELIVERY_MANIFEST.md", "\n".join(manifest_lines) + "\n")

    if state is not None:
        execution = state.setdefault("execution", {})
        execution["status"] = "ready" if ready else "blocked"
        execution["finished_at"] = utc_now() if ready else None
        state.setdefault("qa", {})["delivery"] = {
            "status": "pass" if ready else "fail",
            "report": rel(report_path, workspace),
            "blocking_checks": report["blocking_checks"],
        }
        state.setdefault("artifacts", {})["produced"] = [
            *[item["path"] for item in artifact_rows],
            rel(report_path, workspace),
            "DELIVERY_MANIFEST.md",
        ]
        state["artifacts"]["validation_report"] = rel(report_path, workspace)
        stages = state.setdefault("stages", {})
        stage9 = stages.setdefault("9", {})
        stage9["submission_ready"] = ready
        if pdf_path:
            stage9["final_pdf_path"] = rel(pdf_path, workspace)
        atomic_json(state_path, state)

    print(json.dumps({"submission_ready": ready, "report": str(report_path), "blocking_checks": report["blocking_checks"]}, ensure_ascii=False))
    return 0 if ready else 1


if __name__ == "__main__":
    configure_stdio()
    sys.exit(main())
