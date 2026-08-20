from __future__ import annotations

from jsonschema import Draft202012Validator

from ..agents.audience import AgentKind
from ..agents.routing import AgentAudienceRouter
from .definitions import ToolDefinition, ToolInvocationContext, ToolInvocationResult


class ToolCatalog:
    """Single authority for schema, dispatch, and agent-audience tool projection."""

    def __init__(self, *, audience_router: AgentAudienceRouter | None = None) -> None:
        self._by_name: dict[str, ToolDefinition] = {}
        self._by_id: dict[str, ToolDefinition] = {}
        self._source_tool_ids: dict[str, set[str]] = {}
        self._audience_router = audience_router

    def register(self, definition: ToolDefinition) -> None:
        if definition.name in self._by_name or definition.tool_id in self._by_id:
            raise ValueError("tool identity collision")
        self._by_name[definition.name] = definition
        self._by_id[definition.tool_id] = definition

    def replace_source(self, source_id: str, definitions: tuple[ToolDefinition, ...]) -> None:
        """Atomically replace one dynamic source's tools after collision checks."""
        if not source_id:
            raise ValueError("source_id is required")
        prior_ids = self._source_tool_ids.get(source_id, set())
        prior_names = {self._by_id[tool_id].name for tool_id in prior_ids}
        names = [definition.name for definition in definitions]
        ids = [definition.tool_id for definition in definitions]
        if len(names) != len(set(names)) or len(ids) != len(set(ids)):
            raise ValueError("dynamic tool identity collision")
        if any(name in self._by_name and name not in prior_names for name in names):
            raise ValueError("tool name collision")
        if any(tool_id in self._by_id and tool_id not in prior_ids for tool_id in ids):
            raise ValueError("tool id collision")
        self.remove_source(source_id)
        for definition in definitions:
            self.register(definition)
        self._source_tool_ids[source_id] = set(ids)

    def remove_source(self, source_id: str) -> None:
        for tool_id in self._source_tool_ids.pop(source_id, set()):
            definition = self._by_id.pop(tool_id, None)
            if definition is not None:
                self._by_name.pop(definition.name, None)

    def mcp_definitions(self, agent: AgentKind = AgentKind.VOICE) -> list[dict[str, object]]:
        return [definition.mcp_definition() for definition in self._definitions_for(agent)]

    def realtime_definitions(self) -> tuple[dict[str, object], ...]:
        return tuple(definition.realtime_definition() for definition in self._definitions_for(AgentKind.VOICE))

    def management_projection(self) -> tuple[dict[str, object], ...]:
        result = []
        for definition in sorted(self._by_name.values(), key=lambda item: item.name):
            result.append(
                {
                    "name": definition.name,
                    "description": definition.description,
                    "effect": definition.effect_class,
                    "voice": self._available_to(definition, AgentKind.VOICE),
                    "text": self._available_to(definition, AgentKind.TEXT),
                }
            )
        return tuple(result)

    def invoke(self, name: object, arguments: object, *, agent: AgentKind = AgentKind.VOICE, context: ToolInvocationContext | None = None) -> ToolInvocationResult:
        definition = self._by_name.get(name) if isinstance(name, str) else None
        if definition is None or not self._available_to(definition, agent):
            return ToolInvocationResult("Tool is not granted.", is_error=True)
        if not isinstance(arguments, dict) or not _matches_schema(arguments, definition.input_schema):
            return ToolInvocationResult("Tool arguments are invalid.", is_error=True)
        if definition.context_handler is not None:
            return definition.context_handler(context or ToolInvocationContext(agent), arguments)
        if definition.agent_handler is not None:
            return definition.agent_handler(agent, arguments)
        return definition.handler(arguments)

    def _definitions_for(self, agent: AgentKind) -> tuple[ToolDefinition, ...]:
        return tuple(definition for definition in self._by_name.values() if self._available_to(definition, agent))

    def _available_to(self, definition: ToolDefinition, agent: AgentKind) -> bool:
        if not definition.voice_available:
            return False
        if definition.available_to is not None and not definition.available_to(agent):
            return False
        resource = definition.audience_resource
        return (
            resource is None
            or self._audience_router is None
            or self._audience_router.is_exposed(resource, agent)
        )


def _matches_schema(arguments: dict[str, object], schema: dict[str, object]) -> bool:
    try:
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(arguments)
    except Exception:
        return False
    return True
