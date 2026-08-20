from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from resono_runtime.agents import AgentAudience, AgentAudienceRouter, AgentKind
from resono_runtime.skills import SkillActivation
from resono_runtime.skills.archives import SkillArchiveInspector
from resono_runtime.skills.lifecycle import SkillLifecycle
from resono_runtime.storage.agent_audiences import AgentAudienceRepository
from resono_runtime.storage.database import RuntimeDatabase
from resono_runtime.storage.skills import SkillCatalogRepository
from resono_runtime.tools import ToolCatalog


class SkillActivationTest(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        root = Path(self._temporary.name)
        database = RuntimeDatabase(root / "runtime.sqlite3")
        database.migrate()
        catalog = SkillCatalogRepository(database)
        router = AgentAudienceRouter(AgentAudienceRepository(database))
        inspector = SkillArchiveInspector(root / "quarantine")
        lifecycle = SkillLifecycle(
            catalog=catalog,
            audiences=router,
            skills_root=root / "skills",
            rollback_root=root / "rollbacks",
        )
        candidate = inspector.inspect(
            b"---\nname: planning\ndescription: Plan meetings.\nallowed-tools: calendar.create\n---\nCheck conflicts first.",
            "skills.md",
        )
        preflight = lifecycle.preflight(candidate, audience=AgentAudience.VOICE)
        lifecycle.confirm(preflight.token, replace=False, changed_by="owner", reason="install")
        lifecycle.enable("planning", changed_by="owner", reason="enable")
        self.activation = SkillActivation(catalog, router)
        self.tools = ToolCatalog(audience_router=router)
        self.tools.register(self.activation.tool_definition())

    def tearDown(self) -> None:
        self._temporary.cleanup()

    def test_voice_gets_disclosure_and_can_load_full_instructions(self) -> None:
        self.assertEqual(("planning",), tuple(item.name for item in self.activation.disclosures(AgentKind.VOICE)))
        self.assertEqual((), self.activation.disclosures(AgentKind.TEXT))
        self.assertIn("planning: Plan meetings.", self.activation.voice_instructions())
        self.assertNotIn("Check conflicts first.", self.activation.voice_instructions())

        result = self.tools.invoke("load_agent_skill", {"name": "planning"}, agent=AgentKind.VOICE)
        self.assertFalse(result.is_error)
        self.assertEqual("Check conflicts first.", result.structured_content["instructions"])

    def test_text_cannot_list_or_load_a_voice_skill(self) -> None:
        self.assertEqual([], self.tools.mcp_definitions(AgentKind.TEXT))
        result = self.tools.invoke("load_agent_skill", {"name": "planning"}, agent=AgentKind.TEXT)
        self.assertTrue(result.is_error)


if __name__ == "__main__":
    unittest.main()
