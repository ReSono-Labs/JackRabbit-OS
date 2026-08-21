"""Background-agent adapter over the project's one canonical Agents SDK runner."""

from __future__ import annotations

import asyncio
import threading
import time
from collections.abc import Coroutine
from typing import Any, TypeVar

from ..agents.sdk_runner import run_agent_turn
from ..agents.sdk_runner import AgentTurnObservation
from ..storage.agent_runs import AgentRunRepository
from .output_contract import BackgroundAgentOutput


_Result = TypeVar("_Result")


class AsyncExecutionRuntime:
    """Own one event loop for every SDK phase in a prepared background run."""

    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._owner_thread: int | None = None

    def run(self, operation: Coroutine[Any, Any, _Result]) -> _Result:
        owner = threading.get_ident()
        if self._loop is None:
            self._loop = asyncio.new_event_loop()
            self._owner_thread = owner
        if self._owner_thread != owner or self._loop.is_closed():
            operation.close()
            raise RuntimeError("background-agent async runtime is unavailable")
        return self._loop.run_until_complete(operation)

    def close(self) -> None:
        loop = self._loop
        if loop is None:
            return
        if self._owner_thread != threading.get_ident():
            raise RuntimeError("background-agent async runtime must close on its owner thread")
        try:
            loop.run_until_complete(loop.shutdown_asyncgens())
        finally:
            loop.close()
            self._loop = None
            self._owner_thread = None


class ExecutionBudget:
    def __init__(self, *, max_seconds: int, max_turns: int) -> None:
        self._deadline = time.monotonic() + max_seconds
        self._max_turns = max_turns
        self._used_turns = 0
        self._lock = threading.Lock()

    def allocation(self, requested_turns: int) -> tuple[float, int]:
        with self._lock:
            seconds = self._deadline - time.monotonic()
            turns = min(requested_turns, self._max_turns - self._used_turns)
        if seconds <= 0:
            raise TimeoutError("background-agent run time limit reached")
        if turns <= 0:
            exception = type("MaxTurnsExceeded", (RuntimeError,), {})
            raise exception(f"Max turns ({self._max_turns}) exceeded")
        return seconds, turns

    def record_turns(self, count: int) -> None:
        with self._lock:
            self._used_turns = min(self._max_turns, self._used_turns + max(0, count))


class AgentsSdkExecutor:
    def __init__(self, *, api_key: str, model: str, base_url: str | None,
                 reasoning_effort: str, agent_name: str = "ReSono Background Agent",
                 mcp_url: str | None = None, local_api_token: str | None = None,
                 timeout_seconds: int = 300, run_id: str | None = None,
                 runs: AgentRunRepository | None = None,
                 budget: ExecutionBudget | None = None,
                 async_runtime: AsyncExecutionRuntime | None = None) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url
        self._reasoning_effort = reasoning_effort
        self._agent_name = agent_name
        self._mcp_url = mcp_url
        self._local_api_token = local_api_token
        self._timeout_seconds = timeout_seconds
        self._run_id = run_id
        self._runs = runs
        self._budget = budget or ExecutionBudget(
            max_seconds=timeout_seconds, max_turns=100,
        )
        self._async_runtime = async_runtime or AsyncExecutionRuntime()

    def run(self, *, instructions: str, input_text: str, max_turns: int) -> BackgroundAgentOutput:
        if self._run_id and self._runs:
            self._runs.record_event(self._run_id, "model_request_started", {})
        try:
            result = self._async_runtime.run(self._run(instructions, input_text, max_turns))
        except Exception as error:
            if self._run_id and self._runs:
                self._runs.record_event(
                    self._run_id, "model_request_failed", {"message": str(error)[:1024]},
                )
            raise
        if self._run_id and self._runs:
            self._runs.record_event(self._run_id, "model_request_completed", {})
        return result

    async def _run(self, instructions: str, input_text: str, max_turns: int) -> BackgroundAgentOutput:
        timeout_seconds, allocated_turns = self._budget.allocation(max_turns)
        mcp_server = None
        if self._mcp_url:
            from agents.mcp import MCPServerStreamableHttp
            mcp_server = MCPServerStreamableHttp(
                params={"url": self._mcp_url, "headers": {"Authorization": f"Bearer {self._local_api_token}"},
                        "timeout": timeout_seconds, "terminate_on_close": False},
                name=f"resono-background-{self._run_id}", cache_tools_list=True,
                client_session_timeout_seconds=timeout_seconds,
                require_approval="never", use_structured_content=True,
            )
        async def invoke():
            return await run_agent_turn(
                api_key=self._api_key, model=self._model, instructions=instructions,
                input_text=input_text, base_url=self._base_url,
                reasoning_effort=self._reasoning_effort, max_turns=allocated_turns,
                agent_name=self._agent_name, mcp_server=mcp_server,
                observation_sink=self._record_observation if self._run_id and self._runs else None,
                output_type=BackgroundAgentOutput,
            )
        if mcp_server is None:
            return await asyncio.wait_for(invoke(), timeout=timeout_seconds)
        async with mcp_server:
            return await asyncio.wait_for(invoke(), timeout=timeout_seconds)

    def _record_observation(self, observation: AgentTurnObservation) -> None:
        assert self._run_id is not None and self._runs is not None
        self._budget.record_turns(observation.model_turns)
        self._runs.record_event(
            self._run_id,
            "model_turns",
            {"count": observation.model_turns},
        )
        for summary in observation.reasoning_summaries:
            self._runs.record_event(self._run_id, "reasoning_summary", {"summary": summary})
