"""Creates independent delivery intents after canonical terminal commit."""

from __future__ import annotations

from collections.abc import Callable
import json

from ..storage.agent_deliveries import AgentRunDeliveryRepository
from ..storage.agent_runs import StoredAgentRun
from .run_contract import AgentRunState


class CompletionDispatcher:
    def __init__(self, *, deliveries: AgentRunDeliveryRepository,
                 voice_session_active: Callable[[str], bool]) -> None:
        self._deliveries = deliveries
        self._voice_session_active = voice_session_active

    def record(self, run: StoredAgentRun) -> None:
        if run.state not in {AgentRunState.COMPLETED, AgentRunState.FAILED, AgentRunState.CANCELLED}:
            raise ValueError("completion delivery requires a terminal run")
        base = {
            "runId": run.request.run_id,
            "originSessionId": run.request.origin_id,
            "state": run.state.value,
            "objective": run.request.objective,
            "originalRequest": run.request.original_request,
            "verificationMethod": run.request.verification_method,
            "completionConditions": list(run.request.completion_conditions),
            "stopConditions": list(run.request.stop_conditions),
            "output": run.output,
            "failureCode": run.failure_code,
            "failureMessage": run.failure_message,
            "completedAt": run.completed_at,
        }
        voice_context = json.dumps({
            "runId": run.request.run_id,
            "originSessionId": run.request.origin_id,
            "state": run.state.value,
            "objective": run.request.objective[:4096],
            "originalRequest": run.request.original_request[:4096],
            "failureCode": run.failure_code,
            "failureMessage": run.failure_message[:1024] if run.failure_message else None,
            "completedAt": run.completed_at,
            "output": _voice_output(run.output),
        }, separators=(",", ":"), sort_keys=True)
        notification_context = json.dumps(base, separators=(",", ":"), sort_keys=True)
        existing = {item.channel for item in self._deliveries.list_for_run(run.request.run_id)}
        if "voice" not in existing:
            voice_state = ("pending" if self._voice_session_active(run.request.origin_id)
                           else "skipped_session_inactive")
            self._deliveries.create(run_id=run.request.run_id, channel="voice",
                                    state=voice_state, context_json=voice_context)
        if "notification" not in existing:
            self._deliveries.create(run_id=run.request.run_id, channel="notification",
                                    state="pending", context_json=notification_context)


def _voice_output(output: dict[str, object] | None) -> dict[str, object] | None:
    if output is None:
        return None
    encoded = json.dumps(output, separators=(",", ":"), sort_keys=True)
    if len(encoded.encode("utf-8")) <= 32_768:
        return output
    summary = output.get("summary")
    verification = output.get("verification")
    return {
        "summary": str(summary)[:8192] if summary is not None else "Result is available in the run record.",
        "verification": verification if _encoded_size(verification) <= 16_384 else None,
        "workspaceReferences": sorted(_workspace_references(output))[:64],
        "resultTruncatedForVoice": True,
    }


def _encoded_size(value: object) -> int:
    return len(json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8"))


def _workspace_references(value: object) -> set[str]:
    found: set[str] = set()
    if isinstance(value, str) and value.startswith("workspace://"):
        found.add(value)
    elif isinstance(value, dict):
        for item in value.values():
            found.update(_workspace_references(item))
    elif isinstance(value, list):
        for item in value:
            found.update(_workspace_references(item))
    return found
