from __future__ import annotations

from resono_runtime.agents import AgentAudience, AgentAudienceRouter, AgentKind
from resono_runtime.agents.audience import AudienceResource, AudienceResourceKind
from resono_runtime.background_agent.run_contract import AutonomyProfile
from resono_runtime.background_agent.tool_supply import BackgroundToolGrant, BackgroundToolSupply
from resono_runtime.storage.agent_audiences import AgentAudienceRepository
from resono_runtime.storage.background_agent_settings import BackgroundAgentSettingsRepository
from resono_runtime.storage.database import RuntimeDatabase
from resono_runtime.tools import ToolCatalog, ToolDefinition, ToolInvocationResult


def test_global_tool_migration_enables_current_builtins(tmp_path) -> None:
    database = RuntimeDatabase(tmp_path / "runtime.sqlite3")
    database.migrate()
    settings = BackgroundAgentSettingsRepository(database).get()
    assert settings.autonomy is AutonomyProfile.CUSTOM
    assert {"web_search", "tasks_add", "calendar_create_event", "email_compose"} <= settings.allowed_tool_names


def test_custom_explicit_grant_supplies_domain_writes(tmp_path) -> None:
    database = RuntimeDatabase(tmp_path / "runtime.sqlite3")
    database.migrate()
    resource = AudienceResource(AudienceResourceKind.DOMAIN_TOOL_SET, "tasks")
    router = AgentAudienceRouter(AgentAudienceRepository(database))
    router.set_audience(resource, AgentAudience.BOTH, changed_by="test", reason="test")
    catalog = ToolCatalog(audience_router=router)
    catalog.register(ToolDefinition(
        tool_id="test.tasks.add.v1", name="tasks_add", description="Add task",
        input_schema={"type": "object", "additionalProperties": False},
        handler=lambda _: ToolInvocationResult("ok"), effect_class="local_write",
        audience_resource=resource,
    ))
    supply = BackgroundToolSupply(catalog, BackgroundToolGrant(
        AutonomyProfile.CUSTOM, frozenset({"tasks_add"}), 3,
    ))
    assert [item["name"] for item in supply.mcp_definitions(AgentKind.TEXT)] == ["tasks_add"]
