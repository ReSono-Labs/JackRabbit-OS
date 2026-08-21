from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class AgentTurnObservation:
    model_turns: int
    reasoning_summaries: tuple[str, ...]


async def run_agent_turn(
    *,
    api_key: str,
    model: str,
    instructions: str,
    input_text: str,
    base_url: str | None,
    reasoning_effort: str,
    max_turns: int,
    agent_name: str,
    mcp_server: object | None = None,
    observation_sink: Callable[[AgentTurnObservation], None] | None = None,
    output_type: type[Any] | None = None,
) -> Any:
    """Run one OpenAI Agents SDK turn and return the final output text.

    The single agent-execution path for every runtime agent (text, memory
    review, and future agents): one provider, one model-settings construction,
    one streamed/subscription vs sync/platform branch. Tracing stays disabled
    and no parallel agent loop is created. Callers own any MCP server
    lifecycle and pass the entered server in.
    """
    from agents import Agent, ModelSettings, RunConfig, RunHooks, Runner, set_tracing_disabled
    from agents.models.openai_provider import OpenAIProvider
    from openai.types.shared import Reasoning

    set_tracing_disabled(True)
    provider = OpenAIProvider(api_key=api_key, base_url=base_url, use_responses=True)
    model_settings = ModelSettings(
        reasoning=Reasoning(effort=reasoning_effort, summary="auto")
        if reasoning_effort != "none" else None,
        store=False if base_url else None,
    )
    agent = Agent(
        name=agent_name,
        instructions=instructions,
        model=model,
        model_settings=model_settings,
        mcp_servers=[mcp_server] if mcp_server is not None else [],
        output_type=output_type,
    )
    run_config = RunConfig(model_provider=provider)
    class ObservationHooks(RunHooks):
        async def on_llm_end(self, _context, _agent, response) -> None:
            _observe((response,), observation_sink)

    try:
        if base_url:
            streamed = Runner.run_streamed(
                agent, input=input_text, run_config=run_config, max_turns=max_turns,
                hooks=ObservationHooks(),
            )
            async for _event in streamed.stream_events():
                pass
            if streamed.run_loop_exception is not None:
                raise streamed.run_loop_exception
            return streamed.final_output if output_type is not None else str(streamed.final_output)
        result = await Runner.run(
            agent, input=input_text, run_config=run_config, max_turns=max_turns,
            hooks=ObservationHooks(),
        )
        return result.final_output if output_type is not None else str(result.final_output)
    except BaseException as error:
        raise


def run_agent_turn_sync(**kwargs) -> str:
    """Synchronous wrapper for callers that do not already run an event loop."""
    return asyncio.run(run_agent_turn(**kwargs))


def _observe(raw_responses: object, sink: Callable[[AgentTurnObservation], None] | None) -> None:
    if sink is None:
        return
    responses = tuple(raw_responses) if isinstance(raw_responses, (list, tuple)) else ()
    summaries: list[str] = []
    for response in responses:
        for item in getattr(response, "output", ()):
            if getattr(item, "type", None) != "reasoning":
                continue
            for summary in getattr(item, "summary", ()):
                text = str(getattr(summary, "text", "")).strip()
                if text:
                    summaries.append(text[:16_384])
    sink(AgentTurnObservation(len(responses), tuple(summaries)))
