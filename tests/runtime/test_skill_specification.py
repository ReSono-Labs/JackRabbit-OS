from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from resono_runtime.skills import SkillSpecificationError, parse_skill


class SkillSpecificationTest(unittest.TestCase):
    def test_parses_standard_skill_without_granting_allowed_tools(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "mail-summary"
            root.mkdir()
            (root / "SKILL.md").write_text(
                "---\nname: mail-summary\ndescription: Summarize mail.\n"
                "allowed-tools: email_read\nmetadata:\n  author: test\n---\nUse concise summaries.\n",
                encoding="utf-8",
            )
            skill = parse_skill(root)
        self.assertEqual("mail-summary", skill.name)
        self.assertEqual("email_read", skill.allowed_tools)
        self.assertEqual("Use concise summaries.\n", skill.instructions)

    def test_rejects_name_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "different"
            root.mkdir()
            (root / "SKILL.md").write_text(
                "---\nname: invalid-name\ndescription: Test.\n---\nBody\n", encoding="utf-8"
            )
            with self.assertRaises(SkillSpecificationError):
                parse_skill(root)


if __name__ == "__main__":
    unittest.main()
