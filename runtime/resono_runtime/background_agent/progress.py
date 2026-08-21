"""Safe, recipe-aware progress projection for delegated work."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Any

from .run_contract import AgentRunState, ExecutionRecipe


@dataclass(frozen=True, slots=True)
class RunProgress:
    phase: str
    label: str
    fraction: float
    active: bool
    tone: str
    activity: str
    model_turns: int
    tool_calls: int
    timeline: tuple[dict[str, object], ...]


def project_progress(state: AgentRunState, recipe: ExecutionRecipe,
                     events: Iterable[Any] = ()) -> RunProgress:
    """Describe lifecycle position without claiming unknowable work percentage."""
    items = tuple(events)
    model_turns = sum(
        int(item.detail.get("count", 0)) for item in items if item.event_type == "model_turns"
    )
    tool_calls = max(
        (int(item.detail.get("call", 0)) for item in items if item.event_type.startswith("tool_")),
        default=0,
    )
    timeline = tuple(_timeline(item) for item in items if _visible(item.event_type))[-8:]
    latest = timeline[-1]["label"] if timeline else "Run accepted"

    def value(phase: str, label: str, fraction: float, active: bool, tone: str) -> RunProgress:
        return RunProgress(phase, label, fraction, active, tone, str(latest), model_turns, tool_calls, timeline)

    if state is AgentRunState.ACCEPTED:
        return value("preparing", "Preparing goal context", 0.12, True, "active")
    if state is AgentRunState.QUEUED:
        return value("queued", "Waiting for the Background Agent", 0.24, True, "active")
    if state is AgentRunState.RUNNING:
        label = "Working and checking the result" if recipe is ExecutionRecipe.SELF_REVIEW else "Background Agent is working"
        return value("working", label, 0.52, True, "active")
    if state is AgentRunState.REVIEWING:
        return value("reviewing", "Independent reviewer is checking the result", 0.72, True, "active")
    if state is AgentRunState.REPAIRING:
        return value("repairing", "Applying reviewer feedback", 0.84, True, "active")
    if state is AgentRunState.COMPLETED:
        return value("completed", "Completed", 1.0, False, "complete")
    if state is AgentRunState.CANCELLED:
        return value("cancelled", "Cancelled", 1.0, False, "stopped")
    return value("failed", "Stopped before completion", 1.0, False, "failed")


def explain_failure(run: Any) -> str | None:
    if not run.failure_code:
        return None
    if run.failure_code == "verification_failed" and "stop condition" in str(run.failure_message).lower():
        conditions = "; ".join(run.request.stop_conditions)
        return (
            "The earlier verification wrapper rejected the agent result because a submitted stop "
            f"condition was reported as reached: {conditions or 'an unspecified stop condition'}. "
            "A successful end state belongs under completion conditions, not stop conditions."
        )
    labels = {
        "max_turns_exceeded": "The Agents SDK reached the configured model-turn limit before returning a result.",
        "run_timeout": "The run reached its configured time limit before returning a result.",
        "agent_incomplete": "The agent returned a typed result but reported that work was blocked or still needed attention.",
        "execution_failed": "The Agents SDK execution stopped before it could return a typed result.",
    }
    return labels.get(run.failure_code, str(run.failure_message or run.failure_code))


def _visible(event_type: str) -> bool:
    return event_type in {
        "accepted", "context_frozen", "queued", "sdk_agent_started",
        "model_request_started", "model_request_completed", "model_request_failed",
        "model_turns", "tool_started", "tool_completed", "tool_failed",
        "agent_evidence", "completed", "agent_incomplete", "execution_failed",
        "max_turns_exceeded", "run_timeout", "cancelled",
    }


def _timeline(item: Any) -> dict[str, object]:
    event_type = item.event_type
    detail = item.detail
    tool = _tool_label(str(detail.get("name", "tool")))
    labels = {
        "accepted": "Goal accepted",
        "context_frozen": "Goal context prepared",
        "queued": "Queued for the Background Agent",
        "sdk_agent_started": "Agents SDK run started",
        "model_request_started": "Agent is reasoning and selecting tools",
        "model_request_completed": "Agent returned a typed result",
        "model_request_failed": "Model request failed",
        "model_turns": f"Completed {detail.get('count', 0)} model turns",
        "tool_started": f"{tool} started",
        "tool_completed": f"{tool} completed",
        "tool_failed": f"{tool} failed",
        "agent_evidence": str(detail.get("summary", "Agent evidence recorded")),
        "completed": "Result committed",
        "agent_incomplete": "Agent reported unresolved work",
        "execution_failed": "SDK execution failed",
        "max_turns_exceeded": "Maximum model turns reached",
        "run_timeout": "Maximum run time reached",
        "cancelled": "Run cancelled",
    }
    return {"type": event_type, "label": labels.get(event_type, event_type.replace("_", " ")),
            "createdAt": item.created_at}


def _tool_label(name: str) -> str:
    labels = {
        "web_search": "Searching public sources",
        "run_workspace_write": "Writing a run workspace file",
        "run_workspace_read": "Reading a run workspace file",
        "run_workspace_list": "Inspecting run workspace files",
        "workspace_publish": "Publishing an artifact",
    }
    return labels.get(name, name.replace("_", " ").strip().capitalize())
