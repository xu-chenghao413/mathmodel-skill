from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_sbom import build


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


if __name__ == "__main__":
    unittest.main()
