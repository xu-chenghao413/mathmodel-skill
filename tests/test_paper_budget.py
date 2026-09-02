from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
PLANNER_PATH = SKILL_ROOT / "scripts" / "plan_paper_budget.py"
SPEC = importlib.util.spec_from_file_location("plan_paper_budget", PLANNER_PATH)
assert SPEC is not None and SPEC.loader is not None
PLANNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PLANNER)


def equal_questions(count: int = 4) -> list[dict[str, object]]:
    return [
        {
            "id": f"Q{index}",
            "importance": 3,
            "scenario_load": 3,
            "derivation_depth": 3,
            "novelty_evidence": 3,
            "validation_load": 3,
            "downstream_reuse": 3,
            "reuse_discount": 0,
        }
        for index in range(1, count + 1)
    ]


class PaperBudgetTest(unittest.TestCase):
    def test_all_three_profiles_have_separate_balanced_accounting(self) -> None:
        expected_targets = {"compact": 26, "balanced": 27, "dense": 28}
        for profile, expected in expected_targets.items():
            with self.subTest(profile=profile):
                budget = PLANNER.build_budget({"profile": profile, "questions": equal_questions()})
                self.assertEqual(budget["abstract"]["pages"], 1)
                self.assertTrue(budget["abstract"]["counted_separately"])
                self.assertEqual(budget["official_body"]["target_pages"], expected)
                self.assertLessEqual(budget["official_body"]["target_pages"], 30)
                self.assertTrue(budget["official_body"]["accounting"]["sum_matches_target"])
                self.assertIsNone(budget["appendix"]["page_cap"])
                self.assertEqual(budget["appendix"]["allocation_policy"], "completeness_driven")

    def test_explicit_target_over_30_is_rejected_by_cli(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            input_path = temp_path / "input.json"
            output_path = temp_path / "analysis" / "page_budget.json"
            input_path.write_text(
                json.dumps({"profile": "dense", "official_body_target": 31, "questions": equal_questions()}),
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, str(PLANNER_PATH), "--input", str(input_path), "--output", str(output_path)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("exceeds", result.stderr)
            self.assertFalse(output_path.exists())

    def test_nonuniform_weights_change_question_pages_and_totals_still_match(self) -> None:
        questions = equal_questions(3)
        questions[0].update(
            {
                "importance": 5,
                "scenario_load": 5,
                "derivation_depth": 5,
                "novelty_evidence": 5,
                "validation_load": 5,
                "downstream_reuse": 5,
                "reuse_discount": 0,
            }
        )
        questions[1].update(
            {
                "importance": 1,
                "scenario_load": 1,
                "derivation_depth": 1,
                "novelty_evidence": 1,
                "validation_load": 1,
                "downstream_reuse": 1,
                "reuse_discount": 0.8,
            }
        )
        budget = PLANNER.build_budget(
            {"profile": "balanced", "official_body_target": 27, "questions": questions}
        )
        plans = {item["id"]: item for item in budget["official_body"]["questions"]}
        self.assertGreater(plans["Q1"]["pages"], plans["Q2"]["pages"])
        accounting = budget["official_body"]["accounting"]
        self.assertEqual(accounting["question_pages_sum"], accounting["core_pages"])
        self.assertEqual(accounting["section_pages_sum"], 27)
        self.assertTrue(accounting["sum_matches_target"])
        self.assertIn("under_12_percent", plans["Q2"]["justification_flags"])


if __name__ == "__main__":
    unittest.main()
