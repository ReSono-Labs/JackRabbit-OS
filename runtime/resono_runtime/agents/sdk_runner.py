from __future__ import annotations

import asyncio


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
) -> str:
    """Run one OpenAI Agents SDK turn and return the final output text.

    The single agent-execution path for every runtime agent (text, memory
    review, and future agents): one provider, one model-settings construction,
    one streamed/subscription vs sync/platform branch. Tracing stays disabled
    and no parallel agent loop is created. Callers own any MCP server
    lifecycle and pass the entered server in.
    """
    from agents import Agent, ModelSettings, RunConfig, Runner, set_tracing_disabled
    from agents.models.openai_provider import OpenAIProvider
    from openai.types.shared import Reasoning

    set_tracing_disabled(True)
    provider = OpenAIProvider(api_key=api_key, base_url=base_url, use_responses=True)
    model_settings = ModelSettings(
        reasoning=Reasoning(effort=reasoning_effort) if reasoning_effort != "none" else None,
        store=False if base_url else None,
    )
    agent = Agent(
        name=agent_name,
        instructions=instructions,
        model=model,
        model_settings=model_settings,
        mcp_servers=[mcp_server] if mcp_server is not None else [],
    )
    run_config = RunConfig(model_provider=provider)
    if base_url:
        streamed = Runner.run_streamed(
            agent,
            input=input_text,
            run_config=run_config,
            max_turns=max_turns,
        )
        async for _event in streamed.stream_events():
            pass
        return str(streamed.final_output)
    result = await Runner.run(
        agent,
        input=input_text,
        run_config=run_config,
        max_turns=max_turns,
    )
    return str(result.final_output)


def run_agent_turn_sync(**kwargs) -> str:
    """Synchronous wrapper for callers that do not already run an event loop."""
    return asyncio.run(run_agent_turn(**kwargs))
