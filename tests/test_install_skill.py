from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "install_skill.py"
SPEC = importlib.util.spec_from_file_location("mathmodel_install_skill", SCRIPT)
assert SPEC and SPEC.loader
install_skill = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(install_skill)


class InstallSkillTests(unittest.TestCase):
    def test_agent_scope_paths_are_deterministic(self) -> None:
        home = Path("/home/tester")
        cwd = Path("/work/project")
        self.assertEqual(
            install_skill.resolve_destination("claude", "user", home=home, cwd=cwd),
            (home / ".claude/skills/mathmodel-skill").resolve(),
        )
        self.assertEqual(
            install_skill.resolve_destination("opencode", "project", home=home, cwd=cwd),
            (cwd / ".opencode/skills/mathmodel-skill").resolve(),
        )

    def test_installer_copies_runtime_payload_without_generated_or_ci_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "source"
            destination = Path(temp) / "destination"
            source.mkdir()
            (source / "SKILL.md").write_text("---\nname: mathmodel-skill\n---\n", encoding="utf-8")
            for filename in install_skill.RUNTIME_FILES[1:]:
                (source / filename).write_text(filename, encoding="utf-8")
            for dirname in install_skill.RUNTIME_DIRS:
                (source / dirname).mkdir()
                (source / dirname / "payload.txt").write_text(dirname, encoding="utf-8")
            (source / ".git").mkdir()
            (source / ".github").mkdir()
            (source / "state").mkdir()
            (source / "state" / "decision_log.json").write_text("{}", encoding="utf-8")

            created = install_skill.install_payload(source, destination)

            self.assertIn(destination / "SKILL.md", created)
            self.assertTrue((destination / "references" / "payload.txt").is_file())
            self.assertFalse((destination / ".git").exists())
            self.assertFalse((destination / ".github").exists())
            self.assertFalse((destination / "state").exists())

    def test_installer_refuses_overwrite_and_nested_source_destination(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "source"
            source.mkdir()
            (source / "SKILL.md").write_text("---\nname: mathmodel-skill\n---\n", encoding="utf-8")
            for filename in install_skill.RUNTIME_FILES[1:]:
                (source / filename).write_text(filename, encoding="utf-8")
            for dirname in install_skill.RUNTIME_DIRS:
                (source / dirname).mkdir()

            existing = source.parent / "existing"
            existing.mkdir()
            with self.assertRaises(FileExistsError):
                install_skill.install_payload(source, existing)

            with self.assertRaises(ValueError):
                install_skill.install_payload(source, source / "nested")


if __name__ == "__main__":
    unittest.main()
