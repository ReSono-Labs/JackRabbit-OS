from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from resono_runtime.agents import AgentAudience, AgentAudienceRouter, AgentKind, AudienceResource, AudienceResourceKind
from resono_runtime.skills.archives import SkillArchiveInspector
from resono_runtime.skills.lifecycle import SkillLifecycle, SkillLifecycleError
from resono_runtime.storage.agent_audiences import AgentAudienceRepository
from resono_runtime.storage.database import RuntimeDatabase
from resono_runtime.storage.skills import SkillCatalogRepository


class SkillLifecycleTest(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.root = Path(self._temporary.name)
        database = RuntimeDatabase(self.root / "runtime.sqlite3")
        database.migrate()
        self.catalog = SkillCatalogRepository(database)
        self.router = AgentAudienceRouter(AgentAudienceRepository(database))
        self.inspector = SkillArchiveInspector(self.root / "quarantine")
        self.lifecycle = SkillLifecycle(
            catalog=self.catalog,
            audiences=self.router,
            skills_root=self.root / "skills",
            rollback_root=self.root / "rollbacks",
        )

    def tearDown(self) -> None:
        self._temporary.cleanup()

    def test_new_skill_installs_one_canonical_directory_and_audience(self) -> None:
        preflight = self.lifecycle.preflight(self._candidate("First instructions."), audience=AgentAudience.BOTH)

        self.assertEqual("new", preflight.state)
        stored = self.lifecycle.confirm(
            preflight.token,
            replace=False,
            changed_by="owner",
            reason="install",
        )

        self.assertEqual("enabled", stored.lifecycle_state)
        self.assertTrue((stored.install_path / "SKILL.md").is_file())
        resource = AudienceResource(AudienceResourceKind.SKILL, "planning")
        self.assertTrue(self.router.is_exposed(resource, AgentKind.VOICE))
        self.assertTrue(self.router.is_exposed(resource, AgentKind.TEXT))

    def test_conflict_requires_explicit_replace_and_keeps_one_item(self) -> None:
        initial = self.lifecycle.preflight(self._candidate("First instructions."), audience=AgentAudience.VOICE)
        self.lifecycle.confirm(initial.token, replace=False, changed_by="owner", reason="install")
        replacement = self.lifecycle.preflight(self._candidate("Second instructions."), audience=AgentAudience.TEXT)

        self.assertEqual("conflict", replacement.state)
        with self.assertRaisesRegex(SkillLifecycleError, "explicit confirmation"):
            self.lifecycle.confirm(replacement.token, replace=False, changed_by="owner", reason="replace")

        stored = self.lifecycle.confirm(replacement.token, replace=True, changed_by="owner", reason="replace")

        self.assertEqual(1, len(self.catalog.list()))
        self.assertIn("Second instructions.", (stored.install_path / "SKILL.md").read_text(encoding="utf-8"))
        self.assertIn("First instructions.", (self.root / "rollbacks" / "planning" / "SKILL.md").read_text(encoding="utf-8"))

    def test_disable_then_delete_removes_projection_and_catalog_item(self) -> None:
        preflight = self.lifecycle.preflight(self._candidate("First instructions."), audience=AgentAudience.BOTH)
        self.lifecycle.confirm(preflight.token, replace=False, changed_by="owner", reason="install")

        self.lifecycle.disable("planning", changed_by="owner", reason="disable")
        resource = AudienceResource(AudienceResourceKind.SKILL, "planning")
        self.assertFalse(self.router.is_exposed(resource, AgentKind.VOICE))
        self.lifecycle.enable("planning", changed_by="owner", reason="enable")
        self.assertTrue(self.router.is_exposed(resource, AgentKind.VOICE))
        self.lifecycle.disable("planning", changed_by="owner", reason="disable again")
        self.lifecycle.delete("planning", changed_by="owner", reason="delete")

        self.assertIsNone(self.catalog.get("planning"))
        self.assertFalse((self.root / "skills" / "planning").exists())
        self.assertFalse((self.root / "rollbacks" / "planning").exists())

    def _candidate(self, instructions: str):
        payload = f"---\nname: planning\ndescription: Plan meetings.\n---\n{instructions}".encode("utf-8")
        return self.inspector.inspect(payload, "skills.md")


if __name__ == "__main__":
    unittest.main()
