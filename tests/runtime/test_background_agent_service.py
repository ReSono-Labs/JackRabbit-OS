from __future__ import annotations

from pathlib import Path
import time

from resono_runtime.agents.delegation import DelegationRequest
from resono_runtime.background_agent.run_contract import AgentRunState, AutonomyProfile, ExecutionRecipe, RunLimits
from resono_runtime.background_agent.run_state import RunLifecycle
from resono_runtime.background_agent.service import BackgroundAgentService, PreparedRun
from resono_runtime.storage.agent_runs import AgentRunRepository
from resono_runtime.storage.background_agent_settings import BackgroundAgentSettings
from resono_runtime.storage.database import RuntimeDatabase


class _Settings:
    def get(self) -> BackgroundAgentSettings:
        return BackgroundAgentSettings(
            True, AutonomyProfile.LIMITED, "medium", ExecutionRecipe.DIRECT,
            frozenset(), RunLimits(), "now",
        )


class _CompletingLoop:
    def __init__(self, runs: AgentRunRepository) -> None:
        self._lifecycle = RunLifecycle(runs)

    def execute(self, request, *, already_accepted: bool = False):
        self._lifecycle.move(request.run_id, AgentRunState.QUEUED, event_type="queued")
        self._lifecycle.move(request.run_id, AgentRunState.RUNNING, event_type="running")
        return self._lifecycle.move(
            request.run_id, AgentRunState.COMPLETED,
            event_type="completed", output={"ok": True},
        )


class _CompletionDispatcher:
    def __init__(self) -> None:
        self.runs = []

    def record(self, run) -> None:
        self.runs.append(run)


def _request(goal_id: str) -> DelegationRequest:
    return DelegationRequest(
        "goal", goal_id, "Complete the goal", ("Return ok",), {"type": "object"},
        recipe="direct_v1",
    )


def _wait(runs: AgentRunRepository, run_id: str, state: AgentRunState) -> None:
    for _ in range(100):
        if runs.get(run_id).state is state:
            return
        time.sleep(0.01)
    raise AssertionError(f"run did not reach {state.value}")


def test_goal_origin_is_released_after_completion(tmp_path: Path) -> None:
    database = RuntimeDatabase(tmp_path / "runtime.sqlite3")
    database.migrate()
    runs = AgentRunRepository(database)
    service = BackgroundAgentService(
        settings=_Settings(), runs=runs,
        loop_factory=lambda _request: PreparedRun(_CompletingLoop(runs)),
        completion_dispatcher=_CompletionDispatcher(),
    )
    service.start()
    first = service.submit(_request("goal-1"))
    _wait(runs, first.run_id, AgentRunState.COMPLETED)
    second = service.submit(_request("goal-1"))
    _wait(runs, second.run_id, AgentRunState.COMPLETED)
    service.stop()


def test_factory_failure_does_not_kill_worker(tmp_path: Path) -> None:
    database = RuntimeDatabase(tmp_path / "runtime.sqlite3")
    database.migrate()
    runs = AgentRunRepository(database)
    attempts = 0

    def factory(_request):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("executor unavailable")
        return PreparedRun(_CompletingLoop(runs))

    service = BackgroundAgentService(
        settings=_Settings(), runs=runs, loop_factory=factory,
        completion_dispatcher=_CompletionDispatcher(),
    )
    service.start()
    first = service.submit(_request("goal-1"))
    _wait(runs, first.run_id, AgentRunState.FAILED)
    second = service.submit(_request("goal-1"))
    _wait(runs, second.run_id, AgentRunState.COMPLETED)
    service.stop()


def test_cleanup_failure_does_not_kill_worker(tmp_path: Path) -> None:
    database = RuntimeDatabase(tmp_path / "runtime.sqlite3")
    database.migrate()
    runs = AgentRunRepository(database)
    cleanups = 0

    def factory(_request):
        def cleanup():
            nonlocal cleanups
            cleanups += 1
            if cleanups == 1:
                raise RuntimeError("cleanup failed")
        return PreparedRun(_CompletingLoop(runs), cleanup)

    service = BackgroundAgentService(
        settings=_Settings(), runs=runs, loop_factory=factory,
        completion_dispatcher=_CompletionDispatcher(),
    )
    service.start()
    first = service.submit(_request("goal-1"))
    _wait(runs, first.run_id, AgentRunState.COMPLETED)
    second = service.submit(_request("goal-2"))
    _wait(runs, second.run_id, AgentRunState.COMPLETED)
    service.stop()
    assert cleanups == 2
