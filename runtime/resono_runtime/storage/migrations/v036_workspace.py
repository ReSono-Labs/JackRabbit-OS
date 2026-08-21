from __future__ import annotations

import sqlite3


def apply(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE workspace_entries (
            workspace_id TEXT PRIMARY KEY,
            reference TEXT NOT NULL UNIQUE,
            display_name TEXT NOT NULL,
            media_type TEXT NOT NULL,
            byte_size INTEGER NOT NULL CHECK(byte_size >= 0),
            content_hash TEXT NOT NULL,
            origin TEXT NOT NULL,
            origin_run_id TEXT REFERENCES background_agent_runs(run_id) ON DELETE SET NULL,
            artifact_role TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX workspace_entries_origin_idx ON workspace_entries(origin_run_id, updated_at DESC);
        """
    )
