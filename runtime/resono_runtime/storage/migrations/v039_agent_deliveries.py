from __future__ import annotations

import sqlite3


def apply(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE background_agent_deliveries (
            run_id TEXT NOT NULL REFERENCES background_agent_runs(run_id) ON DELETE CASCADE,
            channel TEXT NOT NULL CHECK(channel IN ('voice','notification')),
            state TEXT NOT NULL CHECK(state IN ('pending','delivered','skipped_session_inactive','failed')),
            context_json TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (run_id, channel)
        );
        CREATE INDEX background_agent_deliveries_state_idx
            ON background_agent_deliveries(channel, state, updated_at);
        """
    )
