"""Authenticated management configuration and audit routes for Background Agent."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..agents.audience import AgentKind
from ..background_agent.run_contract import AutonomyProfile, ExecutionRecipe, RunLimits
from ..background_agent.run_state import RunLifecycle
from ..security.pairing import PairingAuthority
from ..storage.agent_runs import AgentRunRepository, StoredAgentRun
from ..storage.agent_deliveries import AgentRunDeliveryRepository
from ..storage.background_agent_settings import BackgroundAgentSettingsRepository
from ..tools.catalog import ToolCatalog
from ..background_agent.mcp_gateway import BackgroundMcpGateway
from ..background_agent.progress import explain_failure, project_progress

if TYPE_CHECKING:
    from .routes import RouteRequest


class BackgroundAgentRoutes:
    def __init__(self, *, settings: BackgroundAgentSettingsRepository,
                 runs: AgentRunRepository, catalog: ToolCatalog,
                 deliveries: AgentRunDeliveryRepository) -> None:
        self._settings = settings
        self._runs = runs
        self._lifecycle = RunLifecycle(runs)
        self._catalog = catalog
        self._deliveries = deliveries
        self._gateway: BackgroundMcpGateway | None = None

    def attach_gateway(self, gateway: BackgroundMcpGateway) -> None:
        self._gateway = gateway

    def handle_get(self, req: "RouteRequest", pairing: PairingAuthority | None) -> bool:
        path = req.path.split("?", 1)[0]
        if path == "/v1/host/background-agent/notifications":
            visible = self._deliveries.visible_notification_run_ids()
            values = []
            for run_id in visible:
                try:
                    run = self._runs.get(run_id)
                except KeyError:
                    continue
                values.append(_run_view(run, self._runs.events(run_id)))
            req.respond_json(200, {"runs": values})
            return True
        if path == "/v1/voice/completions/next":
            session_id = req.headers.get("X-ReSono-Voice-Session", "").strip()
            delivery = self._deliveries.claim_voice(session_id)
            if delivery is None:
                req.respond_json(200, {"completion": None})
            else:
                import json
                req.respond_json(200, {"completion": json.loads(delivery.context_json)})
            return True
        base = "/v1/management/background-agent"
        if path != base and not path.startswith(base + "/"):
            return False
        if not _session(req, pairing, mutation=False):
            return True
        if path == base:
            settings = self._settings.get()
            req.respond_json(200, {"settings": _settings_view(settings),
                                   "tools": [_tool_view(item, settings.allowed_tool_names)
                                             for item in self._catalog.definitions_for(AgentKind.TEXT)]})
            return True
        if path == base + "/runs":
            req.respond_json(200, {"runs": [
                _run_view(item, self._runs.events(item.request.run_id))
                for item in self._runs.list_recent()
            ]})
            return True
        prefix = base + "/runs/"
        if path.startswith(prefix):
            run_id = path[len(prefix):]
            if "/" in run_id or not run_id:
                return _not_found(req)
            try:
                run = self._runs.get(run_id)
            except KeyError:
                return _not_found(req)
            events = self._runs.events(run_id)
            value = _run_view(run, events)
            value["events"] = [_event_view(item) for item in events]
            req.respond_json(200, value)
            return True
        return _not_found(req)

    def handle_post(self, req: "RouteRequest", pairing: PairingAuthority | None) -> bool:
        path = req.path.split("?", 1)[0]
        native_prefix = "/v1/host/background-agent/notifications/"
        if path.startswith(native_prefix) and path.endswith("/view"):
            run_id = path[len(native_prefix):-len("/view")]
            if not run_id or "/" in run_id:
                return _not_found(req)
            acknowledged = self._deliveries.acknowledge_notification(run_id)
            req.respond_json(200 if acknowledged else 404,
                             {"runId": run_id, "acknowledged": acknowledged})
            return True
        if path == "/v1/voice/completions/ack":
            payload = req.request_json(max_bytes=4096)
            if payload is None:
                return True
            session_id = req.headers.get("X-ReSono-Voice-Session", "").strip()
            delivered = self._deliveries.acknowledge_voice(
                run_id=str(payload.get("runId", "")).strip(),
                session_id=session_id,
            )
            req.respond_json(200 if delivered else 409, {"delivered": delivered})
            return True
        mcp_prefix = "/v1/background-agent/mcp/"
        if path.startswith(mcp_prefix):
            if self._gateway is None:
                return _not_found(req)
            payload = req.request_json(max_bytes=65_536)
            if payload is None:
                return True
            result = self._gateway.handle(
                path[len(mcp_prefix):], payload,
                session_id=req.headers.get("Mcp-Session-Id"),
                protocol_version=req.headers.get("MCP-Protocol-Version"),
            )
            headers = {"Mcp-Session-Id": result.session_id} if result.session_id else None
            if result.payload is None:
                req.respond_empty(result.status, headers=headers)
            else:
                req.respond_json(result.status, result.payload, headers=headers)
            return True
        base = "/v1/management/background-agent"
        if path != base and not path.startswith(base + "/"):
            return False
        if not _session(req, pairing, mutation=True):
            return True
        if path == base + "/settings":
            payload = req.request_json(max_bytes=16_384)
            if payload is None:
                return True
            try:
                available = {item.name for item in self._catalog.definitions_for(AgentKind.TEXT)}
                raw_names = payload.get("allowedTools", [])
                if not isinstance(raw_names, list) or any(not isinstance(item, str) for item in raw_names):
                    raise ValueError("allowedTools must be a list of tool names")
                names = frozenset(raw_names)
                if names - available:
                    raise ValueError("One or more selected tools are unavailable to Background Agent")
                raw_limits = payload.get("limits", {})
                if not isinstance(raw_limits, dict):
                    raise ValueError("limits must be an object")
                limits = RunLimits(
                    max_seconds=int(raw_limits.get("maxSeconds", 300)),
                    max_model_turns=int(raw_limits.get("maxTurns", raw_limits.get("maxModelTurns", 24))),
                    max_tool_calls=int(raw_limits.get("maxToolCalls", 40)),
                    max_review_rounds=int(raw_limits.get("maxReviewRounds", 2)),
                    max_workspace_bytes=int(raw_limits.get("maxWorkspaceBytes", 8 * 1024 * 1024)),
                )
                saved = self._settings.save(
                    enabled=payload.get("enabled") is True,
                    autonomy=AutonomyProfile(str(payload.get("autonomy", "limited"))),
                    reasoning_effort=str(payload.get("reasoningEffort", "medium")),
                    default_recipe=ExecutionRecipe(str(payload.get("defaultRecipe", "self_review_v1"))),
                    allowed_tool_names=names, limits=limits,
                )
                req.respond_json(200, _settings_view(saved))
            except (TypeError, ValueError) as error:
                req.respond_json(400, {"error": {"code": "invalid_background_agent_settings", "message": str(error)}})
            return True
        prefix = base + "/runs/"
        if path.startswith(prefix) and path.endswith("/cancel"):
            run_id = path[len(prefix):-len("/cancel")]
            try:
                req.respond_json(202, _run_view(self._lifecycle.request_cancellation(run_id)))
            except KeyError:
                return _not_found(req)
            return True
        return _not_found(req)

    def handle_delete(self, req: "RouteRequest", pairing: PairingAuthority | None) -> bool:
        path = req.path.split("?", 1)[0]
        prefix = "/v1/management/background-agent/runs/"
        if not path.startswith(prefix):
            return False
        if not _session(req, pairing, mutation=True):
            return True
        run_id = path[len(prefix):]
        if "/" in run_id or not run_id:
            return _not_found(req)
        if self._runs.delete_terminal(run_id):
            req.respond_json(200, {"runId": run_id, "deleted": True})
        else:
            req.respond_json(409, {"error": {"code": "run_not_terminal", "message": "Only a completed, failed, or cancelled run can be deleted."}})
        return True


def _settings_view(item) -> dict[str, object]:
    return {"enabled": item.enabled, "autonomy": item.autonomy.value,
            "reasoningEffort": item.reasoning_effort, "defaultRecipe": item.default_recipe.value,
            "allowedTools": sorted(item.allowed_tool_names),
            "limits": {"maxSeconds": item.limits.max_seconds, "maxTurns": item.limits.max_model_turns,
                       "maxToolCalls": item.limits.max_tool_calls, "maxReviewRounds": item.limits.max_review_rounds,
                       "maxWorkspaceBytes": item.limits.max_workspace_bytes}, "updatedAt": item.updated_at}


def _tool_view(item, granted: frozenset[str]) -> dict[str, object]:
    group = item.audience_resource.stable_id if item.audience_resource is not None else "other"
    return {"name": item.name, "description": item.description, "effect": item.effect_class,
            "group": group, "allowed": item.name in granted}


def _run_view(item: StoredAgentRun, events=()) -> dict[str, object]:
    progress = project_progress(item.state, item.request.recipe, events)
    reasoning_entries = [
        _event_view(event) for event in events
        if event.event_type in {"reasoning_summary", "agent_evidence"}
    ]
    return {"runId": item.request.run_id, "invocationType": item.request.invocation_type.value,
            "originId": item.request.origin_id, "objective": item.request.objective,
            "recipe": item.request.recipe.value,
            "originalRequest": item.request.original_request,
            "verificationMethod": item.request.verification_method,
            "completionConditions": list(item.request.completion_conditions),
            "stopConditions": list(item.request.stop_conditions),
            "state": item.state.value, "cancellationRequested": item.cancellation_requested,
            "output": item.output, "failure": ({"code": item.failure_code, "message": item.failure_message}
            if item.failure_code else None), "createdAt": item.created_at, "updatedAt": item.updated_at,
            "completedAt": item.completed_at,
            "failureExplanation": explain_failure(item),
            "reasoningEntries": reasoning_entries,
            "progress": {"phase": progress.phase, "label": progress.label,
                         "fraction": progress.fraction, "active": progress.active,
                         "tone": progress.tone, "activity": progress.activity,
                         "modelTurns": progress.model_turns, "toolCalls": progress.tool_calls,
                         "timeline": list(progress.timeline)}}


def _event_view(item) -> dict[str, object]:
    return {"index": item.event_index, "type": item.event_type, "state": item.state.value,
            "detail": item.detail, "createdAt": item.created_at}


def _session(req, pairing, *, mutation: bool) -> bool:
    if pairing is None:
        req.respond_json(503, {"error": {"code": "management_unavailable", "message": "Management pairing is unavailable."}})
        return False
    return req.browser_session(pairing, mutation=mutation) is not None


def _not_found(req) -> bool:
    req.respond_json(404, {"error": {"code": "not_found", "message": "Background Agent run was not found."}})
    return True
