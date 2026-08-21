"""Legal lifecycle transitions for a durable background-agent run."""

from __future__ import annotations

from ..storage.agent_runs import AgentRunRepository, StoredAgentRun
from .run_contract import AgentRunRequest, AgentRunState


_TRANSITIONS = {
    AgentRunState.ACCEPTED: frozenset({AgentRunState.QUEUED, AgentRunState.CANCELLED}),
    AgentRunState.QUEUED: frozenset({AgentRunState.RUNNING, AgentRunState.CANCELLED, AgentRunState.FAILED}),
    AgentRunState.RUNNING: frozenset({AgentRunState.REVIEWING, AgentRunState.COMPLETED, AgentRunState.CANCELLED, AgentRunState.FAILED}),
    AgentRunState.REVIEWING: frozenset({AgentRunState.REPAIRING, AgentRunState.COMPLETED, AgentRunState.CANCELLED, AgentRunState.FAILED}),
    AgentRunState.REPAIRING: frozenset({AgentRunState.REVIEWING, AgentRunState.CANCELLED, AgentRunState.FAILED}),
}


class RunLifecycle:
    def __init__(self, repository: AgentRunRepository) -> None:
        self._repository = repository

    def accept(self, request: AgentRunRequest) -> StoredAgentRun:
        return self._repository.create(request)

    def move(self, run_id: str, target: AgentRunState, *, event_type: str,
             detail: dict[str, object] | None = None, output: dict[str, object] | None = None,
             failure_code: str | None = None, failure_message: str | None = None) -> StoredAgentRun:
        current = self._repository.get(run_id)
        if target not in _TRANSITIONS.get(current.state, frozenset()):
            raise ValueError(f"illegal run transition: {current.state.value} -> {target.value}")
        if target is AgentRunState.COMPLETED and output is None:
            raise ValueError("completed runs require output")
        if target is AgentRunState.FAILED and not failure_code:
            raise ValueError("failed runs require a failure code")
        return self._repository.transition(run_id, expected=current.state, target=target,
                                           event_type=event_type, detail=detail, output=output,
                                           failure_code=failure_code, failure_message=failure_message)

    def request_cancellation(self, run_id: str) -> StoredAgentRun:
        return self._repository.request_cancellation(run_id)

    def honour_cancellation(self, run_id: str) -> StoredAgentRun:
        current = self._repository.get(run_id)
        if not current.cancellation_requested:
            return current
        return self.move(run_id, AgentRunState.CANCELLED, event_type="cancelled")

    def recover_after_restart(self) -> int:
        return self._repository.recover_interrupted()
