from pathlib import Path

from resono_runtime.background_agent.execution import BackgroundAgentExecution
from resono_runtime.background_agent.output_contract import BackgroundAgentOutput, PhaseEvidence
from resono_runtime.background_agent.run_contract import AgentRunRequest, AgentRunState, ExecutionRecipe, InvocationType, RunLimits
from resono_runtime.storage.agent_runs import AgentRunRepository
from resono_runtime.storage.database import RuntimeDatabase


class Executor:
    def __init__(self, output): self.output, self.calls = output, []
    def run(self, **call):
        self.calls.append(call)
        if isinstance(self.output, Exception): raise self.output
        return self.output


def request(recipe, run_id):
    return AgentRunRequest(
        run_id=run_id, invocation_type=InvocationType.GOAL, origin_id="voice-1",
        objective="Produce a sourced report.", instruction_profile="goal_task_v2",
        success_criteria=("The report cites a source.",), result_schema={"type": "object"},
        recipe=recipe, limits=RunLimits(max_model_turns=9),
        original_request="Make me a sourced report.",
        verification_method="Inspect the report and citations.",
        completion_conditions=("The report is saved.",),
    )


def repository(tmp_path):
    database = RuntimeDatabase(tmp_path / "runtime.sqlite3"); database.migrate()
    return AgentRunRepository(database)


def complete_output():
    return BackgroundAgentOutput(
        status="complete", summary="The sourced report was produced.",
        artifact_references=["workspace://generated/report.md"],
        verification_summary="The saved report and citations were inspected.",
        phase_evidence=[PhaseEvidence(phase="verification", summary="The report was checked.")],
    )


def test_every_compatibility_recipe_runs_exactly_one_typed_sdk_agent(tmp_path: Path):
    runs = repository(tmp_path)
    for recipe in ExecutionRecipe:
        executor = Executor(complete_output())
        result = BackgroundAgentExecution(repository=runs, executor=executor).execute(request(recipe, recipe.value))
        assert result.state is AgentRunState.COMPLETED
        assert result.output["status"] == "complete"
        assert len(executor.calls) == 1
        assert executor.calls[0]["max_turns"] == 9
        assert "reason-act-check" in executor.calls[0]["instructions"]


def test_incomplete_typed_result_is_preserved_as_truthful_failure(tmp_path: Path):
    output = BackgroundAgentOutput(
        status="blocked", summary="The required source could not be reached.",
        verification_summary="The source requirement remains unmet.",
        unresolved_issues=["Required source unavailable."],
    )
    result = BackgroundAgentExecution(repository=repository(tmp_path), executor=Executor(output)).execute(
        request(ExecutionRecipe.SELF_REVIEW, "blocked")
    )
    assert result.state is AgentRunState.FAILED
    assert result.failure_code == "agent_incomplete"
    assert result.output["status"] == "blocked"


def test_max_turns_has_a_distinct_terminal_failure(tmp_path: Path):
    error = type("MaxTurnsExceeded", (RuntimeError,), {})("limit reached")
    result = BackgroundAgentExecution(repository=repository(tmp_path), executor=Executor(error)).execute(
        request(ExecutionRecipe.DIRECT, "max-turns")
    )
    assert result.state is AgentRunState.FAILED
    assert result.failure_code == "max_turns_exceeded"
    assert result.failure_message == "The agent reached its 9-turn limit."


def test_duplicate_goal_entries_are_rejected():
    try:
        AgentRunRequest(
            run_id="duplicate", invocation_type=InvocationType.GOAL, origin_id="voice-1",
            objective="Produce report.", instruction_profile="goal_task_v2",
            success_criteria=("Same.", "Same."), result_schema={"type": "object"},
            original_request="Make report.", verification_method="Inspect it.",
            completion_conditions=("Saved.",),
        )
    except ValueError as error:
        assert "success_criteria" in str(error)
    else: raise AssertionError("duplicates must fail")
