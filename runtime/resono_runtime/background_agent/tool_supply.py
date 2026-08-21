"""Per-run capability intersection and direct-call enforcement."""

from __future__ import annotations

from dataclasses import dataclass
import threading
import time
from collections.abc import Callable

from ..agents.audience import AgentKind
from ..tools.catalog import ToolCatalog
from ..tools.definitions import ToolDefinition, ToolInvocationContext, ToolInvocationResult
from .run_contract import AutonomyProfile


class ToolBudgetExceeded(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class BackgroundToolGrant:
    autonomy: AutonomyProfile
    explicit_names: frozenset[str]
    max_calls: int

    def __post_init__(self) -> None:
        if self.max_calls <= 0:
            raise ValueError("max_calls must be positive")


class BackgroundToolSupply:
    """One run's immutable view over the canonical Tool Catalog."""

    def __init__(self, catalog: ToolCatalog, grant: BackgroundToolGrant,
                 activity: Callable[[str, dict[str, object]], None] | None = None) -> None:
        self._catalog = catalog
        self._grant = grant
        self._definitions = tuple(
            item for item in catalog.definitions_for(AgentKind.TEXT) if self._allowed(item)
        )
        self._allowed_names = frozenset(item.name for item in self._definitions)
        self._calls = 0
        self._activity = activity or (lambda _event, _detail: None)
        self._lock = threading.Lock()

    @property
    def calls_used(self) -> int:
        with self._lock:
            return self._calls

    def mcp_definitions(self, _agent: AgentKind = AgentKind.TEXT) -> list[dict[str, object]]:
        return [item.mcp_definition() for item in self._definitions]

    def invoke(self, name: object, arguments: object, *, agent: AgentKind = AgentKind.TEXT,
               context: ToolInvocationContext | None = None) -> ToolInvocationResult:
        if agent is not AgentKind.TEXT or not isinstance(name, str) or name not in self._allowed_names:
            return ToolInvocationResult("Tool is not granted to this background-agent run.", is_error=True)
        with self._lock:
            if self._calls >= self._grant.max_calls:
                raise ToolBudgetExceeded("background-agent tool-call limit reached")
            self._calls += 1
            call_number = self._calls
        started = time.monotonic()
        self._activity("tool_started", {"name": name, "call": call_number})
        try:
            result = self._catalog.invoke(
                name, arguments, agent=AgentKind.TEXT,
                context=context or ToolInvocationContext(AgentKind.TEXT),
            )
        except Exception:
            self._activity("tool_failed", {
                "name": name, "call": call_number,
                "durationMs": int((time.monotonic() - started) * 1000),
            })
            raise
        self._activity("tool_completed" if not result.is_error else "tool_failed", {
            "name": name, "call": call_number, "isError": result.is_error,
            "durationMs": int((time.monotonic() - started) * 1000),
        })
        return result

    def _allowed(self, definition: ToolDefinition) -> bool:
        if definition.name not in self._grant.explicit_names:
            return False
        if self._grant.autonomy is AutonomyProfile.LIMITED:
            return definition.effect_class == "read"
        if self._grant.autonomy is AutonomyProfile.EXPANDED:
            return definition.effect_class in {"read", "local_write"}
        return definition.effect_class not in _HARD_APPROVAL_EFFECTS


_HARD_APPROVAL_EFFECTS = frozenset({"destructive", "credential", "package_lifecycle"})
