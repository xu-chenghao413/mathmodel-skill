from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = SKILL_ROOT / "scripts" / "bootstrap_run.py"
VALIDATE = SKILL_ROOT / "scripts" / "validate_delivery.py"
RENDER = SKILL_ROOT / "scripts" / "render_paper.py"
SCORE = SKILL_ROOT / "scripts" / "score_artifact.py"
AI_DISCLOSURE = SKILL_ROOT / "scripts" / "build_ai_disclosure.py"
PACKAGER = SKILL_ROOT / "scripts" / "package_delivery.py"


class AutopilotScriptsTest(unittest.TestCase):
    def test_cumcm_scaffold_uses_2026_electronic_layout(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace_root = Path(temp)
            paper_workspace = workspace_root / "paper_workspace"
            paper_output = workspace_root / "paper_output"
            paper_workspace.mkdir()
            names = (
                "01_abstract.md",
                "02_problem_restate.md",
                "03_analysis.md",
                "04_assumptions.md",
                "05_notation.md",
                "06_models.md",
                "07_sensitivity.md",
                "08_evaluation.md",
                "09_ai_declaration.md",
                "10_references.md",
                "11_appendix.md",
            )
            for name in names:
                content = "本参赛队在竞赛过程中使用了 AI 工具" if name == "09_ai_declaration.md" else name
                paper_workspace.joinpath(name).write_text(content, encoding="utf-8")
            rendered = subprocess.run(
                [
                    sys.executable,
                    str(RENDER),
                    "--competition",
                    "cumcm",
                    "--workspace",
                    str(paper_workspace),
                    "--output-dir",
                    str(paper_output),
                    "--no-pandoc",
                    "--no-compile",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(rendered.returncode, 0, rendered.stdout + rendered.stderr)
            tex = paper_output.joinpath("paper.tex").read_text(encoding="utf-8")
            self.assertIn("withoutpreface", tex)
            self.assertNotIn("\\tableofcontents", tex)
            self.assertLess(tex.index("AI 工具使用声明"), tex.index("参考文献"))

    def test_render_prefers_complete_paper_tex(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace_root = Path(temp)
            paper_workspace = workspace_root / "paper_workspace"
            paper_output = workspace_root / "paper_output"
            paper_workspace.mkdir()
            paper_workspace.joinpath("paper.tex").write_text(
                "\\documentclass{article}\\begin{document}Complete\\end{document}",
                encoding="utf-8",
            )
            paper_workspace.joinpath("references.bib").write_text("@book{x,title={X}}", encoding="utf-8")
            rendered = subprocess.run(
                [
                    sys.executable,
                    str(RENDER),
                    "--competition",
                    "mcm",
                    "--workspace",
                    str(paper_workspace),
                    "--output-dir",
                    str(paper_output),
                    "--no-pandoc",
                    "--no-compile",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                check=False,
            )
            self.assertEqual(rendered.returncode, 0, rendered.stdout + rendered.stderr)
            self.assertIn("Complete", paper_output.joinpath("paper.tex").read_text(encoding="utf-8"))
            self.assertTrue(paper_output.joinpath("references.bib").exists())

    def test_bootstrap_and_valid_delivery(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            problem = workspace / "2026-CUMCM-A.txt"
            problem.write_text("全国大学生数学建模竞赛 A 题", encoding="utf-8")
            boot = subprocess.run(
                [sys.executable, str(BOOTSTRAP), "--workspace", str(workspace), "--problem", str(problem)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(boot.returncode, 0, boot.stdout + boot.stderr)
            state = json.loads((workspace / "state" / "decision_log.json").read_text(encoding="utf-8"))
            self.assertEqual(state["competition"], "cumcm")
            self.assertEqual(state["execution"]["interaction_mode"], "autopilot")
            self.assertIsInstance(state["execution"]["nature_router"]["available"], list)

            scored = subprocess.run(
                [
                    sys.executable,
                    str(SCORE),
                    "--stage",
                    "1",
                    "--critique",
                    str(SKILL_ROOT / "tests" / "fixtures" / "test_critique_good.json"),
                    "--decision-log",
                    str(workspace / "state" / "decision_log.json"),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                check=False,
            )
            self.assertEqual(scored.returncode, 0, (scored.stdout or "") + (scored.stderr or ""))
            state_path = workspace / "state" / "decision_log.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["stages"]["9"]["panel_scores"]["aggregate_v1"] = {"blocking_open": 0}
            state["compliance"]["cumcm"]["paper"].update(
                {
                    "electronic_first_page_abstract": True,
                    "pdf_total_pages": 38,
                    "abstract_pages": 1,
                    "official_body_start_pdf_page": 2,
                    "official_body_end_pdf_page": 28,
                    "official_body_pages": 27,
                    "appendix_start_pdf_page": 29,
                    "appendix_pages": 10,
                    "page_structure_audited": True,
                    "a4_margin_and_pagination_audited": True,
                    "appendix_included": True,
                    "support_file_list_in_appendix": True,
                }
            )
            state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

            (workspace / "paper_output" / "paper.pdf").write_bytes(b"%PDF-" + b"0" * 6000)
            (workspace / "paper_output" / "paper.tex").write_text(
                "AI 工具使用声明\n本参赛队在竞赛过程中使用了 AI 工具。\n"
                "参考文献\n\\centerline{\\heiti 附录}\n"
                "\\renewcommand{\\thesection}{附录\\Alph{section}}\n"
                "支撑材料文件列表\n完整源程序代码\n计算结果详表\n",
                encoding="utf-8",
            )
            (workspace / "paper_output" / "references.bib").write_text("@book{x,title={X}}", encoding="utf-8")
            (workspace / "src" / "run_all.py").write_text("print('ok')", encoding="utf-8")
            (workspace / "requirements.txt").write_text("numpy==1.0\n", encoding="utf-8")
            (workspace / "results" / "metrics.json").write_text('{"score": 1}', encoding="utf-8")
            (workspace / "figures" / "figure_1.svg").write_text("<svg></svg>", encoding="utf-8")
            (workspace / "analysis" / "page_budget.json").write_text(
                json.dumps(
                    {
                        "official_body": {"target_pages": 27},
                        "appendix": {"allocation_policy": "completeness_driven", "page_cap": None},
                    }
                ),
                encoding="utf-8",
            )
            (workspace / "analysis" / "novelty_ledger.json").write_text(
                json.dumps({"unsupported_claims": 0, "claims": []}), encoding="utf-8"
            )
            for name in (
                "statistics_audit.md",
                "citation_audit.md",
                "consistency_sweep.md",
                "visual_qa.md",
                "reviewer_synthesis.md",
            ):
                (workspace / "qa" / name).write_text("pass\n", encoding="utf-8")
            for reviewer_id in (1, 2, 3):
                (workspace / "qa" / f"reviewer_{reviewer_id}.json").write_text(
                    json.dumps({"reviewer": f"R{reviewer_id}", "major_concerns": []}),
                    encoding="utf-8",
                )
            (workspace / "qa" / "reproducibility.json").write_text(
                json.dumps({"command": "python src/run_all.py", "exit_code": 0, "seed": 42}),
                encoding="utf-8",
            )
            (workspace / "qa" / "algorithm_claim_consistency.json").write_text(
                json.dumps({"blocking_count": 0, "methods": []}), encoding="utf-8"
            )
            (workspace / "qa" / "page_structure_audit.json").write_text(
                json.dumps(
                    {
                        "pdf_total_pages": 38,
                        "abstract_pages": 1,
                        "official_body_start_pdf_page": 2,
                        "official_body_end_pdf_page": 28,
                        "official_body_pages": 27,
                        "appendix_start_pdf_page": 29,
                        "appendix_pages": 10,
                    }
                ),
                encoding="utf-8",
            )
            ai_log = {
                "schema_version": "1.1",
                "recording_scope": "key_material_interactions",
                "recording_mode": "summary-only",
                "tools": [{"name": "OpenAI Codex", "version_or_model": "test-model", "provider": "OpenAI"}],
                "uses": [
                    {
                        "purpose_and_stage": "代码调试",
                        "prompt_method_and_process": "提供错误摘要并请求定位",
                        "adoption_and_manual_changes": "人工修改后采用",
                        "verification": "重新运行测试并核对结果",
                    }
                ],
                "team_led_core_modeling_confirmed": True,
                "human_ai_review_confirmed": True,
            }
            (workspace / "qa" / "ai_usage_log.json").write_text(
                json.dumps(ai_log, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            (workspace / "qa" / "AI 工具使用详情.pdf").write_bytes(b"%PDF-" + b"1" * 6000)

            validation = subprocess.run(
                [sys.executable, str(VALIDATE), "--workspace", str(workspace)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(validation.returncode, 0, validation.stdout + validation.stderr)
            report = json.loads((workspace / "qa" / "delivery_validation.json").read_text(encoding="utf-8"))
            self.assertTrue(report["submission_ready"])
            self.assertTrue((workspace / "DELIVERY_MANIFEST.md").exists())

            state = json.loads(state_path.read_text(encoding="utf-8"))
            cumcm = state["compliance"]["cumcm"]
            cumcm["ai"]["team_led_core_modeling_confirmed"] = True
            cumcm["ai"]["human_ai_review_confirmed"] = True
            cumcm["anonymity_confirmed"] = True
            cumcm["paper"].update(
                {
                    "electronic_first_page_abstract": True,
                    "pdf_total_pages": 38,
                    "abstract_pages": 1,
                    "official_body_start_pdf_page": 2,
                    "official_body_end_pdf_page": 28,
                    "official_body_pages": 27,
                    "appendix_start_pdf_page": 29,
                    "appendix_pages": 10,
                    "page_structure_audited": True,
                    "a4_margin_and_pagination_audited": True,
                    "appendix_included": True,
                    "support_file_list_in_appendix": True,
                }
            )
            state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

            fake_bin = workspace / "fake_bin"
            fake_bin.mkdir()
            fake_pdftotext = fake_bin / ("pdftotext.cmd" if os.name == "nt" else "pdftotext")
            # Windows 下不得用 echo 输出中文（BOM/代码页会把 UTF-8 中文转坏），
            # 改用 type 直读 UTF-8 文本文件，保证管道字节原样透传。
            fake_text = fake_bin / "pdftotext_out.txt"
            fake_text.write_text(
                "摘要\nAI 工具使用声明\n本参赛队在竞赛过程中使用了 AI 工具\n参考文献\n",
                encoding="utf-8",
            )
            if os.name == "nt":
                fake_pdftotext.write_text(
                    '@echo off\r\ntype "%~dp0pdftotext_out.txt"\r\n',
                    encoding="ascii",
                )
            else:
                fake_pdftotext.write_text(
                    "#!/bin/sh\nprintf '摘要\\nAI 工具使用声明\\n本参赛队在竞赛过程中使用了 AI 工具\\n参考文献\\n'\n",
                    encoding="utf-8",
                )
                fake_pdftotext.chmod(0o755)
            pack = subprocess.run(
                [sys.executable, str(PACKAGER), "--workspace", str(workspace)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env={**os.environ, "PATH": str(fake_bin) + os.pathsep + os.environ.get("PATH", "")},
                check=False,
            )
            self.assertEqual(pack.returncode, 0, pack.stdout + pack.stderr)
            payload = json.loads(pack.stdout)
            package_path = Path(payload["package"])
            self.assertTrue((package_path / "01_正式提交" / "参赛论文.pdf").exists())
            self.assertTrue((package_path / "01_正式提交" / "支撑材料.zip").exists())
            self.assertTrue((package_path / "PACKAGE_MANIFEST.json").exists())
            self.assertFalse((package_path / "NOT_SUBMISSION_READY.md").exists())

    def test_ai_disclosure_validates_and_renders_tex(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            log_path = workspace / "ai_usage_log.json"
            output_path = workspace / "AI 工具使用详情.pdf"
            log_path.write_text(
                json.dumps(
                    {
                        "tools": [{"name": "Codex", "version_or_model": "test-model", "provider": "OpenAI"}],
                        "uses": [
                            {
                                "purpose_and_stage": "模型候选比较",
                                "prompt_method_and_process": "输入约束摘要并比较候选",
                                "adoption_and_manual_changes": "只采纳经人工推导验证的部分",
                                "verification": "用独立代码和边界样例核验",
                            }
                        ],
                        "team_led_core_modeling_confirmed": False,
                        "human_ai_review_confirmed": False,
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            rendered = subprocess.run(
                [
                    sys.executable,
                    str(AI_DISCLOSURE),
                    "--log",
                    str(log_path),
                    "--output",
                    str(output_path),
                    "--no-compile",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(rendered.returncode, 0, rendered.stdout + rendered.stderr)
            tex = output_path.with_suffix(".tex").read_text(encoding="utf-8")
            self.assertIn("模型候选比较", tex)
            # 参赛队确认状态不写入披露文本
            self.assertNotIn("尚未由参赛队确认", tex)

    def test_non_cumcm_delivery_is_also_one_folder(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            for name in ("state", "qa", "paper_output", "src", "results", "figures"):
                (workspace / name).mkdir()
            (workspace / "state" / "decision_log.json").write_text(
                json.dumps({"competition": "mcm", "stages": {"9": {}}, "artifacts": {}}), encoding="utf-8"
            )
            (workspace / "qa" / "delivery_validation.json").write_text(
                json.dumps({"submission_ready": True}), encoding="utf-8"
            )
            (workspace / "paper_output" / "paper.pdf").write_bytes(b"%PDF-" + b"0" * 6000)
            (workspace / "paper_output" / "paper.tex").write_text("complete", encoding="utf-8")
            (workspace / "src" / "run_all.py").write_text("print('ok')", encoding="utf-8")
            packaged = subprocess.run(
                [sys.executable, str(PACKAGER), "--workspace", str(workspace)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(packaged.returncode, 0, packaged.stdout + packaged.stderr)
            package = Path(json.loads(packaged.stdout)["package"])
            self.assertTrue((package / "01_最终论文" / "paper.pdf").exists())
            self.assertTrue((package / "02_源码结果与复现" / "src" / "run_all.py").exists())
            self.assertTrue((package / "PACKAGE_MANIFEST.json").exists())

    def test_ambiguous_autopilot_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            problem = workspace / "problem.txt"
            problem.write_text("generic modeling task", encoding="utf-8")
            boot = subprocess.run(
                [sys.executable, str(BOOTSTRAP), "--workspace", str(workspace), "--problem", str(problem)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(boot.returncode, 1)
            payload = json.loads(boot.stdout)
            self.assertIn("competition_template_unresolved", payload["blockers"])

            resumed = subprocess.run(
                [
                    sys.executable,
                    str(BOOTSTRAP),
                    "--workspace",
                    str(workspace),
                    "--problem",
                    str(problem),
                    "--competition",
                    "mcm",
                    "--resume",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(resumed.returncode, 0, resumed.stdout + resumed.stderr)
            resumed_payload = json.loads(resumed.stdout)
            self.assertEqual(resumed_payload["competition"], "mcm")
            self.assertNotIn("competition_template_unresolved", resumed_payload["blockers"])


if __name__ == "__main__":
    unittest.main()
