"""Stable application port for replaceable delegated-work implementations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class DelegationRequest:
    origin_kind: str
    origin_id: str
    objective: str
    success_criteria: tuple[str, ...]
    result_schema: dict[str, object]
    requested_resource_ids: tuple[str, ...] = ()
    recipe: str | None = None
    goal_type: str = "general"
    context_summary: str = ""
    expected_result: str = ""
    scope: str = ""
    exclusions: tuple[str, ...] = ()
    source_requirements: str = ""
    workspace_destination: str | None = None
    original_request: str = ""
    verification_method: str = ""
    completion_conditions: tuple[str, ...] = ()
    stop_conditions: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class DelegationRun:
    run_id: str
    origin_kind: str
    origin_id: str
    state: str
    recipe: str
    output: dict[str, object] | None
    failure_code: str | None
    failure_message: str | None


class DelegationService(Protocol):
    def submit(self, request: DelegationRequest) -> DelegationRun: ...
    def inspect(self, run_id: str) -> DelegationRun: ...
    def cancel(self, run_id: str) -> DelegationRun: ...


class DelegationUnavailable:
    """Drop-in composition used when the experimental subsystem is absent."""

    def submit(self, request: DelegationRequest) -> DelegationRun:
        raise RuntimeError("Delegated work is unavailable")

    def inspect(self, run_id: str) -> DelegationRun:
        raise RuntimeError("Delegated work is unavailable")

    def cancel(self, run_id: str) -> DelegationRun:
        raise RuntimeError("Delegated work is unavailable")
