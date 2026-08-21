from __future__ import annotations

from jsonschema import Draft202012Validator
from threading import RLock

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
        self._invocation_authorizer = None
        self._lock = RLock()

    def set_invocation_authorizer(self, authorizer) -> None:
        """Install the one trusted live-session authorization boundary."""
        with self._lock:
            self._invocation_authorizer = authorizer

    def register(self, definition: ToolDefinition) -> None:
        with self._lock:
            if definition.name in self._by_name or definition.tool_id in self._by_id:
                raise ValueError("tool identity collision")
            self._by_name[definition.name] = definition
            self._by_id[definition.tool_id] = definition

    def replace_source(self, source_id: str, definitions: tuple[ToolDefinition, ...]) -> None:
        """Atomically replace one dynamic source's tools after collision checks."""
        with self._lock:
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
        with self._lock:
            for tool_id in self._source_tool_ids.pop(source_id, set()):
                definition = self._by_id.pop(tool_id, None)
                if definition is not None:
                    self._by_name.pop(definition.name, None)

    def mcp_definitions(self, agent: AgentKind = AgentKind.VOICE) -> list[dict[str, object]]:
        return [definition.mcp_definition() for definition in self._definitions_for(agent)]

    def definitions_for(self, agent: AgentKind) -> tuple[ToolDefinition, ...]:
        """Canonical filtered definitions for trusted runtime adapters."""
        return self._definitions_for(agent)

    def realtime_definitions(
        self,
        *,
        include_names: frozenset[str] | None = None,
        exclude_names: frozenset[str] = frozenset(),
    ) -> tuple[dict[str, object], ...]:
        """Build one provider catalog from the canonical authorized Voice tools."""
        return tuple(
            definition.realtime_definition()
            for definition in self._definitions_for(AgentKind.VOICE)
            if definition.name not in exclude_names
            and (include_names is None or definition.name in include_names)
        )

    def management_projection(self) -> tuple[dict[str, object], ...]:
        result = []
        with self._lock:
            definitions = tuple(sorted(self._by_name.values(), key=lambda item: item.name))
        for definition in definitions:
            result.append({
                "name": definition.name,
                "description": definition.description,
                "effect": definition.effect_class,
                "voice": self._available_to(definition, AgentKind.VOICE),
                "text": self._available_to(definition, AgentKind.TEXT),
            })
        return tuple(result)

    def invoke(self, name: object, arguments: object, *, agent: AgentKind = AgentKind.VOICE, context: ToolInvocationContext | None = None) -> ToolInvocationResult:
        invocation_context = context or ToolInvocationContext(agent)
        with self._lock:
            definition = self._by_name.get(name) if isinstance(name, str) else None
            authorizer = self._invocation_authorizer
            available = definition is not None and self._available_to(definition, agent)
            mode_allowed = bool(
                definition is not None
                and (authorizer is None or authorizer(definition.name, invocation_context))
            )
        if not available:
            return ToolInvocationResult("Tool is not granted.", is_error=True)
        if not mode_allowed:
            return ToolInvocationResult("Tool is not granted in the current Voice mode.", is_error=True)
        if not isinstance(arguments, dict) or not _matches_schema(arguments, definition.input_schema):
            return ToolInvocationResult("Tool arguments are invalid.", is_error=True)
        if definition.context_handler is not None:
            return definition.context_handler(invocation_context, arguments)
        if definition.agent_handler is not None:
            return definition.agent_handler(agent, arguments)
        return definition.handler(arguments)

    def _definitions_for(self, agent: AgentKind) -> tuple[ToolDefinition, ...]:
        with self._lock:
            return tuple(
                definition for definition in self._by_name.values()
                if self._available_to(definition, agent)
            )

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
