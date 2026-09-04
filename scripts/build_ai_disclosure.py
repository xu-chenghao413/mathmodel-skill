#!/usr/bin/env python3
"""Build the CUMCM 2026 AI usage disclosure PDF from a structured audit log.

The preferred schema records only interactions that materially affected the
submission.  Each ``key_interactions`` item is a summary of one decision event;
multiple chat turns serving the same event should be aggregated before this
script is called.  Legacy four-field ``uses`` entries remain supported.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    from scripts.console import configure_stdio
except ImportError:
    from console import configure_stdio


REQUIRED_USE_FIELDS = (
    "purpose_and_stage",
    "prompt_method_and_process",
    "adoption_and_manual_changes",
    "verification",
)

REQUIRED_KEY_INTERACTION_FIELDS = (
    "prompt_summary",
    "output_summary",
    "team_decision",
    "manual_changes",
    "verification",
    "affected_artifacts",
)

PROHIBITED_TRANSCRIPT_FIELDS = (
    "raw_transcript",
    "chat_transcript",
    "full_chat",
    "full_prompt",
    "full_response",
)

RECORDING_SCOPE = "key_material_interactions"
RECORDING_MODE = "summary-only"


def latex_escape(value: Any) -> str:
    text = str(value)
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in text)


def _has_content(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple)):
        return bool(value) and all(_has_content(item) for item in value)
    if isinstance(value, dict):
        return bool(value)
    return value is not None


def _validate_key_interaction(
    interaction: Any,
    label: str,
    errors: list[str],
    *,
    require_purpose: bool,
) -> None:
    if not isinstance(interaction, dict):
        errors.append(f"{label} must be an object")
        return
    if require_purpose and not _has_content(interaction.get("purpose_and_stage")):
        errors.append(f"{label}.purpose_and_stage is empty")
    for key in REQUIRED_KEY_INTERACTION_FIELDS[:-1]:
        value = interaction.get(key)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{label}.{key} is empty")
    artifacts = interaction.get("affected_artifacts")
    if not _has_content(artifacts):
        errors.append(f"{label}.affected_artifacts is empty")
    elif isinstance(artifacts, str):
        pass
    elif isinstance(artifacts, (list, tuple)):
        if not all(isinstance(item, str) and item.strip() for item in artifacts):
            errors.append(f"{label}.affected_artifacts contains an empty or non-text item")
    else:
        errors.append(f"{label}.affected_artifacts must be a string or a non-empty list")
    for key in PROHIBITED_TRANSCRIPT_FIELDS:
        if _has_content(interaction.get(key)):
            errors.append(
                f"{label}.{key} must not contain a full chat transcript; "
                "summarize it in prompt_summary/output_summary"
            )


def load_and_validate(path: Path) -> tuple[dict[str, Any], list[str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    errors: list[str] = []
    tools = payload.get("tools") or []
    uses = payload.get("uses") or []
    if not isinstance(tools, list) or not tools:
        errors.append("tools is empty")
    for index, tool in enumerate(tools, start=1):
        if not isinstance(tool, dict):
            errors.append(f"tools[{index}] must be an object")
            continue
        for key in ("name", "version_or_model"):
            if not str(tool.get(key, "")).strip():
                errors.append(f"tools[{index}].{key} is empty")
    if not isinstance(uses, list) or not uses:
        errors.append("uses is empty")
        uses = []
    has_key_interactions = False
    for index, use in enumerate(uses, start=1):
        if not isinstance(use, dict):
            errors.append(f"uses[{index}] must be an object")
            continue
        for key in REQUIRED_USE_FIELDS:
            if not str(use.get(key, "")).strip():
                errors.append(f"uses[{index}].{key} is empty")
        interactions = use.get("key_interactions") or []
        if not isinstance(interactions, list):
            errors.append(f"uses[{index}].key_interactions must be a list")
            interactions = []
        if interactions:
            has_key_interactions = True
        for event_index, interaction in enumerate(interactions, start=1):
            _validate_key_interaction(
                interaction,
                f"uses[{index}].key_interactions[{event_index}]",
                errors,
                require_purpose=False,
            )

        legacy_examples = use.get("typical_interactions") or []
        if not isinstance(legacy_examples, list):
            errors.append(f"uses[{index}].typical_interactions must be a list")
        else:
            for example_index, example in enumerate(legacy_examples, start=1):
                if not _has_content(example):
                    errors.append(f"uses[{index}].typical_interactions[{example_index}] is empty")

    top_level_interactions = payload.get("key_interactions") or []
    if not isinstance(top_level_interactions, list):
        errors.append("key_interactions must be a list")
        top_level_interactions = []
    if top_level_interactions:
        has_key_interactions = True
    for event_index, interaction in enumerate(top_level_interactions, start=1):
        _validate_key_interaction(
            interaction,
            f"key_interactions[{event_index}]",
            errors,
            require_purpose=True,
        )

    recording_scope = payload.get("recording_scope")
    if has_key_interactions and recording_scope != RECORDING_SCOPE:
        errors.append(f"recording_scope must be {RECORDING_SCOPE} when key_interactions are present")
    elif recording_scope is not None and recording_scope != RECORDING_SCOPE:
        errors.append(f"recording_scope must be {RECORDING_SCOPE}")

    recording_mode = payload.get("recording_mode", RECORDING_MODE)
    if recording_mode != RECORDING_MODE:
        errors.append(f"recording_mode must be {RECORDING_MODE}")
    return payload, errors


def _artifact_text(value: Any) -> str:
    if isinstance(value, (list, tuple)):
        return "、".join(str(item) for item in value)
    return str(value)


def _artifact_latex(value: Any) -> str:
    """Escape artifact paths while preserving safe line-break opportunities."""
    items = value if isinstance(value, (list, tuple)) else [value]
    rendered: list[str] = []
    for item in items:
        escaped = latex_escape(item)
        escaped = escaped.replace("/", "/\\allowbreak{}")
        escaped = escaped.replace(r"\_", r"\_\allowbreak{}")
        escaped = escaped.replace(":", r":\allowbreak{}")
        rendered.append(escaped)
    return r"、\allowbreak{}".join(rendered)


def _render_key_interaction(interaction: dict[str, Any], heading: str) -> str:
    return rf"""\subsubsection*{{{latex_escape(heading)}}}
\textbf{{提示目标与约束摘要：}}{latex_escape(interaction['prompt_summary'])}

\textbf{{AI 输出摘要：}}{latex_escape(interaction['output_summary'])}

\textbf{{参赛队决定：}}{latex_escape(interaction['team_decision'])}

\textbf{{人工修改：}}{latex_escape(interaction['manual_changes'])}

\textbf{{核验方式与结果：}}{latex_escape(interaction['verification'])}

% Keep a machine-readable, line-break-free copy for downstream validators.
% affected_artifacts: {latex_escape(_artifact_text(interaction['affected_artifacts']))}
\textbf{{受影响交付物：}}{_artifact_latex(interaction['affected_artifacts'])}
"""


def render_tex(payload: dict[str, Any]) -> str:
    tool_rows = []
    for tool in payload.get("tools", []):
        tool_rows.append(
            f"{latex_escape(tool['name'])} & {latex_escape(tool['version_or_model'])} & "
            f"{latex_escape(tool.get('provider', ''))} \\\\"
        )
    use_blocks = []
    for index, use in enumerate(payload.get("uses", []), start=1):
        examples = use.get("typical_interactions") or []
        example_block = ""
        if examples:
            example_text = "；".join(latex_escape(item) for item in examples)
            example_block = rf"""
\textbf{{代表性交互摘要（兼容旧记录）：}}{example_text}
"""
        interactions = use.get("key_interactions") or []
        if interactions:
            interaction_blocks = "\n".join(
                _render_key_interaction(interaction, f"关键事件 {event_index}（同一事件的多轮交互已聚合）")
                for event_index, interaction in enumerate(interactions, start=1)
            )
            scope = latex_escape(payload.get("recording_scope", RECORDING_SCOPE))
            mode = latex_escape(payload.get("recording_mode", RECORDING_MODE))
            detail_block = rf"""
\textbf{{记录范围：}}{scope}；\textbf{{记录模式：}}{mode}

\textbf{{记录粒度：}}关键且对成果有实质影响的事件摘要；同一事件的多轮交互已聚合，正式文件不转录完整聊天。

{interaction_blocks}
"""
        else:
            detail_block = r"""
\textbf{记录粒度：}用途级摘要（兼容旧记录）；正式文件不转录完整聊天。
"""
        use_blocks.append(
            rf"""\subsection*{{{index}. {latex_escape(use['purpose_and_stage'])}}}
\textbf{{主要提示方式与使用过程：}}{latex_escape(use['prompt_method_and_process'])}

\textbf{{采纳与人工修改：}}{latex_escape(use['adoption_and_manual_changes'])}

\textbf{{人工核验：}}{latex_escape(use['verification'])}

{detail_block}
{example_block}
"""
        )
    top_level_blocks = []
    for index, interaction in enumerate(payload.get("key_interactions") or [], start=1):
        heading = f"补充关键事件 {index}：{interaction['purpose_and_stage']}"
        top_level_blocks.append(_render_key_interaction(interaction, heading))
    top_level_section = ""
    if top_level_blocks:
        top_level_section = rf"""
\section*{{三、补充关键事件记录}}
以下逐项列出用途级摘要之外的关键事件；每项均按一次实质性决策事件汇总，同一事件的多轮交互不逐轮转录。

{chr(10).join(top_level_blocks)}
"""
    # 参赛队确认状态（team_led_core_modeling_confirmed / human_ai_review_confirmed /
    # anonymity_confirmed）属于内部交付门控信息，不写入对外披露的《AI 工具使用详情》；
    # 其状态仅记录于 state/decision_log.json，由 validate_delivery.py 校验。
    return rf"""\documentclass[12pt,a4paper]{{ctexart}}
\usepackage[top=2.5cm,bottom=2.5cm,left=2.5cm,right=2.5cm]{{geometry}}
\usepackage{{booktabs,longtable,array}}
\setlength{{\parindent}}{{2em}}
\begin{{document}}
\begin{{center}}
{{\Large\bfseries AI 工具使用详情}}
\end{{center}}

\section*{{一、所用 AI 工具}}
\begin{{longtable}}{{p{{0.30\textwidth}}p{{0.30\textwidth}}p{{0.25\textwidth}}}}
\toprule
工具名称 & 版本或型号 & 开发机构/公司 \\
\midrule
{chr(10).join(tool_rows)}
\bottomrule
\end{{longtable}}

\section*{{二、具体用途、过程与核验}}
{chr(10).join(use_blocks)}

{top_level_section}

\end{{document}}
"""


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", required=True, help="qa/ai_usage_log.json")
    parser.add_argument("--output", required=True, help="AI 工具使用详情.pdf")
    parser.add_argument("--no-compile", action="store_true", help="Only write the adjacent .tex file")
    args = parser.parse_args()

    log_path = Path(args.log).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    if not log_path.exists():
        print(json.dumps({"status": "blocked", "errors": [f"missing log: {log_path}"]}, ensure_ascii=False))
        return 1
    try:
        payload, errors = load_and_validate(log_path)
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "blocked", "errors": [str(exc)]}, ensure_ascii=False))
        return 1
    if errors:
        print(json.dumps({"status": "blocked", "errors": errors}, ensure_ascii=False))
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    tex_path = output_path.with_suffix(".tex")
    tex_path.write_text(render_tex(payload), encoding="utf-8")
    if args.no_compile:
        print(json.dumps({"status": "tex_ready", "tex": str(tex_path)}, ensure_ascii=False))
        return 0

    engine = shutil.which("xelatex")
    if engine is None:
        print(json.dumps({"status": "blocked", "errors": ["xelatex not found"], "tex": str(tex_path)}, ensure_ascii=False))
        return 1
    for _ in range(2):
        run = subprocess.run(
            [engine, "-interaction=nonstopmode", "-halt-on-error", tex_path.name],
            cwd=tex_path.parent,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if run.returncode != 0:
            print(json.dumps({"status": "blocked", "errors": [run.stdout[-2000:], run.stderr[-1000:]]}, ensure_ascii=False))
            return 1
    built_pdf = tex_path.with_suffix(".pdf")
    if not built_pdf.exists() or built_pdf.stat().st_size < 5000:
        print(json.dumps({"status": "blocked", "errors": ["PDF was not produced"]}, ensure_ascii=False))
        return 1
    if built_pdf.resolve() != output_path:
        shutil.copy2(built_pdf, output_path)
    print(json.dumps({"status": "ready", "pdf": str(output_path), "tex": str(tex_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    configure_stdio()
    sys.exit(main())
