"""Typed instruction assembly; adapters supply purpose without changing the engine."""

from __future__ import annotations

import json

from .run_contract import AgentRunRequest
from ..agents.primary_context import PrimaryAgentContext


def worker_instructions(request: AgentRunRequest, context: PrimaryAgentContext | None = None) -> str:
    base = (
        "You are the ReSono Background Agent running through the OpenAI Agents SDK. Own the complete "
        "reason-act-check loop for the supplied goal. Use only granted tools, work inside the supplied "
        "workspace, inspect actual artifacts, and correct deficiencies you can resolve before returning. "
        "Completion conditions are successful end states. Stop conditions are exceptional blockers and "
        "must never be treated as successful completion. Return the typed BackgroundAgentOutput required "
        "by the SDK. Set status complete only when the requested result and required artifacts exist and "
        "have been checked. Return safe artifact references, requirement outcomes, unresolved issues, a "
        "verification summary, and concise phase evidence for the user-facing run record."
    )
    return base if context is None or not context.rendered_context else base + "\n\n" + context.rendered_context


def worker_input(request: AgentRunRequest) -> str:
    envelope: dict[str, object] = {
        "invocationType": request.invocation_type.value,
        "originId": request.origin_id,
        "instructionProfile": request.instruction_profile,
        "executionRecipe": request.recipe.value,
        "objective": request.objective,
        "originalRequest": request.original_request,
        "successCriteria": list(request.success_criteria),
        "verificationMethod": request.verification_method,
        "completionConditions": list(request.completion_conditions),
        "stopConditions": list(request.stop_conditions),
        "resourceIds": list(request.requested_resource_ids),
        "goalType": request.goal_type,
        "context": request.context_summary,
        "expectedResult": request.expected_result,
        "scope": request.scope,
        "exclusions": list(request.exclusions),
        "sourceRequirements": request.source_requirements,
        "workspaceDestination": request.workspace_destination,
    }
    return json.dumps(envelope, separators=(",", ":"), sort_keys=True)
