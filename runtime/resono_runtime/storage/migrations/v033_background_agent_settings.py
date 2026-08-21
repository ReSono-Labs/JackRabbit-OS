from __future__ import annotations

import sqlite3


def apply(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE background_agent_settings (
            settings_id INTEGER PRIMARY KEY CHECK(settings_id = 1),
            enabled INTEGER NOT NULL,
            autonomy TEXT NOT NULL,
            reasoning_effort TEXT NOT NULL,
            allowed_tool_names_json TEXT NOT NULL,
            max_seconds INTEGER NOT NULL,
            max_model_turns INTEGER NOT NULL,
            max_tool_calls INTEGER NOT NULL,
            max_review_rounds INTEGER NOT NULL,
            max_workspace_bytes INTEGER NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        INSERT INTO background_agent_settings(
            settings_id, enabled, autonomy, reasoning_effort,
            allowed_tool_names_json, max_seconds, max_model_turns,
            max_tool_calls, max_review_rounds, max_workspace_bytes, updated_at
        ) VALUES (1, 0, 'limited', 'medium', '[]', 300, 24, 40, 2, 8388608,
                  strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
        """
    )
