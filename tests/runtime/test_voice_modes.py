from __future__ import annotations

from resono_runtime.agents.audience import AgentKind
from resono_runtime.agents.delegation import DelegationRun
from resono_runtime.realtime.modes import (
    PRIMARY_VOICE_INSTRUCTION,
    VoiceModeService,
    register_voice_mode_tool,
)
from resono_runtime.tools import ToolCatalog, register_device_status
from resono_runtime.tools.definitions import ToolInvocationContext
from resono_runtime.tools.delegation import register_goal_tools


class _Delegation:
    def submit(self, _request):
        return DelegationRun("run-1", "goal", "voice-1", "queued", "direct_v1", None, None, None)

    def inspect(self, _run_id):
        raise NotImplementedError

    def cancel(self, _run_id):
        raise NotImplementedError


def _catalog_and_modes():
    catalog = ToolCatalog()
    modes = VoiceModeService()
    catalog.set_invocation_authorizer(modes.allows)
    register_device_status(catalog, lambda: {"status": "ready"})
    register_goal_tools(catalog, _Delegation(), modes)
    register_voice_mode_tool(catalog, modes)
    primary = lambda: catalog.realtime_definitions(exclude_names=frozenset({"goal_start"}))
    intake = lambda: catalog.realtime_definitions(
        include_names=frozenset({"voice_mode_switch", "goal_start"})
    )
    modes.open_session(
        "voice-1", primary_instructions="Primary.",
        primary_tools=primary, goal_intake_tools=intake,
    )
    return catalog, modes, primary, intake


def test_primary_and_goal_intake_use_distinct_canonical_projections() -> None:
    catalog, modes, primary, _intake = _catalog_and_modes()
    assert "goal_start" not in {tool["name"] for tool in primary()}
    changed = modes.switch("voice-1", "goal_intake")
    assert {tool["name"] for tool in changed.provider_session_update["session"]["tools"]} == {
        "voice_mode_switch", "goal_start",
    }
    denied = catalog.invoke(
        "get_device_status", {}, agent=AgentKind.VOICE,
        context=ToolInvocationContext(AgentKind.VOICE, voice_session_id="voice-1"),
    )
    assert denied.is_error


def test_primary_instruction_keeps_skill_tests_out_of_goal_intake() -> None:
    assert "installed Agent Skill requests" in PRIMARY_VOICE_INSTRUCTION
    assert "word test is never evidence" in PRIMARY_VOICE_INSTRUCTION


def test_duplicate_switch_replays_provider_update() -> None:
    _catalog, modes, _primary, _intake = _catalog_and_modes()
    modes.switch("voice-1", "goal_intake")
    duplicate = modes.switch("voice-1", "goal_intake")
    assert duplicate.structured_content == {"modeKey": "goal_intake", "duplicate": True}
    assert duplicate.provider_session_update["type"] == "session.update"


def test_successful_goal_submission_restores_primary_projection() -> None:
    catalog, modes, _primary, _intake = _catalog_and_modes()
    modes.switch("voice-1", "goal_intake")
    result = catalog.invoke(
        "goal_start",
        {
            "originalRequest": "Research local battery recycling.",
            "objective": "Prepare a sourced battery recycling summary.",
            "successCriteria": ["Summary identifies local options."],
            "verificationMethod": "Verify each option against its public site.",
            "completionConditions": ["A sourced summary is complete."],
            "stopConditions": [],
        },
        agent=AgentKind.VOICE,
        context=ToolInvocationContext(AgentKind.VOICE, voice_session_id="voice-1"),
    )
    assert not result.is_error
    assert modes.mode("voice-1") == "primary"
    assert "goal_start" not in {
        tool["name"] for tool in result.provider_session_update["session"]["tools"]
    }
