"""Slice 2 — real Agents SDK turn over chat completions (TDD)."""

from __future__ import annotations

import pytest

from resono_runtime.agents.sdk_runner import run_agent_turn

from .fake_compatible_server import FakeCompatibleServer


@pytest.fixture
def server():
    instance = FakeCompatibleServer()
    instance.start()
    yield instance
    instance.stop()


@pytest.mark.anyio  # placeholder; run_agent_turn is async — use asyncio.run instead
def test_run_agent_turn_chat_completions_against_fake(server):
    import asyncio

    output = asyncio.run(
        run_agent_turn(
            api_key="test-key",
            model="deepseek-v4-pro",
            instructions="You are a terse assistant.",
            input_text="Hello from slice 2",
            base_url=server.base_url,
            reasoning_effort="none",
            max_turns=1,
            agent_name="test-agent",
            use_responses=False,
        )
    )
    assert "echo:" in output
    assert "Hello from slice 2" in output
    assert server.chat_requests, "no chat completion request received"
