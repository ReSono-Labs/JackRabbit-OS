from __future__ import annotations

import json
from pathlib import Path

from resono_runtime.background_agent.completion_dispatch import CompletionDispatcher
from resono_runtime.background_agent.run_contract import AgentRunRequest, AgentRunState, InvocationType
from resono_runtime.background_agent.run_state import RunLifecycle
from resono_runtime.storage.agent_deliveries import AgentRunDeliveryRepository
from resono_runtime.storage.agent_runs import AgentRunRepository
from resono_runtime.storage.database import RuntimeDatabase


def _completed_run(database: RuntimeDatabase, *, large: bool = False):
    runs = AgentRunRepository(database)
    lifecycle = RunLifecycle(runs)
    request = AgentRunRequest(
        run_id="run-1", invocation_type=InvocationType.GOAL,
        origin_id="voice-1", objective="Prepare the report.",
        instruction_profile="goal_task_v2",
        success_criteria=("Report is complete.",),
        result_schema={"type": "object"},
        original_request="Prepare a report.",
        verification_method="Inspect the report.",
        completion_conditions=("The report is saved.",),
    )
    lifecycle.accept(request)
    lifecycle.move("run-1", AgentRunState.QUEUED, event_type="queued")
    lifecycle.move("run-1", AgentRunState.RUNNING, event_type="running")
    return lifecycle.move(
        "run-1", AgentRunState.COMPLETED, event_type="completed",
        output={"summary": "Complete", "result": {"body": "x" * (80_000 if large else 8)}},
    )


def test_voice_delivery_is_leased_only_to_origin_and_acknowledged(tmp_path: Path) -> None:
    database = RuntimeDatabase(tmp_path / "runtime.sqlite3")
    database.migrate()
    deliveries = AgentRunDeliveryRepository(database)
    CompletionDispatcher(
        deliveries=deliveries, voice_session_active=lambda value: value == "voice-1",
    ).record(_completed_run(database))

    assert deliveries.claim_voice("voice-other") is None
    claimed = deliveries.claim_voice("voice-1")
    assert claimed is not None and claimed.state == "delivering"
    assert not deliveries.acknowledge_voice(run_id="run-1", session_id="voice-other")
    assert deliveries.acknowledge_voice(run_id="run-1", session_id="voice-1")
    states = {item.channel: item.state for item in deliveries.list_for_run("run-1")}
    assert states == {"notification": "pending", "voice": "delivered"}


def test_voice_context_is_bounded_while_notification_keeps_full_output(tmp_path: Path) -> None:
    database = RuntimeDatabase(tmp_path / "runtime.sqlite3")
    database.migrate()
    deliveries = AgentRunDeliveryRepository(database)
    CompletionDispatcher(
        deliveries=deliveries, voice_session_active=lambda _value: True,
    ).record(_completed_run(database, large=True))
    values = {item.channel: json.loads(item.context_json)
              for item in deliveries.list_for_run("run-1")}
    assert len(json.dumps(values["voice"]).encode()) < 65_536
    assert values["voice"]["output"]["resultTruncatedForVoice"] is True
    assert len(values["notification"]["output"]["result"]["body"]) == 80_000


def test_native_notification_clock_starts_once_after_completed_run_is_viewed(tmp_path: Path) -> None:
    database = RuntimeDatabase(tmp_path / "runtime.sqlite3")
    database.migrate()
    deliveries = AgentRunDeliveryRepository(database)
    CompletionDispatcher(
        deliveries=deliveries, voice_session_active=lambda _value: False,
    ).record(_completed_run(database))

    assert deliveries.visible_notification_run_ids() == ("run-1",)
    assert deliveries.acknowledge_notification("run-1")
    first = {item.channel: item.updated_at for item in deliveries.list_for_run("run-1")}
    assert deliveries.acknowledge_notification("run-1")
    second = {item.channel: item.updated_at for item in deliveries.list_for_run("run-1")}
    assert first["notification"] == second["notification"]
    assert deliveries.visible_notification_run_ids() == ("run-1",)
