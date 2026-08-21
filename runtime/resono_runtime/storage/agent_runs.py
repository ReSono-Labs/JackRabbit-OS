"""Durable storage owned exclusively by the removable background-agent module."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json

from ..background_agent.run_contract import AgentRunRequest, AgentRunState
from .database import RuntimeDatabase


@dataclass(frozen=True, slots=True)
class StoredAgentRun:
    request: AgentRunRequest
    state: AgentRunState
    cancellation_requested: bool
    output: dict[str, object] | None
    failure_code: str | None
    failure_message: str | None
    created_at: str
    updated_at: str
    completed_at: str | None


@dataclass(frozen=True, slots=True)
class AgentRunEvent:
    run_id: str
    event_index: int
    event_type: str
    state: AgentRunState
    detail: dict[str, object]
    created_at: str


class AgentRunRepository:
    def __init__(self, database: RuntimeDatabase) -> None:
        self._database = database

    def create(self, request: AgentRunRequest) -> StoredAgentRun:
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "INSERT INTO background_agent_runs(run_id, invocation_type, origin_id, objective, instruction_profile, success_criteria_json, result_schema_json, requested_resource_ids_json, recipe, autonomy, limits_json, state, goal_type, context_summary, expected_result, scope, exclusions_json, source_requirements, workspace_destination, original_request, verification_method, completion_conditions_json, stop_conditions_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, strftime('%Y-%m-%dT%H:%M:%fZ', 'now'), strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))",
                (request.run_id, request.invocation_type.value, request.origin_id, request.objective,
                 request.instruction_profile, _json(request.success_criteria), _json(request.result_schema),
                 _json(request.requested_resource_ids), request.recipe.value, request.autonomy.value, _json(asdict(request.limits)),
                 AgentRunState.ACCEPTED.value, request.goal_type, request.context_summary,
                 request.expected_result, request.scope, _json(request.exclusions),
                 request.source_requirements, request.workspace_destination,
                 request.original_request, request.verification_method,
                 _json(request.completion_conditions), _json(request.stop_conditions)),
            )
            self._append_event(connection, request.run_id, "accepted", AgentRunState.ACCEPTED, {})
            connection.commit()
        return self.get(request.run_id)

    def get(self, run_id: str) -> StoredAgentRun:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM background_agent_runs WHERE run_id = ?", (run_id,)).fetchone()
        if row is None:
            raise KeyError(run_id)
        return _run(row)

    def list_recent(self, *, limit: int = 50) -> tuple[StoredAgentRun, ...]:
        if limit < 1 or limit > 200:
            raise ValueError("limit must be between 1 and 200")
        with self._database.connect() as connection:
            rows = connection.execute("SELECT * FROM background_agent_runs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return tuple(_run(row) for row in rows)

    def terminal_missing_delivery(self) -> tuple[StoredAgentRun, ...]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT r.* FROM background_agent_runs r "
                "LEFT JOIN background_agent_deliveries d ON d.run_id = r.run_id "
                "WHERE r.state IN (?, ?, ?) GROUP BY r.run_id HAVING COUNT(d.channel) < 2 "
                "ORDER BY r.completed_at",
                (AgentRunState.COMPLETED.value, AgentRunState.FAILED.value,
                 AgentRunState.CANCELLED.value),
            ).fetchall()
        return tuple(_run(row) for row in rows)

    def events(self, run_id: str) -> tuple[AgentRunEvent, ...]:
        with self._database.connect() as connection:
            rows = connection.execute("SELECT * FROM background_agent_run_events WHERE run_id = ? ORDER BY event_index", (run_id,)).fetchall()
        return tuple(_event(row) for row in rows)

    def record_event(self, run_id: str, event_type: str, detail: dict[str, object]) -> AgentRunEvent:
        current = self.get(run_id)
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._append_event(connection, run_id, event_type, current.state, detail)
            connection.commit()
        return self.events(run_id)[-1]

    def transition(self, run_id: str, *, expected: AgentRunState, target: AgentRunState,
                   event_type: str, detail: dict[str, object] | None = None,
                   output: dict[str, object] | None = None, failure_code: str | None = None,
                   failure_message: str | None = None) -> StoredAgentRun:
        terminal = target in _TERMINAL_STATES
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            changed = connection.execute(
                "UPDATE background_agent_runs SET state = ?, output_json = ?, failure_code = ?, failure_message = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now'), completed_at = CASE WHEN ? THEN strftime('%Y-%m-%dT%H:%M:%fZ', 'now') ELSE completed_at END WHERE run_id = ? AND state = ?",
                (target.value, _json(output) if output is not None else None, failure_code,
                 failure_message, int(terminal), run_id, expected.value),
            ).rowcount
            if changed != 1:
                connection.rollback()
                raise ValueError("run state changed or run does not exist")
            self._append_event(connection, run_id, event_type, target, detail or {})
            connection.commit()
        return self.get(run_id)

    def request_cancellation(self, run_id: str) -> StoredAgentRun:
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT state, cancellation_requested FROM background_agent_runs WHERE run_id = ?", (run_id,)).fetchone()
            if row is None:
                connection.rollback()
                raise KeyError(run_id)
            state = AgentRunState(str(row["state"]))
            if state in _TERMINAL_STATES:
                connection.rollback()
                return self.get(run_id)
            if not bool(row["cancellation_requested"]):
                connection.execute("UPDATE background_agent_runs SET cancellation_requested = 1, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE run_id = ?", (run_id,))
                self._append_event(connection, run_id, "cancellation_requested", state, {})
            connection.commit()
        return self.get(run_id)

    def recover_interrupted(self) -> int:
        recoverable = tuple(state.value for state in _ACTIVE_STATES)
        placeholders = ",".join("?" for _ in recoverable)
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute(f"SELECT run_id, state FROM background_agent_runs WHERE state IN ({placeholders})", recoverable).fetchall()
            for row in rows:
                connection.execute("UPDATE background_agent_runs SET state = ?, failure_code = ?, failure_message = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now'), completed_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE run_id = ?", (AgentRunState.FAILED.value, "runtime_interrupted", "Runtime stopped before the run completed.", row["run_id"]))
                self._append_event(connection, str(row["run_id"]), "recovered_as_failed", AgentRunState.FAILED, {"previousState": str(row["state"])})
            connection.commit()
        return len(rows)

    def delete_terminal(self, run_id: str) -> bool:
        with self._database.connect() as connection:
            changed = connection.execute(
                "DELETE FROM background_agent_runs WHERE run_id = ? AND state IN (?, ?, ?)",
                (run_id, AgentRunState.COMPLETED.value, AgentRunState.FAILED.value,
                 AgentRunState.CANCELLED.value),
            ).rowcount
            connection.commit()
        return changed == 1

    @staticmethod
    def _append_event(connection, run_id: str, event_type: str, state: AgentRunState, detail: dict[str, object]) -> None:
        row = connection.execute("SELECT COALESCE(MAX(event_index), -1) + 1 AS next_index FROM background_agent_run_events WHERE run_id = ?", (run_id,)).fetchone()
        connection.execute("INSERT INTO background_agent_run_events(run_id, event_index, event_type, state, detail_json, created_at) VALUES (?, ?, ?, ?, ?, strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))", (run_id, int(row["next_index"]), event_type, state.value, _json(detail)))


_TERMINAL_STATES = frozenset({AgentRunState.COMPLETED, AgentRunState.FAILED, AgentRunState.CANCELLED})
_ACTIVE_STATES = frozenset({AgentRunState.QUEUED, AgentRunState.RUNNING, AgentRunState.REVIEWING, AgentRunState.REPAIRING})


def _json(value: object) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def _run(row) -> StoredAgentRun:
    from ..background_agent.run_contract import AutonomyProfile, ExecutionRecipe, InvocationType, RunLimits
    request = AgentRunRequest(
        run_id=str(row["run_id"]), invocation_type=InvocationType(str(row["invocation_type"])),
        origin_id=str(row["origin_id"]), objective=str(row["objective"]),
        instruction_profile=str(row["instruction_profile"]),
        success_criteria=tuple(json.loads(str(row["success_criteria_json"]))),
        result_schema=json.loads(str(row["result_schema_json"])),
        requested_resource_ids=tuple(json.loads(str(row["requested_resource_ids_json"]))),
        recipe=ExecutionRecipe(str(row["recipe"])),
        autonomy=AutonomyProfile(str(row["autonomy"])),
        limits=RunLimits(**json.loads(str(row["limits_json"]))),
        goal_type=str(row["goal_type"]), context_summary=str(row["context_summary"]),
        expected_result=str(row["expected_result"]), scope=str(row["scope"]),
        exclusions=tuple(json.loads(str(row["exclusions_json"]))),
        source_requirements=str(row["source_requirements"]),
        workspace_destination=(str(row["workspace_destination"])
                               if row["workspace_destination"] else None),
        original_request=(str(row["original_request"]) if row["original_request"]
                          else str(row["objective"])),
        verification_method=(str(row["verification_method"])
            if row["verification_method"] else
            "Compare the result against every supplied success criterion using available evidence."),
        completion_conditions=(tuple(json.loads(str(row["completion_conditions_json"])))
            if json.loads(str(row["completion_conditions_json"])) else
            tuple(json.loads(str(row["success_criteria_json"])))),
        stop_conditions=tuple(json.loads(str(row["stop_conditions_json"]))),
    )
    return StoredAgentRun(request, AgentRunState(str(row["state"])), bool(row["cancellation_requested"]), json.loads(str(row["output_json"])) if row["output_json"] else None, row["failure_code"], row["failure_message"], str(row["created_at"]), str(row["updated_at"]), str(row["completed_at"]) if row["completed_at"] else None)


def _event(row) -> AgentRunEvent:
    return AgentRunEvent(str(row["run_id"]), int(row["event_index"]), str(row["event_type"]), AgentRunState(str(row["state"])), json.loads(str(row["detail_json"])), str(row["created_at"]))
