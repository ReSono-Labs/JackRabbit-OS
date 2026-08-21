"""Trusted request adapters into one provider-neutral background-agent contract."""

from __future__ import annotations

from dataclasses import dataclass
import secrets

from ..storage.background_agent_settings import BackgroundAgentSettings
from .run_contract import AgentRunRequest, ExecutionRecipe, InvocationType


@dataclass(frozen=True, slots=True)
class GoalTask:
    goal_id: str
    objective: str
    success_criteria: tuple[str, ...]
    result_schema: dict[str, object]
    requested_resource_ids: tuple[str, ...] = ()
    recipe: ExecutionRecipe | None = None
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


def from_goal(goal: GoalTask, settings: BackgroundAgentSettings) -> AgentRunRequest:
    return _request(
        invocation_type=InvocationType.GOAL,
        origin_id=_required(goal.goal_id, "goal_id"),
        objective=goal.objective,
        success_criteria=goal.success_criteria,
        result_schema=goal.result_schema,
        requested_resource_ids=goal.requested_resource_ids,
        settings=settings,
        instruction_profile="goal_task_v1",
        recipe=goal.recipe or settings.default_recipe,
        goal_type=goal.goal_type, context_summary=goal.context_summary,
        expected_result=goal.expected_result, scope=goal.scope,
        exclusions=goal.exclusions, source_requirements=goal.source_requirements,
        workspace_destination=goal.workspace_destination,
        original_request=goal.original_request,
        verification_method=goal.verification_method,
        completion_conditions=goal.completion_conditions,
        stop_conditions=goal.stop_conditions,
    )


def _request(*, invocation_type: InvocationType, origin_id: str, objective: str,
             success_criteria: tuple[str, ...], result_schema: dict[str, object],
             requested_resource_ids: tuple[str, ...], settings: BackgroundAgentSettings,
             instruction_profile: str, recipe: ExecutionRecipe, goal_type: str,
             context_summary: str, expected_result: str, scope: str,
             exclusions: tuple[str, ...], source_requirements: str,
             workspace_destination: str | None, original_request: str,
             verification_method: str,
             completion_conditions: tuple[str, ...],
             stop_conditions: tuple[str, ...]) -> AgentRunRequest:
    if not settings.enabled:
        raise PermissionError("Background Agent is disabled")
    return AgentRunRequest(
        run_id=secrets.token_hex(16), invocation_type=invocation_type,
        origin_id=origin_id, objective=objective.strip(), instruction_profile=instruction_profile,
        success_criteria=success_criteria, result_schema=result_schema,
        requested_resource_ids=requested_resource_ids, autonomy=settings.autonomy,
        limits=settings.limits, recipe=recipe,
        goal_type=goal_type, context_summary=context_summary,
        expected_result=expected_result, scope=scope, exclusions=exclusions,
        source_requirements=source_requirements,
        workspace_destination=workspace_destination,
        original_request=(original_request.strip() or objective.strip()),
        verification_method=(verification_method.strip() or
            "Compare the result against every supplied success criterion using available evidence."),
        completion_conditions=(completion_conditions or success_criteria),
        stop_conditions=stop_conditions,
    )


def _required(value: str, name: str) -> str:
    if not value or value.strip() != value:
        raise ValueError(f"{name} must be a non-empty trimmed string")
    return value
