"""Versioned immutable context shared by local agent execution surfaces."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ExecutionKind(str, Enum):
    PRIMARY_VOICE = "primary_voice"
    GOAL_INTAKE = "goal_intake"
    BACKGROUND_GOAL = "background_goal"


@dataclass(frozen=True, slots=True)
class WorkspaceGrant:
    scope: str
    access: str


@dataclass(frozen=True, slots=True)
class PrimaryAgentContext:
    context_version: int
    execution_id: str
    execution_kind: ExecutionKind
    origin_id: str
    instruction_profile: str
    tool_ids: tuple[str, ...] = ()
    skill_ids: tuple[str, ...] = ()
    memory_references: tuple[str, ...] = ()
    workspace_grants: tuple[WorkspaceGrant, ...] = ()
    rendered_context: str = ""

    def __post_init__(self) -> None:
        if self.context_version != 1:
            raise ValueError("unsupported primary-agent context version")
        for name, value in (("execution_id", self.execution_id), ("origin_id", self.origin_id),
                            ("instruction_profile", self.instruction_profile)):
            if not value or value.strip() != value:
                raise ValueError(f"{name} must be a non-empty trimmed string")
        for values in (self.tool_ids, self.skill_ids, self.memory_references):
            if len(values) != len(set(values)):
                raise ValueError("primary-agent context references must be unique")
        if len(self.rendered_context) > 32_768:
            raise ValueError("rendered agent context is too long")
