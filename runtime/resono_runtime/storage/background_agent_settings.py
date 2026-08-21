"""Durable operator policy for the optional Background Agent."""

from __future__ import annotations

from dataclasses import dataclass
import json

from ..background_agent.run_contract import AutonomyProfile, ExecutionRecipe, RunLimits
from .database import RuntimeDatabase


@dataclass(frozen=True, slots=True)
class BackgroundAgentSettings:
    enabled: bool
    autonomy: AutonomyProfile
    reasoning_effort: str
    default_recipe: ExecutionRecipe
    allowed_tool_names: frozenset[str]
    limits: RunLimits
    updated_at: str


class BackgroundAgentSettingsRepository:
    def __init__(self, database: RuntimeDatabase) -> None:
        self._database = database

    def get(self) -> BackgroundAgentSettings:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM background_agent_settings WHERE settings_id = 1").fetchone()
        if row is None:
            raise RuntimeError("background-agent settings are not initialized")
        return _settings(row)

    def save(self, *, enabled: bool, autonomy: AutonomyProfile, reasoning_effort: str,
             default_recipe: ExecutionRecipe, allowed_tool_names: frozenset[str],
             limits: RunLimits) -> BackgroundAgentSettings:
        if reasoning_effort not in {"none", "low", "medium", "high"}:
            raise ValueError("reasoning_effort is invalid")
        normalized_names = frozenset(_tool_name(item) for item in allowed_tool_names)
        with self._database.connect() as connection:
            connection.execute(
                "UPDATE background_agent_settings SET enabled = ?, autonomy = ?, reasoning_effort = ?, default_recipe = ?, allowed_tool_names_json = ?, max_seconds = ?, max_model_turns = ?, max_tool_calls = ?, max_review_rounds = ?, max_workspace_bytes = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE settings_id = 1",
                (int(enabled), autonomy.value, reasoning_effort, default_recipe.value,
                 json.dumps(sorted(normalized_names), separators=(",", ":")), limits.max_seconds,
                 limits.max_model_turns, limits.max_tool_calls, limits.max_review_rounds,
                 limits.max_workspace_bytes),
            )
            connection.commit()
        return self.get()


def _settings(row) -> BackgroundAgentSettings:
    names = json.loads(str(row["allowed_tool_names_json"]))
    if not isinstance(names, list) or any(not isinstance(item, str) for item in names):
        raise RuntimeError("stored background-agent tool grants are invalid")
    return BackgroundAgentSettings(
        bool(row["enabled"]), AutonomyProfile(str(row["autonomy"])),
        str(row["reasoning_effort"]), ExecutionRecipe(str(row["default_recipe"])), frozenset(names),
        RunLimits(max_seconds=int(row["max_seconds"]), max_model_turns=int(row["max_model_turns"]),
                  max_tool_calls=int(row["max_tool_calls"]), max_review_rounds=int(row["max_review_rounds"]),
                  max_workspace_bytes=int(row["max_workspace_bytes"])), str(row["updated_at"]),
    )


def _tool_name(value: str) -> str:
    if not value or value.strip() != value or len(value) > 128:
        raise ValueError("tool names must be non-empty trimmed strings")
    return value
