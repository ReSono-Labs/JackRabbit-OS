from __future__ import annotations

import sqlite3


def apply(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE background_agent_runs (
            run_id TEXT PRIMARY KEY,
            invocation_type TEXT NOT NULL,
            origin_id TEXT NOT NULL,
            objective TEXT NOT NULL,
            instruction_profile TEXT NOT NULL,
            success_criteria_json TEXT NOT NULL,
            result_schema_json TEXT NOT NULL,
            requested_resource_ids_json TEXT NOT NULL,
            autonomy TEXT NOT NULL,
            limits_json TEXT NOT NULL,
            state TEXT NOT NULL,
            cancellation_requested INTEGER NOT NULL DEFAULT 0,
            output_json TEXT,
            failure_code TEXT,
            failure_message TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            completed_at TEXT
        );
        CREATE INDEX background_agent_runs_state_idx ON background_agent_runs(state, updated_at);
        CREATE TABLE background_agent_run_events (
            run_id TEXT NOT NULL REFERENCES background_agent_runs(run_id) ON DELETE CASCADE,
            event_index INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            state TEXT NOT NULL,
            detail_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (run_id, event_index)
        );
        """
    )
