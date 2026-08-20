from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from resono_runtime.agents import (
    AgentAudience,
    AgentAudienceRouter,
    AgentKind,
    AudienceResource,
    AudienceResourceKind,
)
from resono_runtime.storage.agent_audiences import AgentAudienceRepository
from resono_runtime.storage.database import RuntimeDatabase
from resono_runtime.tools import ToolCatalog, ToolDefinition, ToolInvocationResult


class AgentAudienceRouterTest(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.database = RuntimeDatabase(Path(self._temporary.name) / "runtime.sqlite3")
        self.database.migrate()
        self.router = AgentAudienceRouter(AgentAudienceRepository(self.database))
        self.skill = AudienceResource(AudienceResourceKind.SKILL, "meeting-planning")

    def tearDown(self) -> None:
        self._temporary.cleanup()

    def test_migration_and_one_canonical_binding(self) -> None:
        self.router.set_audience(
            self.skill,
            AgentAudience.VOICE,
            changed_by="owner",
            reason="initial import",
        )
        self.router.set_audience(
            self.skill,
            AgentAudience.BOTH,
            changed_by="owner",
            reason="expand access",
        )

        self.assertTrue(self.router.is_exposed(self.skill, AgentKind.VOICE))
        self.assertTrue(self.router.is_exposed(self.skill, AgentKind.TEXT))
        with self.database.connect() as connection:
            binding_count = connection.execute(
                "SELECT COUNT(*) FROM agent_audience_bindings"
            ).fetchone()[0]
            audit_count = connection.execute(
                "SELECT COUNT(*) FROM agent_audience_audit"
            ).fetchone()[0]
        self.assertEqual(1, binding_count)
        self.assertEqual(2, audit_count)

    def test_disable_and_remove_stop_both_projections(self) -> None:
        self.router.set_audience(
            self.skill,
            AgentAudience.BOTH,
            changed_by="owner",
            reason="initial import",
        )
        self.router.deactivate(self.skill, changed_by="owner", reason="disabled")
        self.assertFalse(self.router.is_exposed(self.skill, AgentKind.VOICE))
        self.assertFalse(self.router.is_exposed(self.skill, AgentKind.TEXT))

        self.router.remove_resource(self.skill, changed_by="owner", reason="deleted")
        self.assertIsNone(self.router.binding_for(self.skill))

    def test_catalog_uses_named_agent_projection(self) -> None:
        catalog = ToolCatalog(audience_router=self.router)
        catalog.register(
            ToolDefinition(
                tool_id="test.skill-tool.v1",
                name="skill_tool",
                description="Test tool.",
                input_schema={"type": "object", "properties": {}, "additionalProperties": False},
                handler=lambda _: ToolInvocationResult("ok"),
                audience_resource=self.skill,
            )
        )

        self.assertEqual((), catalog.realtime_definitions())
        self.router.set_audience(
            self.skill,
            AgentAudience.TEXT,
            changed_by="owner",
            reason="text only",
        )
        self.assertEqual((), catalog.realtime_definitions())
        self.assertEqual(["skill_tool"], [tool["name"] for tool in catalog.mcp_definitions(AgentKind.TEXT)])
        self.assertTrue(catalog.invoke("skill_tool", {}, agent=AgentKind.VOICE).is_error)
        self.assertFalse(catalog.invoke("skill_tool", {}, agent=AgentKind.TEXT).is_error)


if __name__ == "__main__":
    unittest.main()
