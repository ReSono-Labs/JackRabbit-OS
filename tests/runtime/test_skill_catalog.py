from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from resono_runtime.skills import parse_skill_document
from resono_runtime.storage.database import RuntimeDatabase
from resono_runtime.storage.skills import SkillCatalogRepository


class SkillCatalogRepositoryTest(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        root = Path(self._temporary.name)
        self.database = RuntimeDatabase(root / "runtime.sqlite3")
        self.database.migrate()
        self.catalog = SkillCatalogRepository(self.database)

    def tearDown(self) -> None:
        self._temporary.cleanup()

    def test_standalone_document_parses_before_install_directory_exists(self) -> None:
        document_path = Path(self._temporary.name) / "skills.md"
        document_path.write_text("---\nname: planning\ndescription: Plan meetings.\n---\nUse the calendar.", encoding="utf-8")

        document = parse_skill_document(document_path)

        self.assertEqual("planning", document.name)

    def test_catalog_replaces_one_canonical_skill_row(self) -> None:
        self.catalog.save_current(
            name="planning",
            description="Plan meetings.",
            content_hash="first",
            install_path=Path("/runtime/skills/planning"),
            source_filename="SKILL.md",
            state="installed",
            action="install",
            changed_by="owner",
            reason="import",
        )
        self.catalog.save_current(
            name="planning",
            description="Plan meetings better.",
            content_hash="second",
            install_path=Path("/runtime/skills/planning"),
            source_filename="skills.md",
            state="installed",
            action="replace",
            changed_by="owner",
            reason="confirmed replacement",
        )

        stored = self.catalog.get("planning")
        self.assertEqual("second", stored.content_hash)
        self.assertEqual(1, len(self.catalog.list()))
        with self.database.connect() as connection:
            audit_count = connection.execute("SELECT COUNT(*) FROM skill_catalog_audit").fetchone()[0]
        self.assertEqual(2, audit_count)


if __name__ == "__main__":
    unittest.main()
