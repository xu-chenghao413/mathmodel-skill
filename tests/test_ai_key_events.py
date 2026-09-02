from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
AI_DISCLOSURE = SKILL_ROOT / "scripts" / "build_ai_disclosure.py"


def base_payload() -> dict:
    return {
        "tools": [{"name": "Codex", "version_or_model": "test-model", "provider": "OpenAI"}],
        "uses": [
            {
                "purpose_and_stage": "模型选择与求解",
                "prompt_method_and_process": "给出约束与候选模型，请求比较适用边界",
                "adoption_and_manual_changes": "参赛队独立推导后采用其中一个候选并重写求解流程",
                "verification": "与基线比较，并用边界样例和独立代码复算",
            }
        ],
        "team_led_core_modeling_confirmed": True,
        "human_ai_review_confirmed": True,
    }


def key_event() -> dict:
    return {
        "prompt_summary": "比较 A 与 B 模型，约束为运行时间不超过十分钟",
        "output_summary": "建议采用 A，并指出 B 在小样本下不稳定",
        "team_decision": "采纳 A 的结构，不采纳未经证明的参数建议",
        "manual_changes": "重新推导目标函数，并自行实现收敛判据",
        "verification": "消融试验、边界样例与三次固定种子复算均通过",
        "affected_artifacts": ["src/solve.py", "paper_output/paper.tex"],
    }


class AIKeyEventsTest(unittest.TestCase):
    def run_builder(self, payload: dict) -> tuple[subprocess.CompletedProcess[str], str]:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            log_path = workspace / "ai_usage_log.json"
            output_path = workspace / "AI 工具使用详情.pdf"
            log_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run(
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
            tex_path = output_path.with_suffix(".tex")
            tex = tex_path.read_text(encoding="utf-8") if tex_path.exists() else ""
            return result, tex

    def test_structured_nested_events_render_every_summary_field(self) -> None:
        payload = base_payload()
        payload["recording_scope"] = "key_material_interactions"
        payload["recording_mode"] = "summary-only"
        payload["uses"][0]["key_interactions"] = [key_event()]

        result, tex = self.run_builder(payload)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(r"key\_material\_interactions", tex)
        self.assertIn("summary-only", tex)
        self.assertIn("同一事件的多轮交互已聚合", tex)
        for value in key_event().values():
            if isinstance(value, list):
                for item in value:
                    self.assertIn(item.replace("_", r"\_"), tex)
            else:
                self.assertIn(value, tex)
        self.assertIn("正式文件不转录完整聊天", tex)

    def test_top_level_events_are_rendered_not_dropped(self) -> None:
        payload = base_payload()
        payload["recording_scope"] = "key_material_interactions"
        event = key_event()
        event["purpose_and_stage"] = "最终一致性审查"
        payload["key_interactions"] = [event]

        result, tex = self.run_builder(payload)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("补充关键事件 1：最终一致性审查", tex)
        self.assertIn(event["output_summary"], tex)
        # 参赛队确认状态属于内部交付门控信息，不写入对外披露
        self.assertNotIn("参赛队确认状态", tex)

    def test_empty_structured_fields_are_blocked(self) -> None:
        payload = base_payload()
        payload["recording_scope"] = "key_material_interactions"
        event = key_event()
        event["output_summary"] = "  "
        event["affected_artifacts"] = []
        payload["uses"][0]["key_interactions"] = [event]

        result, tex = self.run_builder(payload)

        self.assertEqual(result.returncode, 1)
        self.assertEqual(tex, "")
        response = json.loads(result.stdout)
        self.assertTrue(any("output_summary is empty" in error for error in response["errors"]))
        self.assertTrue(any("affected_artifacts is empty" in error for error in response["errors"]))

    def test_key_events_require_explicit_scope_and_reject_full_chat(self) -> None:
        payload = base_payload()
        event = key_event()
        event["raw_transcript"] = "User: ... Assistant: ..."
        payload["uses"][0]["key_interactions"] = [event]

        result, _ = self.run_builder(payload)

        self.assertEqual(result.returncode, 1)
        response = json.loads(result.stdout)
        self.assertTrue(any("recording_scope must be key_material_interactions" in error for error in response["errors"]))
        self.assertTrue(any("must not contain a full chat transcript" in error for error in response["errors"]))

    def test_legacy_four_field_use_still_renders_without_missing_tone(self) -> None:
        result, tex = self.run_builder(base_payload())

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("模型选择与求解", tex)
        self.assertIn("用途级摘要（兼容旧记录）", tex)
        self.assertNotIn("未附典型交互", tex)


if __name__ == "__main__":
    unittest.main()
