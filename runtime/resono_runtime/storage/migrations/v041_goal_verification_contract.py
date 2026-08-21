from __future__ import annotations

import sqlite3


def apply(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        ALTER TABLE background_agent_runs
            ADD COLUMN verification_method TEXT NOT NULL DEFAULT '';
        ALTER TABLE background_agent_runs
            ADD COLUMN completion_conditions_json TEXT NOT NULL DEFAULT '[]';
        ALTER TABLE background_agent_runs
            ADD COLUMN stop_conditions_json TEXT NOT NULL DEFAULT '[]';
        """
    )
