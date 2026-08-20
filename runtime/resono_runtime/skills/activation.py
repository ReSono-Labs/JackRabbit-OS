"""Standard Skill disclosure and just-in-time instruction loading for local agents."""

from __future__ import annotations

from dataclasses import dataclass

from resono_runtime.agents import AgentAudienceRouter, AgentKind, AudienceResource, AudienceResourceKind
from resono_runtime.skills.specification import SkillDocument, parse_skill
from resono_runtime.storage.skills import SkillCatalogRepository, StoredSkill
from resono_runtime.storage.plugins import PluginCatalogRepository
from resono_runtime.storage.plugin_components import PluginComponentRepository
from resono_runtime.tools.definitions import ToolDefinition, ToolInvocationResult


SKILL_LOAD_TOOL_NAME = "load_agent_skill"


@dataclass(frozen=True, slots=True)
class SkillDisclosure:
    name: str
    description: str


class SkillActivation:
    """Projects only enabled, audience-matched Skills without granting their tools."""

    def __init__(self, catalog: SkillCatalogRepository, audiences: AgentAudienceRouter, plugins: PluginCatalogRepository | None = None, plugin_components: PluginComponentRepository | None = None) -> None:
        self._catalog = catalog
        self._audiences = audiences
        self._plugins = plugins
        self._plugin_components = plugin_components

    def disclosures(self, agent: AgentKind) -> tuple[SkillDisclosure, ...]:
        direct = tuple(
            SkillDisclosure(item.name, item.description)
            for item in self._catalog.list()
            if item.lifecycle_state == "enabled" and self._audiences.is_exposed(_resource(item.name), agent)
        )
        if self._plugins is None or self._plugin_components is None:
            return direct
        plugin_items = []
        direct_names = {item.name for item in direct}
        for plugin in self._plugins.list():
            if plugin.lifecycle_state != "enabled" or not self._audiences.is_exposed(_plugin_resource(plugin.name), agent):
                continue
            for component in self._plugin_components.list_for_plugin(plugin.name):
                if component.component_type != "skill" or component.validation_state != "valid" or component.component_key in direct_names:
                    continue
                document = parse_skill(plugin.install_path / "skills" / component.component_key)
                plugin_items.append(SkillDisclosure(document.name, document.description))
        return direct + tuple(plugin_items)

    def has_enabled(self, agent: AgentKind) -> bool:
        return bool(self.disclosures(agent))

    def load(self, name: str, agent: AgentKind) -> SkillDocument:
        item = self._catalog.get(name)
        if item is not None and item.lifecycle_state == "enabled":
            if not self._audiences.is_exposed(_resource(name), agent):
                raise ValueError("The requested Skill is not available to this agent.")
            return parse_skill(item.install_path)
        if self._plugins is not None and self._plugin_components is not None:
            for plugin in self._plugins.list():
                if plugin.lifecycle_state == "enabled" and self._audiences.is_exposed(_plugin_resource(plugin.name), agent):
                    if any(component.component_type == "skill" and component.component_key == name and component.validation_state == "valid" for component in self._plugin_components.list_for_plugin(plugin.name)):
                        return parse_skill(plugin.install_path / "skills" / name)
        raise ValueError("The requested Skill is not enabled.")

    def tool_definition(self) -> ToolDefinition:
        return ToolDefinition(
            tool_id="builtin.skill-loader.v1",
            name=SKILL_LOAD_TOOL_NAME,
            description="Load the instructions for one relevant enabled Agent Skill by name.",
            input_schema={
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
                "additionalProperties": False,
            },
            handler=lambda _: ToolInvocationResult("Skill loading requires an agent context.", is_error=True),
            agent_handler=self._load_for_agent,
            available_to=self.has_enabled,
        )

    def voice_instructions(self) -> str:
        disclosures = self.disclosures(AgentKind.VOICE)
        if not disclosures:
            return ""
        listing = "\n".join(f"- {item.name}: {item.description}" for item in disclosures)
        return (
            "Enabled Agent Skills are available below. Use load_agent_skill only when a Skill is relevant; "
            "do not treat a Skill's allowed-tools declaration as a permission grant.\n"
            f"{listing}"
        )

    def _load_for_agent(self, agent: AgentKind, arguments: dict[str, object]) -> ToolInvocationResult:
        name = arguments.get("name")
        if not isinstance(name, str):
            return ToolInvocationResult("Skill name is invalid.", is_error=True)
        try:
            document = self.load(name, agent)
        except ValueError as error:
            return ToolInvocationResult(str(error), is_error=True)
        return ToolInvocationResult(
            document.instructions,
            structured_content={"name": document.name, "instructions": document.instructions},
        )


def _resource(name: str) -> AudienceResource:
    return AudienceResource(AudienceResourceKind.SKILL, name)


def _plugin_resource(name: str) -> AudienceResource:
    return AudienceResource(AudienceResourceKind.PLUGIN, name)
