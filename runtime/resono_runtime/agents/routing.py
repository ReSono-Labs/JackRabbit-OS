"""Agent-audience routing without package, permission, or execution behavior."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from resono_runtime.agents.audience import AgentAudience, AgentKind, AudienceResource


@dataclass(frozen=True)
class AudienceBinding:
    resource: AudienceResource
    audience: AgentAudience
    active: bool
    changed_at: str
    changed_by: str
    change_reason: str


class AudienceBindingStore(Protocol):
    """The minimal durable contract required by the router."""

    def save(
        self,
        resource: AudienceResource,
        audience: AgentAudience,
        *,
        changed_by: str,
        reason: str,
    ) -> AudienceBinding: ...

    def get(self, resource: AudienceResource) -> AudienceBinding | None: ...

    def list_for(self, agent: AgentKind) -> list[AudienceBinding]: ...

    def deactivate(
        self,
        resource: AudienceResource,
        *,
        changed_by: str,
        reason: str,
    ) -> AudienceBinding | None: ...

    def remove(
        self,
        resource: AudienceResource,
        *,
        changed_by: str,
        reason: str,
    ) -> None: ...


class AgentAudienceRouter:
    """Answers only whether a valid resource belongs to one local agent view."""

    def __init__(self, bindings: AudienceBindingStore) -> None:
        self._bindings = bindings

    def set_audience(
        self,
        resource: AudienceResource,
        audience: AgentAudience,
        *,
        changed_by: str,
        reason: str,
    ) -> AudienceBinding:
        self._require_actor_and_reason(changed_by, reason)
        return self._bindings.save(
            resource,
            audience,
            changed_by=changed_by,
            reason=reason,
        )

    def binding_for(self, resource: AudienceResource) -> AudienceBinding | None:
        return self._bindings.get(resource)

    def is_exposed(self, resource: AudienceResource, agent: AgentKind) -> bool:
        binding = self._bindings.get(resource)
        return bool(binding and binding.active and binding.audience.includes(agent))

    def list_for(self, agent: AgentKind) -> list[AudienceBinding]:
        return self._bindings.list_for(agent)

    def deactivate(
        self,
        resource: AudienceResource,
        *,
        changed_by: str,
        reason: str,
    ) -> AudienceBinding | None:
        self._require_actor_and_reason(changed_by, reason)
        return self._bindings.deactivate(
            resource,
            changed_by=changed_by,
            reason=reason,
        )

    def remove_resource(
        self,
        resource: AudienceResource,
        *,
        changed_by: str,
        reason: str,
    ) -> None:
        self._require_actor_and_reason(changed_by, reason)
        self._bindings.remove(resource, changed_by=changed_by, reason=reason)

    @staticmethod
    def _require_actor_and_reason(changed_by: str, reason: str) -> None:
        if not changed_by or changed_by.strip() != changed_by:
            raise ValueError("changed_by must be a non-empty trimmed string")
        if not reason or reason.strip() != reason:
            raise ValueError("reason must be a non-empty trimmed string")

