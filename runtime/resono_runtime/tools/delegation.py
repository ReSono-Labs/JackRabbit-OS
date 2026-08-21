"""Voice-facing goal tools over the stable replaceable delegation port."""

from __future__ import annotations

from ..agents.audience import AgentKind, AudienceResource, AudienceResourceKind
from ..agents.delegation import DelegationRequest, DelegationService
from .catalog import ToolCatalog
from .definitions import ToolDefinition, ToolInvocationContext, ToolInvocationResult
from ..background_agent.output_contract import background_output_schema


GOAL_TOOL_SET = AudienceResource(AudienceResourceKind.DOMAIN_TOOL_SET, "builtin.goal.v1")


def register_goal_tools(catalog: ToolCatalog, service: DelegationService, voice_modes=None) -> None:
    catalog.register(ToolDefinition(
        tool_id="builtin.goal.start.v1", name="goal_start",
        description="Start one bounded background goal when the user explicitly asks R1 to work on something beyond this live Voice turn. State the objective and concrete success criteria. Choose direct for simple work, self_review for normal checked work, or independent_review for important work needing a separate reviewer.",
        input_schema={"type": "object", "properties": {
            "objective": {"type": "string", "minLength": 1, "maxLength": 16384},
            "originalRequest": {"type": "string", "minLength": 1, "maxLength": 16384},
            "successCriteria": {"type": "array", "items": {"type": "string", "minLength": 1, "maxLength": 2048}, "minItems": 1, "maxItems": 20, "uniqueItems": True},
            "verificationMethod": {"type": "string", "minLength": 1, "maxLength": 16384},
            "completionConditions": {"type": "array", "items": {"type": "string", "minLength": 1, "maxLength": 2048}, "minItems": 1, "maxItems": 20, "uniqueItems": True},
            "stopConditions": {"type": "array", "items": {"type": "string", "minLength": 1, "maxLength": 2048}, "maxItems": 20, "uniqueItems": True},
            "recipe": {"type": "string", "enum": ["direct_v1", "self_review_v1", "independent_review_v1"]},
            "goalType": {"type": "string", "minLength": 1, "maxLength": 128},
            "context": {"type": "string", "maxLength": 16384},
            "expectedResult": {"type": "string", "maxLength": 16384},
            "scope": {"type": "string", "maxLength": 16384},
            "exclusions": {"type": "array", "items": {"type": "string", "minLength": 1, "maxLength": 2048}, "maxItems": 20, "uniqueItems": True},
            "sourceRequirements": {"type": "string", "maxLength": 16384},
            "workspaceDestination": {"type": "string", "pattern": "^workspace://"},
        }, "required": ["originalRequest", "objective", "successCriteria", "verificationMethod", "completionConditions", "stopConditions"], "additionalProperties": False},
        handler=lambda _args: ToolInvocationResult("A Voice session is required.", is_error=True),
        context_handler=lambda context, args: _start(service, context, args, voice_modes),
        effect_class="local_write", audience_resource=GOAL_TOOL_SET,
        available_to=lambda agent: agent is AgentKind.VOICE,
    ))
    catalog.register(ToolDefinition(
        tool_id="builtin.goal.inspect.v1", name="goal_inspect",
        description="Check the current state or final result of a background goal by its run ID.",
        input_schema=_run_schema(), handler=lambda args: _inspect(service, args),
        effect_class="read", audience_resource=GOAL_TOOL_SET,
        available_to=lambda agent: agent is AgentKind.VOICE,
    ))
    catalog.register(ToolDefinition(
        tool_id="builtin.goal.cancel.v1", name="goal_cancel",
        description="Request cancellation of an active background goal by its run ID when the user asks to stop it.",
        input_schema=_run_schema(), handler=lambda args: _cancel(service, args),
        effect_class="local_write", audience_resource=GOAL_TOOL_SET,
        available_to=lambda agent: agent is AgentKind.VOICE,
    ))


def _start(service: DelegationService, context: ToolInvocationContext,
           args: dict[str, object], voice_modes=None) -> ToolInvocationResult:
    if not context.voice_session_id:
        return ToolInvocationResult("A live Voice session is required to start a goal.", is_error=True)
    try:
        run = service.submit(DelegationRequest(
            origin_kind="goal", origin_id=context.voice_session_id,
            objective=str(args["objective"]).strip(),
            success_criteria=tuple(str(item).strip() for item in args["successCriteria"]),
            result_schema=background_output_schema(),
            recipe=str(args.get("recipe")) if args.get("recipe") else None,
            goal_type=str(args.get("goalType", "general")).strip(),
            context_summary=str(args.get("context", "")).strip(),
            expected_result=str(args.get("expectedResult", "")).strip(),
            scope=str(args.get("scope", "")).strip(),
            exclusions=tuple(str(item).strip() for item in args.get("exclusions", [])),
            source_requirements=str(args.get("sourceRequirements", "")).strip(),
            workspace_destination=(str(args["workspaceDestination"]).strip()
                                   if args.get("workspaceDestination") else None),
            original_request=str(args["originalRequest"]).strip(),
            verification_method=str(args["verificationMethod"]).strip(),
            completion_conditions=tuple(str(item).strip() for item in args["completionConditions"]),
            stop_conditions=tuple(str(item).strip() for item in args["stopConditions"]),
        ))
    except Exception as error:
        return ToolInvocationResult(str(error), is_error=True)
    return ToolInvocationResult(
        f"Goal accepted with run ID {run.run_id}.",
        {"runId": run.run_id, "state": run.state, "recipe": run.recipe},
        provider_session_update=(
            voice_modes.restore_primary(context.voice_session_id)
            if voice_modes is not None else None
        ),
    )


def _inspect(service: DelegationService, args: dict[str, object]) -> ToolInvocationResult:
    try:
        run = service.inspect(str(args["runId"]))
    except Exception as error:
        return ToolInvocationResult(str(error), is_error=True)
    return ToolInvocationResult(
        f"Goal is {run.state}.",
        {"runId": run.run_id, "state": run.state, "recipe": run.recipe,
         "output": run.output, "failureCode": run.failure_code,
         "failureMessage": run.failure_message},
    )


def _cancel(service: DelegationService, args: dict[str, object]) -> ToolInvocationResult:
    try:
        run = service.cancel(str(args["runId"]))
    except Exception as error:
        return ToolInvocationResult(str(error), is_error=True)
    return ToolInvocationResult(
        "Cancellation requested.", {"runId": run.run_id, "state": run.state},
    )


def _run_schema() -> dict[str, object]:
    return {"type": "object", "properties": {"runId": {"type": "string", "minLength": 1}},
            "required": ["runId"], "additionalProperties": False}

