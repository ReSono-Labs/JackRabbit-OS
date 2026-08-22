from __future__ import annotations

from pathlib import Path

import pytest

from resono_runtime.agents.audience import AgentKind
from resono_runtime.background_agent.workspace import RunWorkspaceRegistry
from resono_runtime.storage.database import RuntimeDatabase
from resono_runtime.storage.workspace import WorkspaceRepository
from resono_runtime.tools.catalog import ToolCatalog
from resono_runtime.tools.definitions import ToolInvocationContext
from resono_runtime.workspace.service import DurableWorkspace
from resono_runtime.workspace.tools import register_workspace_tools


def test_primary_voice_can_read_but_not_modify_agent_workspaces(tmp_path: Path) -> None:
    database = RuntimeDatabase(tmp_path / "runtime.sqlite3")
    database.migrate()
    runs = RunWorkspaceRegistry(tmp_path / "runs")
    run = runs.create("run-1", max_total_bytes=1024 * 1024)
    run.write_text("work/report.md", "Verified agent output.")
    catalog = ToolCatalog()
    register_workspace_tools(
        catalog,
        DurableWorkspace(tmp_path / "user", WorkspaceRepository(database)),
        runs,
    )

    voice_names = {item["name"] for item in catalog.mcp_definitions(AgentKind.VOICE)}
    assert {
        "workspace_list",
        "workspace_read",
        "run_workspace_list",
        "run_workspace_read",
    } <= voice_names
    assert "run_workspace_write" not in voice_names
    assert "workspace_publish" not in voice_names

    context = ToolInvocationContext(AgentKind.VOICE, voice_session_id="voice-1")
    listed = catalog.invoke(
        "run_workspace_list", {"runId": "run-1"}, agent=AgentKind.VOICE, context=context,
    )
    read = catalog.invoke(
        "run_workspace_read",
        {"runId": "run-1", "reference": "work/report.md"},
        agent=AgentKind.VOICE,
        context=context,
    )
    denied = catalog.invoke(
        "run_workspace_write",
        {"reference": "work/changed.md", "content": "not allowed"},
        agent=AgentKind.VOICE,
        context=context,
    )

    assert not listed.is_error
    assert listed.structured_content == {"runId": "run-1", "files": ["work/report.md"]}
    assert not read.is_error
    assert read.structured_content == {
        "runId": "run-1",
        "reference": "work/report.md",
        "text": "Verified agent output.",
    }
    assert denied.is_error
    assert denied.text == "Tool is not granted."


def test_releasing_run_workspace_preserves_published_artifact(tmp_path: Path) -> None:
    database = RuntimeDatabase(tmp_path / "runtime.sqlite3")
    database.migrate()
    runs = RunWorkspaceRegistry(tmp_path / "runs")
    run = runs.create("run-1", max_total_bytes=1024 * 1024)
    run.write_text("work/report.md", "Durable result.")
    durable = DurableWorkspace(tmp_path / "user", WorkspaceRepository(database))
    durable.publish(
        run.path_for_publication("work/report.md"),
        "workspace://documents/report.md",
        media_type="text/markdown",
        origin_run_id=None,
        artifact_role="result",
    )

    runs.release("run-1")
    runs.release("run-1")

    assert durable.read("workspace://documents/report.md") == b"Durable result."
    assert not (tmp_path / "runs" / "run-1").exists()
    with pytest.raises(KeyError):
        runs.get("run-1")


def test_release_cannot_escape_run_workspace_root(tmp_path: Path) -> None:
    runs = RunWorkspaceRegistry(tmp_path / "runs")
    outside = tmp_path / "outside"
    outside.mkdir()
    marker = outside / "keep.txt"
    marker.write_text("keep", encoding="utf-8")

    with pytest.raises(Exception):
        runs.release("../outside")

    assert marker.read_text(encoding="utf-8") == "keep"
