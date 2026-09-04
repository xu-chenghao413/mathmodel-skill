from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "examples" / "quickstart" / "run_demo.py"


class QuickstartDemoTests(unittest.TestCase):
    def test_demo_generates_conserved_allocation_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "demo-output"
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--output", str(output)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            with (output / "results" / "allocation.csv").open(encoding="utf-8", newline="") as handle:
                allocations = list(csv.DictReader(handle))
            total = sum((Decimal(row["allocation"]) for row in allocations), Decimal("0"))
            self.assertEqual(len(allocations), 5)
            self.assertEqual(total, Decimal("10000.00"))

            summary = json.loads((output / "results" / "summary.json").read_text(encoding="utf-8"))
            manifest = json.loads((output / "qa" / "manifest.json").read_text(encoding="utf-8"))
            self.assertTrue(summary["checks"]["budget_conserved"])
            self.assertTrue(manifest["synthetic_data"])
            self.assertTrue(manifest["ready"])
            self.assertIn("results/allocation.csv", manifest["files"])
            self.assertIn("analysis/model_card.json", manifest["files"])

    def test_demo_refuses_overwrite_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "demo-output"
            first = subprocess.run(
                [sys.executable, str(SCRIPT), "--output", str(output)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            second = subprocess.run(
                [sys.executable, str(SCRIPT), "--output", str(output)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(first.returncode, 0)
            self.assertEqual(second.returncode, 2)
            self.assertIn("already exists", second.stderr)


if __name__ == "__main__":
    unittest.main()
