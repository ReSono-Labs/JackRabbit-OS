from __future__ import annotations

import sqlite3


def apply(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        ALTER TABLE background_agent_runs
            ADD COLUMN original_request TEXT NOT NULL DEFAULT '';

        ALTER TABLE background_agent_deliveries RENAME TO background_agent_deliveries_v39;
        CREATE TABLE background_agent_deliveries (
            run_id TEXT NOT NULL REFERENCES background_agent_runs(run_id) ON DELETE CASCADE,
            channel TEXT NOT NULL CHECK(channel IN ('voice','notification')),
            state TEXT NOT NULL CHECK(state IN (
                'pending','delivering','delivered','skipped_session_inactive','failed'
            )),
            context_json TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (run_id, channel)
        );
        INSERT INTO background_agent_deliveries(run_id, channel, state, context_json, updated_at)
            SELECT run_id, channel, state, context_json, updated_at
            FROM background_agent_deliveries_v39;
        DROP TABLE background_agent_deliveries_v39;
        CREATE INDEX background_agent_deliveries_state_idx
            ON background_agent_deliveries(channel, state, updated_at);
        """
    )
