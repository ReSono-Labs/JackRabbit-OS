"""Bounded single-worker implementation of the stable delegation port."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import queue
import threading

from ..core.logging import runtime_logger

from ..agents.delegation import DelegationRequest, DelegationRun
from ..storage.agent_runs import AgentRunRepository, StoredAgentRun
from ..storage.background_agent_settings import BackgroundAgentSettingsRepository
from .adapters import GoalTask, from_goal
from .run_contract import AgentRunRequest, AgentRunState, ExecutionRecipe
from .execution import BackgroundAgentExecution
from .run_state import RunLifecycle
from .completion_dispatch import CompletionDispatcher


@dataclass(frozen=True, slots=True)
class PreparedRun:
    execution: BackgroundAgentExecution
    close: Callable[[], None] = lambda: None


RunLoopFactory = Callable[[AgentRunRequest], PreparedRun]


class BackgroundAgentService:
    def __init__(self, *, settings: BackgroundAgentSettingsRepository,
                 runs: AgentRunRepository, loop_factory: RunLoopFactory,
                 completion_dispatcher: CompletionDispatcher,
                 shutdown: Callable[[], None] = lambda: None,
                 queue_capacity: int = 8) -> None:
        if queue_capacity < 1 or queue_capacity > 64:
            raise ValueError("queue_capacity must be between 1 and 64")
        self._settings = settings
        self._runs = runs
        self._lifecycle = RunLifecycle(runs)
        self._loop_factory = loop_factory
        self._completion_dispatcher = completion_dispatcher
        self._shutdown = shutdown
        self._queue: queue.Queue[AgentRunRequest | None] = queue.Queue(maxsize=queue_capacity)
        self._origins: dict[tuple[str, str], str] = {}
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._log = runtime_logger()

    def start(self) -> None:
        with self._lock:
            if self._thread is not None:
                return
            self._thread = threading.Thread(target=self._work, name="resono-background-agent", daemon=True)
            self._thread.start()

    def stop(self) -> None:
        with self._lock:
            thread = self._thread
            if thread is None:
                return
            self._thread = None
        self._queue.put(None)
        thread.join(timeout=5.0)

    def submit(self, request: DelegationRequest) -> DelegationRun:
        settings = self._settings.get()
        recipe = ExecutionRecipe(request.recipe) if request.recipe else None
        if request.origin_kind != "goal":
            raise ValueError("origin_kind must be goal")
        internal = from_goal(GoalTask(
            request.origin_id, request.objective, request.success_criteria,
            request.result_schema, request.requested_resource_ids, recipe,
            request.goal_type, request.context_summary, request.expected_result,
            request.scope, request.exclusions, request.source_requirements,
            request.workspace_destination, request.original_request,
            request.verification_method, request.completion_conditions,
            request.stop_conditions,
        ), settings)
        origin = (request.origin_kind, request.origin_id)
        with self._lock:
            prior_run_id = self._origins.get(origin)
            if prior_run_id is not None:
                prior = self._runs.get(prior_run_id)
                if prior.state in {AgentRunState.COMPLETED, AgentRunState.FAILED, AgentRunState.CANCELLED}:
                    self._origins.pop(origin, None)
                else:
                    raise RuntimeError("This origin already has delegated work in progress")
            self._origins[origin] = internal.run_id
        try:
            stored = self._lifecycle.accept(internal)
            self._queue.put_nowait(internal)
        except Exception:
            with self._lock:
                if self._origins.get(origin) == internal.run_id:
                    self._origins.pop(origin, None)
            raise
        return _view(stored)

    def inspect(self, run_id: str) -> DelegationRun:
        return _view(self._runs.get(run_id))

    def cancel(self, run_id: str) -> DelegationRun:
        return _view(self._lifecycle.request_cancellation(run_id))

    def recover_interrupted(self) -> int:
        count = self._runs.recover_interrupted()
        for run in self._runs.terminal_missing_delivery():
            self._record_completion(run)
        return count

    def _work(self) -> None:
        while True:
            request = self._queue.get()
            if request is None:
                try:
                    self._shutdown()
                finally:
                    self._queue.task_done()
                return
            try:
                prepared = self._loop_factory(request)
            except Exception as error:
                try:
                    self._lifecycle.move(
                        request.run_id, AgentRunState.QUEUED,
                        event_type="executor_initialization_started",
                    )
                    terminal = self._lifecycle.move(
                        request.run_id, AgentRunState.FAILED,
                        event_type="executor_initialization_failed",
                        failure_code="executor_initialization_failed",
                        failure_message=str(error)[:1024],
                    )
                    self._record_completion(terminal)
                except Exception:
                    self._log.exception("background_agent.initialization_failure_commit_failed")
            else:
                try:
                    try:
                        terminal = prepared.execution.execute(request, already_accepted=True)
                    except Exception as error:
                        current = self._runs.get(request.run_id)
                        if current.state in {
                            AgentRunState.COMPLETED,
                            AgentRunState.FAILED,
                            AgentRunState.CANCELLED,
                        }:
                            terminal = current
                        else:
                            terminal = self._lifecycle.move(
                                request.run_id,
                                AgentRunState.FAILED,
                                event_type="executor_failed",
                                failure_code="executor_failed",
                                failure_message=str(error)[:1024],
                            )
                        self._log.exception(
                            "background_agent.executor_failed",
                            extra={"runId": request.run_id},
                        )
                    self._record_completion(terminal)
                finally:
                    try:
                        prepared.close()
                    except Exception:
                        # Cleanup failure is recorded without killing the single
                        # worker or changing an already committed terminal result.
                        self._log.exception(
                            "background_agent.cleanup_failed",
                            extra={"runId": request.run_id},
                        )
            finally:
                with self._lock:
                    origin = (request.invocation_type.value, request.origin_id)
                    if self._origins.get(origin) == request.run_id:
                        self._origins.pop(origin, None)
                self._queue.task_done()

    def _record_completion(self, terminal: StoredAgentRun) -> None:
        try:
            self._completion_dispatcher.record(terminal)
        except Exception:
            self._log.exception(
                "background_agent.completion_delivery_record_failed",
                extra={"runId": terminal.request.run_id, "state": terminal.state.value},
            )


def _view(item: StoredAgentRun) -> DelegationRun:
    return DelegationRun(
        item.request.run_id, item.request.invocation_type.value, item.request.origin_id,
        item.state.value, item.request.recipe.value, item.output,
        item.failure_code, item.failure_message,
    )
