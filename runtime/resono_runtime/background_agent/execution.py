"""Thin terminal boundary around one OpenAI Agents SDK Background Agent run."""

from __future__ import annotations

from ..agents.primary_context import PrimaryAgentContext
from ..storage.agent_runs import AgentRunRepository, StoredAgentRun
from .instructions import worker_input, worker_instructions
from .output_contract import BackgroundAgentOutput
from .run_contract import AgentRunRequest, AgentRunState
from .run_state import RunLifecycle
from .sdk_executor import AgentsSdkExecutor


class BackgroundAgentExecution:
    def __init__(self, *, repository: AgentRunRepository, executor: AgentsSdkExecutor,
                 context: PrimaryAgentContext | None = None) -> None:
        self._repository = repository
        self._lifecycle = RunLifecycle(repository)
        self._executor = executor
        self._context = context

    def execute(self, request: AgentRunRequest, *, already_accepted: bool = False) -> StoredAgentRun:
        run = self._repository.get(request.run_id) if already_accepted else self._lifecycle.accept(request)
        try:
            run = self._lifecycle.move(run.request.run_id, AgentRunState.QUEUED, event_type="queued")
            if run.cancellation_requested:
                return self._lifecycle.honour_cancellation(run.request.run_id)
            self._lifecycle.move(run.request.run_id, AgentRunState.RUNNING, event_type="sdk_agent_started")
            output = self._executor.run(
                instructions=worker_instructions(request, self._context),
                input_text=worker_input(request), max_turns=request.limits.max_model_turns,
            )
            if not isinstance(output, BackgroundAgentOutput):
                raise TypeError("Background Agent returned an invalid typed output")
            value = output.model_dump(mode="json")
            for evidence in output.phase_evidence:
                self._repository.record_event(request.run_id, "agent_evidence", {
                    "phase": evidence.phase, "summary": evidence.summary,
                })
            if output.status == "complete":
                return self._lifecycle.move(
                    request.run_id, AgentRunState.COMPLETED, event_type="completed",
                    output=value, detail={"artifactCount": len(output.artifact_references)},
                )
            message = output.summary if output.status == "blocked" else (
                output.unresolved_issues[0] if output.unresolved_issues else output.summary
            )
            return self._lifecycle.move(
                request.run_id, AgentRunState.FAILED, event_type="agent_incomplete",
                output=value, detail={"status": output.status, "message": message[:1024]},
                failure_code="agent_incomplete", failure_message=message[:1024],
            )
        except Exception as error:
            current = self._repository.get(request.run_id)
            if current.state in {AgentRunState.COMPLETED, AgentRunState.FAILED, AgentRunState.CANCELLED}:
                return current
            max_turns = error.__class__.__name__ == "MaxTurnsExceeded"
            timed_out = isinstance(error, TimeoutError)
            code = "max_turns_exceeded" if max_turns else "run_timeout" if timed_out else "execution_failed"
            message = (
                f"The agent reached its {request.limits.max_model_turns}-turn limit."
                if max_turns else f"The agent reached its {request.limits.max_seconds}-second time limit."
                if timed_out else str(error)[:1024]
            )
            detail: dict[str, object] = {"message": message}
            if max_turns:
                detail["configuredMaxTurns"] = request.limits.max_model_turns
            if timed_out:
                detail["configuredMaxSeconds"] = request.limits.max_seconds
            return self._lifecycle.move(
                request.run_id, AgentRunState.FAILED, event_type=code, detail=detail,
                failure_code=code, failure_message=message,
            )
