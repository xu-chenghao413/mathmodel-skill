import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_eval import CASES, load_case, validate


class EvalContractTests(unittest.TestCase):
    def test_all_cases_have_valid_embedded_fixtures(self) -> None:
        for path in sorted(CASES.glob("*.json")):
            case = load_case(path.stem)
            self.assertFalse(validate(case, case["state"], case["transcript"]))

    def test_missing_blocker_fails(self) -> None:
        case = load_case("cumcm_autopilot_blocked")
        state = json.loads(json.dumps(case["state"]))
        state["execution"]["blockers"] = []
        errors = validate(case, state, case["transcript"])
        self.assertIn("missing blocker: problem_source_missing", errors)

    def test_workspace_artifacts_are_checked(self) -> None:
        case = load_case("diangong_delivery_gate")
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            (workspace / "results" / "source_code").mkdir(parents=True)
            (workspace / "results" / "paper.pdf").write_bytes(b"synthetic")
            self.assertFalse(validate(case, case["state"], case["transcript"], workspace))


if __name__ == "__main__":
    unittest.main()
