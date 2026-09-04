from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_sbom import build
from scripts.status import load_snapshot, snapshot


class ProjectToolTests(unittest.TestCase):
    def test_sbom_contains_hashed_source_components(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "source"
            source.mkdir()
            (source / "hello.txt").write_text("hello\n", encoding="utf-8")
            output = source / "dist" / "demo.sbom.json"

            build(source, output, "demo", "1.0.0")

            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["bomFormat"], "CycloneDX")
            self.assertEqual(payload["metadata"]["component"]["version"], "1.0.0")
            component = next(item for item in payload["components"] if item["name"] == "hello.txt")
            self.assertEqual(component["hashes"][0]["alg"], "SHA-256")
            self.assertEqual(len(component["hashes"][0]["content"]), 64)
            self.assertFalse(any(item["name"].startswith("dist/") for item in payload["components"]))

    def test_status_snapshot_reports_progress_and_blockers(self) -> None:
        state = {
            "competition": "mcm",
            "mode": "standard",
            "current_stage": 3,
            "execution": {"interaction_mode": "guided", "blockers": ["problem_source_missing"]},
            "stages": {"3": {"_label": "model_selection"}, "9": {"submission_ready": False}},
        }
        data = snapshot(state, Path("workspace/state/decision_log.json"))
        self.assertEqual(data["status"], "blocked")
        self.assertEqual(data["competition"], "mcm")
        self.assertEqual(data["mode"], "guided")
        self.assertEqual(data["current_stage_label"], "model_selection")
        self.assertEqual(data["blockers"], ["problem_source_missing"])

    def test_status_snapshot_accepts_ready_state(self) -> None:
        state = {
            "competition": "cumcm",
            "current_stage": 9,
            "execution": {"blockers": []},
            "stages": {"9": {"submission_ready": True}},
        }
        data = snapshot(state, Path("state/decision_log.json"))
        self.assertEqual(data["status"], "ready")
        self.assertTrue(data["submission_ready"])

    def test_status_missing_state_is_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            data = load_snapshot(Path(temp) / "state" / "decision_log.json")
            self.assertEqual(data["status"], "missing")
            self.assertEqual(data["blockers"], ["state_file_missing"])


if __name__ == "__main__":
    unittest.main()
