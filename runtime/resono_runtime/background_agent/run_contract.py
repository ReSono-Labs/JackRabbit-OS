"""Typed, provider-neutral contracts for one background-agent run."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class InvocationType(str, Enum):
    GOAL = "goal"


class AutonomyProfile(str, Enum):
    LIMITED = "limited"
    EXPANDED = "expanded"
    CUSTOM = "custom"


class ExecutionRecipe(str, Enum):
    DIRECT = "direct_v1"
    SELF_REVIEW = "self_review_v1"
    INDEPENDENT_REVIEW = "independent_review_v1"


class AgentRunState(str, Enum):
    ACCEPTED = "accepted"
    QUEUED = "queued"
    RUNNING = "running"
    REVIEWING = "reviewing"
    REPAIRING = "repairing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class RunLimits:
    max_seconds: int = 300
    max_model_turns: int = 24
    max_tool_calls: int = 40
    max_review_rounds: int = 2
    max_workspace_bytes: int = 8 * 1024 * 1024

    def __post_init__(self) -> None:
        values = (
            self.max_seconds,
            self.max_model_turns,
            self.max_tool_calls,
            self.max_review_rounds,
            self.max_workspace_bytes,
        )
        if any(value <= 0 for value in values):
            raise ValueError("run limits must be positive")
        if self.max_seconds > 3600 or self.max_model_turns > 100 or self.max_tool_calls > 500:
            raise ValueError("run limits exceed the supported maximum")
        if self.max_review_rounds > 10 or self.max_workspace_bytes > 256 * 1024 * 1024:
            raise ValueError("run limits exceed the supported maximum")


@dataclass(frozen=True, slots=True)
class AgentRunRequest:
    run_id: str
    invocation_type: InvocationType
    origin_id: str
    objective: str
    instruction_profile: str
    success_criteria: tuple[str, ...]
    result_schema: dict[str, object]
    requested_resource_ids: tuple[str, ...] = ()
    recipe: ExecutionRecipe = ExecutionRecipe.SELF_REVIEW
    autonomy: AutonomyProfile = AutonomyProfile.LIMITED
    limits: RunLimits = RunLimits()
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

    def __post_init__(self) -> None:
        for name, value in (
            ("run_id", self.run_id),
            ("origin_id", self.origin_id),
            ("objective", self.objective),
            ("instruction_profile", self.instruction_profile),
        ):
            if not value or value.strip() != value:
                raise ValueError(f"{name} must be a non-empty trimmed string")
        if not self.success_criteria or any(
            not item or item.strip() != item for item in self.success_criteria
        ):
            raise ValueError("success_criteria must contain trimmed values")
        if len(self.success_criteria) > 20 or len(set(self.success_criteria)) != len(self.success_criteria):
            raise ValueError("success_criteria must contain at most 20 unique values")
        if any(len(item) > 2048 for item in self.success_criteria):
            raise ValueError("success_criteria item is too long")
        if not isinstance(self.result_schema, dict) or not self.result_schema:
            raise ValueError("result_schema must be a non-empty object")
        if len(self.objective) > 16_384:
            raise ValueError("objective is too long")
        if not self.original_request or self.original_request.strip() != self.original_request:
            raise ValueError("original_request must be a non-empty trimmed string")
        if len(self.original_request) > 16_384:
            raise ValueError("original_request is too long")
        if not self.verification_method or self.verification_method.strip() != self.verification_method:
            raise ValueError("verification_method must be a non-empty trimmed string")
        if len(self.verification_method) > 16_384:
            raise ValueError("verification_method is too long")
        if not self.completion_conditions or any(
            not item or item.strip() != item for item in self.completion_conditions
        ):
            raise ValueError("completion_conditions must contain trimmed values")
        if len(self.completion_conditions) > 20 or len(set(self.completion_conditions)) != len(self.completion_conditions):
            raise ValueError("completion_conditions must contain at most 20 unique values")
        if any(len(item) > 2048 for item in self.completion_conditions):
            raise ValueError("completion_conditions item is too long")
        if any(not item or item.strip() != item for item in self.stop_conditions):
            raise ValueError("stop_conditions must contain trimmed values")
        if len(self.stop_conditions) > 20 or len(set(self.stop_conditions)) != len(self.stop_conditions):
            raise ValueError("stop_conditions must contain at most 20 unique values")
        if any(len(item) > 2048 for item in self.stop_conditions):
            raise ValueError("stop_conditions item is too long")
        if not self.goal_type or self.goal_type.strip() != self.goal_type:
            raise ValueError("goal_type must be a non-empty trimmed string")
        for value in (self.context_summary, self.expected_result, self.scope, self.source_requirements):
            if len(value) > 16_384:
                raise ValueError("goal context field is too long")
        if any(not item or item.strip() != item for item in self.exclusions):
            raise ValueError("exclusions must contain trimmed values")
        if len(self.exclusions) > 20 or len(set(self.exclusions)) != len(self.exclusions):
            raise ValueError("exclusions must contain at most 20 unique values")
        if any(len(item) > 2048 for item in self.exclusions):
            raise ValueError("exclusions item is too long")
        if len(set(self.requested_resource_ids)) != len(self.requested_resource_ids):
            raise ValueError("requested_resource_ids must be unique")


@dataclass(frozen=True, slots=True)
class AgentRunResult:
    run_id: str
    state: AgentRunState
    output: dict[str, object] | None = None
    failure_code: str | None = None
    failure_message: str | None = None

    def __post_init__(self) -> None:
        terminal = self.state in {
            AgentRunState.COMPLETED,
            AgentRunState.FAILED,
            AgentRunState.CANCELLED,
        }
        if not terminal:
            raise ValueError("AgentRunResult requires a terminal state")
        if self.state is AgentRunState.COMPLETED and self.output is None:
            raise ValueError("completed runs require output")
        if self.state is AgentRunState.FAILED and not self.failure_code:
            raise ValueError("failed runs require a failure code")
