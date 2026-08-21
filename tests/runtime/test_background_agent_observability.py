import asyncio
from pathlib import Path
from types import SimpleNamespace

from resono_runtime.agents.audience import AgentKind
from resono_runtime.agents.sdk_runner import _observe, run_agent_turn
from resono_runtime.background_agent.progress import explain_failure, project_progress
from resono_runtime.background_agent.run_contract import AgentRunRequest, AgentRunState, AutonomyProfile, ExecutionRecipe, InvocationType
from resono_runtime.background_agent.tool_supply import BackgroundToolGrant, BackgroundToolSupply
from resono_runtime.storage.agent_runs import AgentRunRepository
from resono_runtime.storage.database import RuntimeDatabase
from resono_runtime.tools.catalog import ToolCatalog
from resono_runtime.tools.definitions import ToolDefinition, ToolInvocationResult


def request(run_id):
    return AgentRunRequest(
        run_id=run_id, invocation_type=InvocationType.GOAL, origin_id="voice-1",
        objective="Research.", instruction_profile="goal_task_v2",
        success_criteria=("Return findings.",), result_schema={"type": "object"},
        original_request="Research.", verification_method="Check findings.",
        completion_conditions=("Findings returned.",),
        stop_conditions=("A required source is unavailable.",),
    )


def repository(tmp_path):
    database = RuntimeDatabase(tmp_path / "runtime.sqlite3"); database.migrate()
    return AgentRunRepository(database)


def test_observation_records_only_provider_reasoning_summaries():
    values = []
    reasoning = SimpleNamespace(type="reasoning", summary=(SimpleNamespace(text="Checked evidence."),))
    message = SimpleNamespace(type="message", summary=(SimpleNamespace(text="private"),))
    _observe((SimpleNamespace(output=(reasoning, message)),), values.append)
    assert values[0].model_turns == 1
    assert values[0].reasoning_summaries == ("Checked evidence.",)


def test_subscription_uses_required_streaming_and_per_turn_reasoning_hook(monkeypatch):
    import agents

    observations = []
    captured = {}

    class Streamed:
        run_loop_exception = None
        final_output = "finished"

        async def stream_events(self):
            await captured["hooks"].on_llm_end(None, captured["agent"], SimpleNamespace(output=(
                SimpleNamespace(type="reasoning", summary=(SimpleNamespace(text="Compared sources."),)),
            )))
            if False:
                yield None

    def fake_streamed(agent, *, input, run_config, max_turns, hooks):
        captured["reasoning"] = agent.model_settings.reasoning
        captured["input"] = input
        captured["hooks"] = hooks
        captured["agent"] = agent
        return Streamed()

    monkeypatch.setattr(agents.Runner, "run_streamed", fake_streamed)
    result = asyncio.run(run_agent_turn(
        api_key="token", model="gpt-test", instructions="Work.", input_text="Research.",
        base_url="https://example.test/codex", reasoning_effort="medium", max_turns=5,
        agent_name="Background", observation_sink=observations.append,
    ))
    assert result == "finished"
    assert captured["reasoning"].summary == "auto"
    assert observations[0].model_turns == 1
    assert observations[0].reasoning_summaries == ("Compared sources.",)


def test_tool_events_drive_progress_without_arguments_or_results(tmp_path: Path):
    runs = repository(tmp_path); runs.create(request("tools"))
    catalog = ToolCatalog()
    catalog.register(ToolDefinition(
        tool_id="built-in:web_search", name="web_search", description="Search.",
        input_schema={"type": "object"}, effect_class="read",
        handler=lambda _args: ToolInvocationResult("secret-result"),
    ))
    supply = BackgroundToolSupply(
        catalog, BackgroundToolGrant(AutonomyProfile.LIMITED, frozenset({"web_search"}), 4),
        activity=lambda event, detail: runs.record_event("tools", event, detail),
    )
    assert supply.invoke("web_search", {"query": "private-query"}).text == "secret-result"
    events = runs.events("tools")
    progress = project_progress(AgentRunState.RUNNING, ExecutionRecipe.DIRECT, events)
    assert progress.tool_calls == 1
    assert progress.activity == "Searching public sources completed"
    serialized = repr(tuple(event.detail for event in events))
    assert "private-query" not in serialized and "secret-result" not in serialized


def test_historical_stop_failure_has_specific_explanation(tmp_path: Path):
    runs = repository(tmp_path); run = runs.create(request("historical"))
    runs.transition("historical", expected=run.state, target=AgentRunState.QUEUED, event_type="queued")
    runs.transition("historical", expected=AgentRunState.QUEUED, target=AgentRunState.FAILED,
                    event_type="verification_failed", failure_code="verification_failed",
                    failure_message="triggered stop condition")
    assert "earlier verification wrapper" in explain_failure(runs.get("historical"))


def test_terminal_progress_is_truthful():
    completed = project_progress(AgentRunState.COMPLETED, ExecutionRecipe.DIRECT)
    failed = project_progress(AgentRunState.FAILED, ExecutionRecipe.DIRECT)
    assert completed.label == "Completed" and completed.fraction == 1.0 and not completed.active
    assert failed.tone == "failed" and not failed.active
