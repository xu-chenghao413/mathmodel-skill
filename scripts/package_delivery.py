#!/usr/bin/env python3
"""Package a mathmodel workspace into one versioned delivery folder."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


MAX_CUMCM_BYTES = 20 * 1024 * 1024


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def digest(path: Path, algorithm: str) -> str:
    value = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def pdf_signature_ok(path: Path) -> bool:
    try:
        return path.is_file() and path.stat().st_size >= 5000 and path.read_bytes()[:5] == b"%PDF-"
    except OSError:
        return False


def copy_tree(source: Path, destination: Path) -> None:
    if not source.exists():
        return
    shutil.copytree(
        source,
        destination,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".git", ".DS_Store"),
    )


def next_version(root: Path, stem: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    pattern = re.compile(re.escape(stem) + r"_v(\d{3})$")
    versions = [int(match.group(1)) for item in root.iterdir() if item.is_dir() and (match := pattern.match(item.name))]
    return root / f"{stem}_v{(max(versions, default=0) + 1):03d}"


def check(name: str, passed: bool, evidence: str) -> dict[str, str]:
    return {"name": name, "status": "pass" if passed else "fail", "evidence": evidence}


def load_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def page_structure_ok(payload: dict[str, Any]) -> tuple[bool, str]:
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
    conditions = (
        total > 0,
        abstract == 1,
        body_start == abstract + 1,
        body == body_end - body_start + 1,
        26 <= body <= 28,
        appendix_start == body_end + 1,
        appendix >= 1,
        total == abstract + body + appendix,
    )
    evidence = json.dumps({key: payload.get(key) for key in keys}, ensure_ascii=False)
    return all(conditions), evidence


def extract_pdf_text(path: Path, first_page_only: bool = False) -> tuple[str | None, str | None]:
    command = shutil.which("pdftotext")
    if command:
        args = [command]
        if first_page_only:
            args.extend(["-f", "1", "-l", "1"])
        args.extend(["-enc", "UTF-8", str(path), "-"])
        try:
            run = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
            if run.returncode == 0 and run.stdout.strip():
                return run.stdout, None
            return None, (run.stderr or f"pdftotext exit {run.returncode}").strip()
        except OSError as exc:
            return None, str(exc)
    return None, "pdftotext unavailable"


def iter_files(root: Path) -> Iterable[Path]:
    if root.exists():
        yield from sorted(path for path in root.rglob("*") if path.is_file())


def make_support_archive(workspace: Path, archive_path: Path, ai_details: Path | None) -> list[str]:
    included: list[str] = []
    with tempfile.TemporaryDirectory(prefix="mathmodel-support-") as temp_name:
        stage = Path(temp_name) / "支撑材料"
        stage.mkdir(parents=True)
        mapping = {
            "src": "源程序",
            "results": "计算结果",
            "figures": "图表与中间结果",
            "data_processed": "处理后数据",
            "support_materials": "补充资料",
        }
        for source_name, destination_name in mapping.items():
            source = workspace / source_name
            if source.exists() and any(source.rglob("*")):
                copy_tree(source, stage / destination_name)
        for name in ("requirements.txt", "environment.yml", "pyproject.toml", "renv.lock"):
            source = workspace / name
            if source.exists() and source.is_file():
                shutil.copy2(source, stage / source.name)
        repro = workspace / "qa" / "reproducibility.json"
        if repro.exists():
            shutil.copy2(repro, stage / "复现运行记录.json")
        run_entry = next(iter(sorted((workspace / "src").glob("run_all.*"))), None) if (workspace / "src").exists() else None
        (stage / "README_复现说明.md").write_text(
            "# 复现说明\n\n"
            f"- 一键入口：`源程序/{run_entry.name}`\n" if run_entry else "# 复现说明\n\n- 未检测到 `src/run_all.*`，当前支撑材料不可复现。\n",
            encoding="utf-8",
        )
        if ai_details and ai_details.exists():
            shutil.copy2(ai_details, stage / "AI 工具使用详情.pdf")
        included = [path.relative_to(stage).as_posix() for path in iter_files(stage)]
        list_path = stage / "支撑材料文件清单.md"
        list_path.write_text(
            "# 支撑材料文件清单\n\n" + "\n".join(f"- `{item}`" for item in included) + "\n",
            encoding="utf-8",
        )
        included.append("支撑材料文件清单.md")
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in iter_files(stage):
                archive.write(path, path.relative_to(stage).as_posix())
    return sorted(included)


def write_readmes(package: Path, ready: bool, blockers: list[str], print_forms: bool) -> None:
    status = "可进入人工提交步骤" if ready else "候选交付包，当前不可直接提交"
    (package / "README_交付说明.md").write_text(
        "# CUMCM 交付包\n\n"
        f"- 状态：**{status}**\n"
        "- `01_正式提交/`：电子提交候选，只包含参赛论文与支撑材料。\n"
        "- `02_纸质版准备/`：打印装订材料；是否提交及时间以当前赛年赛区通知为准。\n"
        "- `03_复现与审查留档/`：队内复核资料，不得整体上传竞赛系统。\n"
        "- `04_本地哈希核验/`：本地 MD5/SHA-256；官方客户端生成的 MD5 才是提交依据。\n"
        "- 正式生成/上传 MD5 后，不再打开、自动保存或编辑冻结副本。\n",
        encoding="utf-8",
    )
    (package / "02_纸质版准备" / "打印装订说明.md").write_text(
        "# 打印装订说明\n\n"
        "按当前赛年官方通知执行。2026 基线顺序为：承诺书、编号专用页、论文；A4、四边至少 2.5 cm、左侧装订。"
        + ("当前目录已包含两张用户提供的专用页。\n" if print_forms else "当前目录缺少一张或两张官方专用页，纸质版尚未就绪。\n"),
        encoding="utf-8",
    )
    marker = package / "NOT_SUBMISSION_READY.md"
    if not ready:
        marker.write_text(
            "# 不可直接提交\n\n以下硬门尚未通过：\n\n" + "\n".join(f"- `{item}`" for item in blockers) + "\n",
            encoding="utf-8",
        )


def package_generic(workspace: Path, output_root: Path, competition: str, state: dict[str, Any], state_path: Path) -> int:
    package = next_version(output_root, f"{competition.upper()}_最终交付包")
    paper_dir = package / "01_最终论文"
    repro_dir = package / "02_源码结果与复现"
    qa_dir = package / "03_QA与清单"
    for directory in (paper_dir, repro_dir, qa_dir):
        directory.mkdir(parents=True, exist_ok=False)
    copy_tree(workspace / "paper_output", paper_dir)
    for source_name in ("src", "results", "figures", "analysis", "data_processed"):
        copy_tree(workspace / source_name, repro_dir / source_name)
    for name in ("requirements.txt", "environment.yml", "pyproject.toml", "renv.lock"):
        source = workspace / name
        if source.exists() and source.is_file():
            shutil.copy2(source, repro_dir / source.name)
    copy_tree(workspace / "qa", qa_dir / "qa")
    for name in ("DELIVERY_MANIFEST.md",):
        source = workspace / name
        if source.exists():
            shutil.copy2(source, qa_dir / source.name)

    core_report_path = workspace / "qa" / "delivery_validation.json"
    core_report = json.loads(core_report_path.read_text(encoding="utf-8")) if core_report_path.exists() else {}
    ready = core_report.get("submission_ready") is True
    blockers = [] if ready else ["core_delivery_validation"]
    (package / "README_交付说明.md").write_text(
        f"# {competition.upper()} 最终交付包\n\n"
        "- `01_最终论文/`：最终 PDF、可编辑源和参考文献。\n"
        "- `02_源码结果与复现/`：代码、结果、图表、处理后数据和环境。\n"
        "- `03_QA与清单/`：复现、统计、引用、视觉和互盲终审记录。\n",
        encoding="utf-8",
    )
    if blockers:
        (package / "NOT_SUBMISSION_READY.md").write_text(
            "# 不可直接提交\n\n- `core_delivery_validation` 未通过。\n", encoding="utf-8"
        )
    rows = [
        {"path": path.relative_to(package).as_posix(), "bytes": path.stat().st_size, "sha256": digest(path, "sha256")}
        for path in iter_files(package)
        if path.name != "PACKAGE_MANIFEST.json"
    ]
    (package / "PACKAGE_MANIFEST.json").write_text(
        json.dumps(
            {"schema_version": "1.0", "generated_at": utc_now(), "competition": competition, "submission_ready": ready, "blocking_checks": blockers, "files": rows},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    state.setdefault("artifacts", {})["delivery_package"] = str(package)
    stage9 = state.setdefault("stages", {}).setdefault("9", {})
    stage9["submission_ready"] = ready
    stage9["delivery_package_path"] = str(package)
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"submission_ready": ready, "package": str(package), "blocking_checks": blockers}, ensure_ascii=False))
    return 0 if ready else 1


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--output-root", help="Defaults to <workspace>/delivery")
    parser.add_argument("--ai-details", help="Defaults to qa/AI 工具使用详情.pdf")
    parser.add_argument("--commitment", help="Current-year official commitment PDF")
    parser.add_argument("--number-page", help="Current-year official number-page PDF")
    parser.add_argument("--identity-token", action="append", default=[], help="Known private token to scan in extracted paper text")
    args = parser.parse_args()

    workspace = Path(args.workspace).expanduser().resolve()
    state_path = workspace / "state" / "decision_log.json"
    if not state_path.exists():
        print(json.dumps({"status": "blocked", "errors": ["state/decision_log.json missing"]}, ensure_ascii=False))
        return 1
    state = json.loads(state_path.read_text(encoding="utf-8"))
    output_root = Path(args.output_root).expanduser().resolve() if args.output_root else workspace / "delivery"
    competition = state.get("competition")
    if competition not in {"cumcm", "mcm", "diangong"}:
        print(json.dumps({"status": "blocked", "errors": [f"unknown competition: {competition}"]}, ensure_ascii=False))
        return 1
    if competition != "cumcm":
        return package_generic(workspace, output_root, competition, state, state_path)

    package = next_version(output_root, "CUMCM_最终交付包")
    formal = package / "01_正式提交"
    print_dir = package / "02_纸质版准备"
    archive_dir = package / "03_复现与审查留档"
    hash_dir = package / "04_本地哈希核验"
    for directory in (formal, print_dir, archive_dir, hash_dir):
        directory.mkdir(parents=True, exist_ok=False)

    paper_source = workspace / "paper_output" / "paper.pdf"
    paper_target = formal / "参赛论文.pdf"
    if paper_source.exists():
        shutil.copy2(paper_source, paper_target)

    ai_details = Path(args.ai_details).expanduser().resolve() if args.ai_details else workspace / "qa" / "AI 工具使用详情.pdf"
    support_archive = formal / "支撑材料.zip"
    support_files = make_support_archive(workspace, support_archive, ai_details if ai_details.exists() else None)

    for source_name in ("paper_output", "src", "results", "figures", "analysis", "qa"):
        copy_tree(workspace / source_name, archive_dir / source_name)
    for name in ("requirements.txt", "environment.yml", "pyproject.toml", "renv.lock", "DELIVERY_MANIFEST.md"):
        source = workspace / name
        if source.exists() and source.is_file():
            shutil.copy2(source, archive_dir / source.name)

    commitment = Path(args.commitment).expanduser().resolve() if args.commitment else None
    number_page = Path(args.number_page).expanduser().resolve() if args.number_page else None
    if commitment and commitment.exists():
        shutil.copy2(commitment, print_dir / "承诺书.pdf")
    if number_page and number_page.exists():
        shutil.copy2(number_page, print_dir / "编号专用页.pdf")
    print_forms = bool(commitment and commitment.exists() and number_page and number_page.exists())

    compliance = ((state.get("compliance") or {}).get("cumcm") or {})
    ai_state = compliance.get("ai") or {}
    paper_state = compliance.get("paper") or {}
    ai_log_path = workspace / "qa" / "ai_usage_log.json"
    ai_log = load_json_object(ai_log_path)
    page_audit_path = workspace / "qa" / "page_structure_audit.json"
    page_audit = load_json_object(page_audit_path)
    page_audit_ok, page_audit_evidence = page_structure_ok(page_audit)
    page_state_matches = page_audit_ok and all(
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
    algorithm_audit_path = workspace / "qa" / "algorithm_claim_consistency.json"
    algorithm_audit = load_json_object(algorithm_audit_path)
    algorithm_audit_ok = algorithm_audit.get("blocking_count") == 0
    core_report_path = workspace / "qa" / "delivery_validation.json"
    core_report = json.loads(core_report_path.read_text(encoding="utf-8")) if core_report_path.exists() else {}

    first_page_text, first_page_error = extract_pdf_text(paper_target, first_page_only=True) if paper_target.exists() else (None, "paper missing")
    full_text, full_text_error = extract_pdf_text(paper_target, first_page_only=False) if paper_target.exists() else (None, "paper missing")
    normalized = re.sub(r"\s+", "", full_text or "")
    first_normalized = re.sub(r"\s+", "", first_page_text or "")
    ai_statement_pos = normalized.find("本参赛队在竞赛过程中使用了AI工具")
    references_pos = normalized.rfind("参考文献")
    identity_hits = sorted({token for token in args.identity_token if token and token in (full_text or "")})

    checks = [
        check("core_delivery_validation", core_report.get("submission_ready") is True, str(core_report_path)),
        check("paper_pdf", pdf_signature_ok(paper_target), str(paper_target)),
        check("paper_under_20mb", paper_target.exists() and paper_target.stat().st_size <= MAX_CUMCM_BYTES, f"bytes={paper_target.stat().st_size if paper_target.exists() else 'missing'}"),
        check("support_archive", support_archive.exists() and support_archive.stat().st_size > 0, str(support_archive)),
        check("support_under_20mb", support_archive.exists() and support_archive.stat().st_size <= MAX_CUMCM_BYTES, f"bytes={support_archive.stat().st_size if support_archive.exists() else 'missing'}"),
        check("ai_details_pdf", pdf_signature_ok(ai_details), str(ai_details)),
        check("team_led_core_modeling_confirmed", ai_state.get("team_led_core_modeling_confirmed") is True, str(ai_state.get("team_led_core_modeling_confirmed"))),
        check("human_ai_review_confirmed", ai_state.get("human_ai_review_confirmed") is True, str(ai_state.get("human_ai_review_confirmed"))),
        check("ai_log_confirmations_match", ai_log.get("team_led_core_modeling_confirmed") is True and ai_log.get("human_ai_review_confirmed") is True, str(ai_log_path)),
        check("ai_details_fresh", ai_details.exists() and ai_log_path.exists() and ai_details.stat().st_mtime >= ai_log_path.stat().st_mtime, f"details={ai_details.stat().st_mtime if ai_details.exists() else 'missing'}, log={ai_log_path.stat().st_mtime if ai_log_path.exists() else 'missing'}"),
        check("anonymity_confirmed", compliance.get("anonymity_confirmed") is True and not identity_hits, f"state={compliance.get('anonymity_confirmed')}, hits={identity_hits}"),
        check("electronic_first_page_abstract_audited", paper_state.get("electronic_first_page_abstract") is True, str(paper_state.get("electronic_first_page_abstract"))),
        check("page_structure_audit", page_audit_ok, page_audit_evidence),
        check("page_structure_state_matches", paper_state.get("page_structure_audited") is True and page_state_matches, str(page_audit_path)),
        check("algorithm_claim_consistency", algorithm_audit_ok, f"blocking_count={algorithm_audit.get('blocking_count')}, path={algorithm_audit_path}"),
        check("a4_margin_and_pagination_audited", paper_state.get("a4_margin_and_pagination_audited") is True, str(paper_state.get("a4_margin_and_pagination_audited"))),
        check("appendix_and_support_list_audited", paper_state.get("appendix_included") is True and paper_state.get("support_file_list_in_appendix") is True, json.dumps(paper_state, ensure_ascii=False)),
        check("first_page_is_abstract", bool(first_normalized) and "摘要" in first_normalized and "承诺书" not in first_normalized and "编号专用页" not in first_normalized, first_page_error or "text extracted"),
        check("ai_statement_before_references", ai_statement_pos >= 0 and references_pos > ai_statement_pos, f"ai={ai_statement_pos}, references={references_pos}, extraction={full_text_error or 'ok'}"),
    ]
    blockers = [item["name"] for item in checks if item["status"] == "fail"]
    ready = not blockers

    print_forms_ready = print_forms
    write_readmes(package, ready, blockers, print_forms_ready)

    formal_files = [path for path in iter_files(formal)]
    hash_lines = ["# Local hashes only; official client-generated MD5 prevails."]
    for path in formal_files:
        hash_lines.append(f"MD5 {digest(path, 'md5')}  {path.name}")
        hash_lines.append(f"SHA256 {digest(path, 'sha256')}  {path.name}")
    (hash_dir / "LOCAL_HASHES.txt").write_text("\n".join(hash_lines) + "\n", encoding="utf-8")

    report = {
        "schema_version": "1.0",
        "generated_at": utc_now(),
        "ruleset": "cumcm_2026",
        "package": str(package),
        "submission_ready": ready,
        "checks": checks,
        "blocking_checks": blockers,
        "support_archive_files": support_files,
        "paper_text_extraction": {"first_page": first_page_error or "ok", "full": full_text_error or "ok"},
        "print_forms_ready": print_forms_ready,
    }
    qa_report = workspace / "qa" / "cumcm_submission_check.json"
    qa_report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    shutil.copy2(qa_report, archive_dir / "qa" / qa_report.name)

    package_rows = []
    for path in iter_files(package):
        if path.name == "PACKAGE_MANIFEST.json":
            continue
        package_rows.append({
            "path": path.relative_to(package).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": digest(path, "sha256"),
        })
    package_manifest = {
        "schema_version": "1.0",
        "generated_at": utc_now(),
        "submission_ready": ready,
        "blocking_checks": blockers,
        "files": package_rows,
    }
    (package / "PACKAGE_MANIFEST.json").write_text(json.dumps(package_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    state.setdefault("qa", {})["cumcm_submission"] = {
        "status": "pass" if ready else "fail",
        "report": str(qa_report.relative_to(workspace).as_posix()),
        "blocking_checks": blockers,
    }
    state.setdefault("artifacts", {})["delivery_package"] = str(package)
    compliance.setdefault("package", {}).update({"path": str(package), "submission_ready": ready})
    stage9 = state.setdefault("stages", {}).setdefault("9", {})
    stage9["submission_ready"] = ready
    stage9["delivery_package_path"] = str(package)
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"submission_ready": ready, "package": str(package), "blocking_checks": blockers}, ensure_ascii=False))
    return 0 if ready else 1


if __name__ == "__main__":
    sys.exit(main())
